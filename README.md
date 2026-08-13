# Atlantic Passage Sim

A probabilistic passage-provisioning tool for offshore sailing routes. Uses
Monte Carlo simulation over a boat's polar (speed) model and wind data to
estimate passage-time distributions and provisioning needs.

**Test case**: the Atlantic trade-wind route from Las Palmas (Gran Canaria)
to Rodney Bay (St Lucia) -- the classic ARC rally route, ~2600-2700 nm --
sailed on a Hallberg-Rassy 40 (bluewater cruiser, fin keel, 36.23 ft LWL).

## Project structure

- `data/hallberg-rassy40.pol` -- real polar data (TWA x TWS -> boat speed)
- `src/polar.py` -- `Polar` class: parses `.pol` files, interpolated boat-speed lookup
- `src/route.py` -- rhumb-line route geometry (Las Palmas -> Rodney Bay)
- `src/wind_data.py` -- loads ERA5 wind NetCDF, converts u/v to TWS/TWA
- `scripts/fetch_era5.py` -- one-time ERA5 wind data download (see setup below)
- `notebooks/plot_polar.py` -- polar diagram plot
- `notebooks/monte_carlo_toy.py` -- Phase 2: Monte Carlo with synthetic i.i.d. daily wind
- `notebooks/monte_carlo_era5.py` -- Phase 3: Monte Carlo sampling real historical passages
- `src/provisioning.py` -- Phase 4: turns a passage-time distribution into a food/water plan
- `notebooks/provisioning_plan.py` -- Phase 4: runs the Phase 3 simulation and prints a provisioning plan

## Setup

```
pip install -r requirements.txt
```

## Phase 3: ERA5 wind data setup

Phase 3 replaces synthetic wind with real ERA5 reanalysis data, and replaces
independent daily draws with **historical-passage sampling**: each Monte
Carlo trial picks a random historical start date and walks day-by-day through
that actual historical wind sequence, so real multi-day weather persistence
(lulls, squally patches) comes through naturally.

To fetch the data, you need a free Copernicus Climate Data Store (CDS) account:

1. Register at https://cds.climate.copernicus.eu and log in.
2. Go to your CDS user profile page and copy your API key.
3. Create `~/.cdsapirc` (in your home directory, **not** in this repo) with:
   ```
   url: https://cds.climate.copernicus.eu/api
   key: <your-api-key>
   ```
4. Open the [ERA5 hourly single-levels dataset page](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels)
   and click through to **accept the dataset's license/terms**. This is a
   common gotcha -- the API call fails with a permissions error until you've
   done this once, even with a valid API key.
5. Run the fetch (from `scripts/`):
   ```
   cd scripts
   python fetch_era5.py
   ```
   This makes two CDS requests -- 10 years of Nov-Mar daily-mean 10m wind
   over the route corridor, plus a Jan-Mar buffer request for the year after
   the last season (so the final season has a real buffer to walk into
   instead of falling off the edge of the data) -- and saves the combined
   result to `data/era5_wind_nov_jan.nc` (gitignored -- regenerate via this
   script rather than committing it). CDS request queueing can take anywhere
   from minutes to a couple hours depending on system load, per request.
6. Once the data file exists, run the Monte Carlo simulation:
   ```
   cd notebooks
   python monte_carlo_era5.py
   ```

## Phase 4: provisioning plan

Turns the Phase 3 passage-time distribution into a food/water plan, sized to
the 95th percentile of simulated passage time (not the mean -- provisioning
for the average case leaves a coin-flip's worth of crews short) plus a fixed
contingency buffer for the unexpected (becalming, gear failure, diversion).

Crew size, percentile, and contingency buffer are configured at the top of
`notebooks/provisioning_plan.py`. Consumption rates (4 L water and 1.8 kg
food per person per day -- bluewater-cruising rules of thumb; 12.5 L/day
fuel, a boat-level ARC rule of thumb rather than something derived from this
route's simulated wind, since the passage-time simulation doesn't track
per-trial calm/motoring days) live in `src/provisioning.py`.

```
cd notebooks
python provisioning_plan.py
```

## Validation

Simulated passage time (5000 trials, HR40, corrected polar table, full
Nov-Mar ERA5 buffer): **mean 18.0 days, median 17.0, 5th-95th pct 15-22
days, max 26 days**.

The real ARC's Las Palmas -> Rodney Bay crossing is widely reported at
**18-21 days average** across the whole (mixed-boat-type) fleet -- the
simulated mean falls right inside that band. A modest cruising boat in the
2003 ARC ("Albatros") finished in 16d 5h, close to this simulation's median;
the fastest-ever crossing (8d 6h, the maxi racer *Rambler 88* in 2016) is
an extreme-performance outlier not comparable to a cruising monohull like
the HR40 and isn't expected to match. Real ARC skippers also commonly
report motoring through 10-20% of the crossing and budgeting 200-400 L of
diesel for it -- the basis for this project's fuel-provisioning rate (see
Phase 4 above).

Sources:
[World Cruising Club ARC overview](https://worldcruising.com/events/arc),
[ARC 2003 results](https://www.yumpu.com/en/document/view/34079409/arc-2003-results-world-cruising-club),
[NoForeignLand: How much diesel does a cruising sailboat really need?](https://blog.noforeignland.com/how-much-diesel-does-a-cruising-sailboat-really-need/)
