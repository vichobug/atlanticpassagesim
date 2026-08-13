"""
fetch_era5.py

One-time download of ERA5 10m wind reanalysis data over the Las Palmas ->
Rodney Bay trade-wind corridor, for the last 10 Nov-Jan trade-wind seasons
(with a Feb buffer so late-season passages don't run off the edge of the
data -- see notebooks/monte_carlo_era5.py).

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

YEARS = [str(y) for y in range(2015, 2025)]
MONTHS = ["11", "12", "01", "02"]  # Nov, Dec, Jan (season) + Feb (buffer)
DAYS = [f"{d:02d}" for d in range(1, 32)]
TIMES = ["00:00", "06:00", "12:00", "18:00"]

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


def build_request(area):
    return {
        "product_type": "reanalysis",
        "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
        "year": YEARS,
        "month": MONTHS,
        "day": DAYS,
        "time": TIMES,
        "area": area,
        "data_format": "netcdf",
    }


def fetch():
    area = compute_area()
    print(f"Requesting ERA5 wind over area [N, W, S, E] = {area}")
    print(f"Years: {YEARS[0]}-{YEARS[-1]}, months: {MONTHS}, times: {TIMES}")

    client = cdsapi.Client()
    request = build_request(area)
    client.retrieve("reanalysis-era5-single-levels", request, RAW_DOWNLOAD_PATH)
    print(f"Downloaded raw hourly data to {RAW_DOWNLOAD_PATH}")

    ds = xr.open_dataset(RAW_DOWNLOAD_PATH).rename({"valid_time": "time"})
    daily = ds.resample(time="1D").mean()
    daily.to_netcdf(OUTPUT_PATH)
    print(f"Saved daily-mean wind field to {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch()
