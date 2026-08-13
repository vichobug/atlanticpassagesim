# Data Dictionary

Every dataset the simulation pulls or generates, what it contains, where it
comes from, and how each field is used downstream.

---

## 1. `hallberg-rassy40.pol` (checked into git)

The boat's **polar diagram**: measured/predicted boat speed as a function of
wind angle and wind strength, for a Hallberg-Rassy 40. This is a static,
hand-authored reference table -- not fetched from anywhere.

**Format**: tab-separated text. Row 1 is a header of TWS (True Wind Speed)
values in knots. Each subsequent row starts with a TWA (True Wind Angle) in
degrees, followed by boat speed in knots at each TWS for that angle.

| Field | Meaning | Units | Range in this file |
|---|---|---|---|
| `TWA` (row label) | True wind angle: angle between the wind and the boat's heading, 0 = wind dead ahead, 180 = wind dead astern | degrees | 0-180 (17 rows) |
| `TWS` (column header) | True wind speed | knots | 0-60 (17 columns) |
| cell value | Boat speed at that TWA/TWS combination | knots | 0.0-11.2 |

**Used by**: `src/polar.py`'s `Polar` class, which 2D-linearly-interpolates
(`scipy.interpolate.RegularGridInterpolator`) between grid points to get a
boat speed for any arbitrary (TWS, TWA) pair encountered during simulation.
TWA is folded to 0-180 (symmetric port/starboard) before lookup; TWS is
clipped to the table's [0, 60] range rather than extrapolated.

---

## 2. ERA5 reanalysis wind data (fetched, gitignored)

The real-world weather input. **ERA5** is the European Centre for
Medium-Range Weather Forecasts' (ECMWF) fifth-generation atmospheric
reanalysis -- a physics-model reconstruction of global historical weather,
blending decades of observations (satellites, ships, buoys, radiosondes) into
a consistent hourly gridded record. It's the standard reference dataset for
"what did the weather actually do on date X" going back to 1940.

Distributed via the **Copernicus Climate Data Store (CDS)**, ECMWF/EU's public
data portal (`cds.climate.copernicus.eu`), which is why the setup requires a
free CDS account + API key + one-time license acceptance for the specific
dataset (`reanalysis-era5-single-levels`) before the API will serve data.

### 2a. Raw download: `era5_wind_raw_hourly.nc`

Fetched by `scripts/fetch_era5.py` via the `cdsapi` Python client, one CDS API
request for the full multi-year, multi-variable pull. Format: NetCDF
(originally GRIB internally, converted server-side).

**Request parameters** (`fetch_era5.py`'s `build_request()`):

| Parameter | Value | Meaning |
|---|---|---|
| `product_type` | `reanalysis` | The historical best-estimate reconstruction (as opposed to a forecast ensemble) |
| `variable` | `10m_u_component_of_wind`, `10m_v_component_of_wind` | Wind velocity components 10m above ground/sea surface -- the standard meteorological measurement height |
| `year` | 2015-2024 | Last 10 years, one full decade of trade-wind seasons |
| `month` | 11, 12, 1, 2 | Nov-Dec-Jan (the ARC/trade-wind sailing season) + Feb as a buffer so late-January starts don't run off the edge of the data mid-passage |
| `day` | 1-31 | All days (invalid combos like Feb 30 are silently ignored by CDS) |
| `time` | 00:00, 06:00, 12:00, 18:00 UTC | Synoptic hours only, not all 24 -- keeps the download ~4x smaller; a day's mean of 4 evenly-spaced samples is a good enough approximation of the daily mean for this route's synoptic-scale trade winds |
| `area` | `[N, W, S, E]` bounding box, computed from the route's waypoints + 3 deg margin | Restricts the download to just the Atlantic corridor the route crosses, not the whole globe |
| `data_format` | `netcdf` | CDS converts its native GRIB to NetCDF server-side before download |

**Resulting file structure** (as actually downloaded, confirmed by inspection):

| Dimension | Size | Description |
|---|---|---|
| `valid_time` | 4812 | One entry per synoptic timestep across the whole 2015-2024, Nov-Feb pull (10 years x 4 months x ~30 days x 4 times/day, minus a few due to calendar quirks) |
| `latitude` | 80 | 0.25 deg grid, 11.25N to 31.0N |
| `longitude` | 199 | 0.25 deg grid, 63.75W to 14.25W |

| Variable | Dims | Units | Meaning |
|---|---|---|---|
| `u10` | (valid_time, latitude, longitude) | m/s | Eastward wind component at 10m height (positive = blowing toward the east) |
| `v10` | (valid_time, latitude, longitude) | m/s | Northward wind component at 10m height (positive = blowing toward the north) |
| `number` | scalar | -- | Ensemble member ID; always 0 here (reanalysis has one deterministic member, not an ensemble) |
| `expver` | (valid_time) | -- | ECMWF's internal "experiment version" tag; always `0001` for finalized ERA5 (a different value would flag preliminary/near-real-time data, not relevant here) |

Grid resolution is 0.25 deg (~15 nm), well below the ~100nm route-waypoint
spacing used elsewhere -- see `src/wind_data.py`'s docstring for why nearest-
neighbor lookup (not bilinear interpolation) is good enough at that ratio.

### 2b. Processed file: `era5_wind_nov_jan.nc`

Produced from the raw file by `fetch_era5.py`: renames the `valid_time`
dimension to `time` (matching what `src/wind_data.py` expects), then
resamples from synoptic-hour resolution down to a **daily mean**
(`ds.resample(time="1D").mean()`). This is the file the simulation actually
reads.

| Dimension | Size | Description |
|---|---|---|
| `time` | 3653 | One daily-mean entry per calendar day, 2015-01-01 through 2024-12-31 (the resample runs over the whole year even though only Nov/Dec/Jan/Feb have real data underneath -- other months are an artifact of the resample call, not meaningful, and are never queried by the simulation) |
| `latitude` | 80 | Same grid as above |
| `longitude` | 199 | Same grid as above |

Variables (`u10`, `v10`) are the same u/v wind components as above, now
averaged across each day's synoptic samples.

**Used by**: `src/wind_data.py`.
- `wind_at(ds, lat, lon, date)`: nearest-neighbor lookup of `u10`/`v10` at a
  given point/day, converts m/s to knots (`x 1.94384`), and combines u/v into
  a wind speed (`hypot(u, v)`) and a meteorological "wind FROM" bearing
  (`(270 - atan2(v, u)) % 360` -- u/v give the direction wind blows *toward*,
  but sailors need the direction it blows *from*).
- `wind_to_twa(wind_from_bearing, course_bearing)`: converts that true wind
  bearing into a signed angle relative to the boat's course (True Wind
  Angle), which is what `polar.py`'s `boat_speed()` actually consumes.

---

## 3. Route geometry (computed, not fetched)

`src/route.py` hard-codes the two endpoints and computes everything else:

| Constant | Value | Meaning |
|---|---|---|
| `LAS_PALMAS` | (28.15 N, 17.10 W) | Start: Las Palmas, Gran Canaria |
| `RODNEY_BAY` | (14.08 N, 60.95 W) | End: Rodney Bay, St Lucia |
| `EARTH_RADIUS_NM` | 3440.065 | Mean Earth radius in nautical miles, used in the rhumb-line math |

Route distance/bearing use **rhumb-line** (constant-compass-bearing) geometry
rather than great-circle, since over this route's ~16 degrees of latitude
span the two diverge by only ~1-2% in distance, and a rhumb line is how
trade-wind passages are actually sailed (one steady heading) -- which matches
what "course bearing" needs to mean for the TWA calculation in
`wind_data.py`.

Derived values used by the simulation: total route distance (~2590 nm),
course bearing (~251 deg true), and `latlon_at_distance()` -- a closed-form
projection giving the boat's lat/lon after sailing N nm along the rhumb line,
used every simulated day to know where to sample the wind field.

---

## 4. Monte Carlo simulation output (generated each run, not persisted as data)

`notebooks/monte_carlo_era5.py` doesn't fetch new data -- it consumes
`era5_wind_nov_jan.nc` + the polar + the route geometry and produces:

- **Per-trial passage time** (days): for each of 5000 trials, a random
  historical Nov/Dec/Jan start date is picked, then the simulation walks
  day-by-day, looking up that day's real historical wind at the boat's
  current position, converting to boat speed via the polar, and advancing
  distance (`speed_kn * 24` nm/day) until the route distance is covered.
  This is what makes it "historical-passage sampling" rather than i.i.d.
  daily draws (the Phase 2 toy model): each trial reuses one real,
  consecutive historical weather sequence, so real multi-day persistence
  (lulls, squalls) comes through.
- **Summary stats**: mean/median/std/5th/95th percentile/min/max passage
  time in days, printed to stdout.
- **`monte_carlo_era5_histogram.png`**: histogram of the 5000 trial outcomes.

Two safety valves worth knowing about: `MAX_DAYS = 200` discards any trial
that never completes (pathological all-calm draw); and any trial whose walk
runs past `era5_wind_nov_jan.nc`'s last available date holds that last day's
wind constant for the remainder (flagged in stdout as "hit the data edge") --
in the most recent run this was 118 of 5000 trials (~2.4%).
