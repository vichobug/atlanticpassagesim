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
   This downloads 10 years of Nov-Feb daily-mean 10m wind over the route
   corridor to `data/era5_wind_nov_jan.nc` (gitignored -- regenerate via this
   script rather than committing it). CDS request queueing can take anywhere
   from minutes to a couple hours depending on system load.
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
food per person per day -- bluewater-cruising rules of thumb; fuel is not
modeled, since engine hours on this route depend far more on tactics than on
passage length) live in `src/provisioning.py`.

```
cd notebooks
python provisioning_plan.py
```
