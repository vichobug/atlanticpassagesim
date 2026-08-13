"""
wind_data.py

Loads a downloaded ERA5 daily-mean 10m wind NetCDF file and provides a
lookup function that converts gridded u/v wind components into (TWS, TWA)
at a given lat/lon/date, relative to the boat's course bearing.

Expects a dataset with variables "u10"/"v10" (m/s) and coordinates
"latitude"/"longitude"/"time" -- the layout produced by fetch_era5.py.
"""

import math

import numpy as np
import xarray as xr

MS_TO_KNOTS = 1.94384


def load_wind_field(path: str = "data/era5_wind_nov_jan.nc") -> xr.Dataset:
    return xr.open_dataset(path)


def wind_at(ds: xr.Dataset, lat: float, lon: float, date) -> tuple:
    """Nearest-neighbor lookup of (tws_knots, wind_from_bearing_deg_true) at lat/lon/date.

    Space and time lookups both use nearest-neighbor: ERA5's 0.25 deg grid
    (~15 nm) is well below the ~100nm route-waypoint spacing and the synoptic
    scale that matters for this route, so bilinear interpolation isn't worth
    the added complexity for a v1 model.
    """
    date = np.datetime64(date, "D")
    point = ds.sel(latitude=lat, longitude=lon, time=date, method="nearest")

    u = float(point["u10"])
    v = float(point["v10"])

    speed_ms = math.hypot(u, v)
    tws_knots = speed_ms * MS_TO_KNOTS

    # u/v give the direction wind is blowing TOWARD; sailors care about the
    # direction it's blowing FROM (standard meteorological convention).
    wind_from_deg = (270 - math.degrees(math.atan2(v, u))) % 360

    return tws_knots, wind_from_deg


def wind_to_twa(wind_from_bearing_deg: float, course_bearing_deg: float) -> float:
    """Signed angle (-180..180) between the wind's true bearing and the boat's course.

    polar.boat_speed() already folds any TWA into 0-180 symmetric port/
    starboard (see src/polar.py's TWA folding), so this doesn't need to do
    that folding itself -- it just needs a correctly-signed angle.
    """
    return (wind_from_bearing_deg - course_bearing_deg + 180) % 360 - 180


def tws_twa_at(ds: xr.Dataset, lat: float, lon: float, date, course_bearing_deg: float) -> tuple:
    tws, wind_from = wind_at(ds, lat, lon, date)
    twa = wind_to_twa(wind_from, course_bearing_deg)
    return tws, twa


if __name__ == "__main__":
    # Sanity check against a small synthetic dataset (no real ERA5 file needed):
    # wind blowing FROM due north (u=0, v=-speed): a boat heading north (course
    # 000) is sailing INTO that wind -> headwind, TWA ~= 0. A boat heading
    # south (course 180) has that same wind pushing from behind -> TWA ~= 180.
    lat = np.array([20.0])
    lon = np.array([-40.0])
    time = np.array([np.datetime64("2020-01-15", "ns")])

    wind_speed_ms = 10.0
    # wind FROM the north means it blows TOWARD the south: u=0, v=-speed
    u10 = np.array([[[0.0]]])
    v10 = np.array([[[-wind_speed_ms]]])

    synthetic_ds = xr.Dataset(
        {
            "u10": (["time", "latitude", "longitude"], u10),
            "v10": (["time", "latitude", "longitude"], v10),
        },
        coords={"time": time, "latitude": lat, "longitude": lon},
    )

    tws, wind_from = wind_at(synthetic_ds, 20.0, -40.0, "2020-01-15")
    print(f"Synthetic wind FROM north: TWS={tws:.2f} kn, wind_from={wind_from:.1f} deg (expect ~0)")

    twa_headwind = wind_to_twa(wind_from, course_bearing_deg=0.0)
    twa_astern = wind_to_twa(wind_from, course_bearing_deg=180.0)
    print(f"Course 000 (heading N, wind from N): TWA={twa_headwind:.1f} deg (expect ~0, on the nose)")
    print(f"Course 180 (heading S, wind from N): TWA={abs(twa_astern):.1f} deg (expect ~180, dead astern)")
