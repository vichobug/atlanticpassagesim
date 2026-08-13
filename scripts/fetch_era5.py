"""
fetch_era5.py

One-time download of ERA5 10m wind reanalysis data over the Las Palmas ->
Rodney Bay trade-wind corridor, for the last 10 Nov-Jan trade-wind seasons
(with a Feb-Mar buffer so late-season/slow passages don't run off the edge
of the data -- see notebooks/monte_carlo_era5.py).

The CDS request takes year and month as independent lists (a full cross
product), so a single request can't express "Feb-Mar of the year AFTER each
Nov-Dec season" -- year=2016/month=01-03 already covers the buffer following
the 2015 Nov-Dec season, but the final season (Nov-Dec 2024) needs Jan-Mar
2025 as its buffer, which isn't reachable by adding 2025 to YEARS (that would
also request Nov-Dec 2025, which doesn't exist yet). So this fetches the main
Nov-Dec-Jan-Feb-Mar cross product for YEARS, plus a second, separate
buffer-only request for BUFFER_YEAR's Jan-Mar, and concatenates the two.

Requires a Copernicus Climate Data Store (CDS) account and API key -- see
the "Phase 3 setup" section in README.md for how to create one and configure
~/.cdsapirc before running this script.

Downloads hourly u/v wind at synoptic hours (00/06/12/18 UTC) rather than all
24 hours/day, then resamples to a daily mean locally -- this keeps the
download small while giving full control/transparency over what "daily mean"
means, rather than relying on a separate CDS-side daily-statistics product.

Usage:
    python fetch_era5.py
"""

import sys
sys.path.insert(0, "../src")

import cdsapi
import xarray as xr

from route import generate_waypoints

OUTPUT_PATH = "../data/era5_wind_nov_jan.nc"
RAW_DOWNLOAD_PATH = "../data/era5_wind_raw_hourly.nc"
RAW_BUFFER_DOWNLOAD_PATH = "../data/era5_wind_raw_hourly_buffer.nc"

YEARS = [str(y) for y in range(2015, 2025)]
MONTHS = ["11", "12", "01", "02", "03"]  # Nov, Dec, Jan (season) + Feb-Mar (buffer)
DAYS = [f"{d:02d}" for d in range(1, 32)]
TIMES = ["00:00", "06:00", "12:00", "18:00"]

# The final season's (Nov-Dec of YEARS[-1]) own Feb-Mar buffer -- see module
# docstring for why this can't just be folded into YEARS/MONTHS above.
BUFFER_YEAR = str(int(YEARS[-1]) + 1)
BUFFER_MONTHS = ["01", "02", "03"]

AREA_MARGIN_DEG = 3.0  # buffer around the route corridor's lat/lon bounds


def compute_area():
    """[N, W, S, E] bounding box covering the route corridor plus a margin."""
    waypoints = generate_waypoints()
    lats = [w[0] for w in waypoints]
    lons = [w[1] for w in waypoints]
    north = max(lats) + AREA_MARGIN_DEG
    south = min(lats) - AREA_MARGIN_DEG
    west = min(lons) - AREA_MARGIN_DEG
    east = max(lons) + AREA_MARGIN_DEG
    return [north, west, south, east]


def build_request(area, years, months):
    return {
        "product_type": "reanalysis",
        "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
        "year": years,
        "month": months,
        "day": DAYS,
        "time": TIMES,
        "area": area,
        "data_format": "netcdf",
    }


def fetch():
    area = compute_area()
    client = cdsapi.Client()

    print(f"Requesting ERA5 wind over area [N, W, S, E] = {area}")
    print(f"Years: {YEARS[0]}-{YEARS[-1]}, months: {MONTHS}, times: {TIMES}")
    main_request = build_request(area, YEARS, MONTHS)
    client.retrieve("reanalysis-era5-single-levels", main_request, RAW_DOWNLOAD_PATH)
    print(f"Downloaded raw hourly data to {RAW_DOWNLOAD_PATH}")

    print(f"Requesting buffer year {BUFFER_YEAR}, months: {BUFFER_MONTHS} "
          f"(Feb-Mar buffer for the {YEARS[-1]} Nov-Dec season)")
    buffer_request = build_request(area, [BUFFER_YEAR], BUFFER_MONTHS)
    client.retrieve("reanalysis-era5-single-levels", buffer_request, RAW_BUFFER_DOWNLOAD_PATH)
    print(f"Downloaded raw buffer hourly data to {RAW_BUFFER_DOWNLOAD_PATH}")

    ds_main = xr.open_dataset(RAW_DOWNLOAD_PATH).rename({"valid_time": "time"})
    ds_buffer = xr.open_dataset(RAW_BUFFER_DOWNLOAD_PATH).rename({"valid_time": "time"})
    ds = xr.concat([ds_main, ds_buffer], dim="time").sortby("time")

    daily = ds.resample(time="1D").mean()
    daily.to_netcdf(OUTPUT_PATH)
    print(f"Saved daily-mean wind field to {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch()
