"""
monte_carlo_era5.py

Phase 3: Monte Carlo passage simulation using REAL ERA5 wind data, sampling
real historical passages instead of independent daily draws.

Each trial picks a random historical start date (from the fetched Nov-Jan
seasons) and walks day-by-day through that actual historical wind sequence
along the route, looking up boat speed via polar.boat_speed() at each day's
position and historical wind. This captures real multi-day weather
persistence (lulls, squally patches) for free, since it's real weather -- not
a synthetic model -- unlike the Phase 2 toy simulation
(notebooks/monte_carlo_toy.py), which drew i.i.d. daily wind and understated
passage-time variance as a result.

Requires data/era5_wind_nov_jan.nc, produced by scripts/fetch_era5.py -- see
the "Phase 3 setup" section in README.md.
"""

import sys
sys.path.insert(0, "../src")

import numpy as np
import matplotlib.pyplot as plt

import route
from polar import Polar
from wind_data import load_wind_field, tws_twa_at

WIND_DATA_PATH = "../data/era5_wind_nov_jan.nc"
N_TRIALS = 5000
MAX_DAYS = 200  # safety cap against pathological all-calm draws

rng = np.random.default_rng(seed=42)


def get_available_start_dates(ds):
    """Historical dates (Nov, Dec, Jan only) valid as passage START days.

    The walk itself is allowed to read into the fetched Feb buffer -- see
    fetch_era5.py -- so a late-season start date doesn't run off the edge of
    the data for a normal-length passage.
    """
    months = ds["time.month"].values
    season_mask = np.isin(months, [11, 12, 1])
    return ds["time"].values[season_mask]


def simulate_passage(boat, ds, course_bearing, route_distance_nm, available_start_dates):
    start_date = rng.choice(available_start_dates)
    last_available_date = ds["time"].values.max()

    distance_covered = 0.0
    day_offset = 0
    hit_data_edge = False

    while distance_covered < route_distance_nm and day_offset < MAX_DAYS:
        current_date = start_date + np.timedelta64(day_offset, "D")
        if current_date > last_available_date:
            current_date = last_available_date
            hit_data_edge = True

        lat, lon = route.latlon_at_distance(distance_covered)
        tws, twa = tws_twa_at(ds, lat, lon, current_date, course_bearing)
        speed_kn = boat.boat_speed(tws, twa)
        distance_covered += speed_kn * 24.0
        day_offset += 1

    return day_offset, hit_data_edge, start_date


def main():
    boat = Polar("../data/hallberg-rassy40.pol")
    ds = load_wind_field(WIND_DATA_PATH)
    course_bearing = route.course_bearing_deg()
    route_distance_nm = route.total_route_distance_nm()
    available_start_dates = get_available_start_dates(ds)

    print(f"Loaded wind field: {ds['time'].values.min()} to {ds['time'].values.max()}")
    print(f"{len(available_start_dates)} possible historical start dates (Nov-Jan)")
    print(f"Route distance: {route_distance_nm:.1f} nm, course bearing: {course_bearing:.1f} deg\n")

    passage_days = []
    start_years_used = []
    edge_hits = 0

    for _ in range(N_TRIALS):
        days, hit_edge, start_date = simulate_passage(
            boat, ds, course_bearing, route_distance_nm, available_start_dates
        )
        passage_days.append(days)
        start_years_used.append(np.datetime64(start_date, "Y").astype(int) + 1970)
        if hit_edge:
            edge_hits += 1

    passage_days = np.array(passage_days)

    hit_cap = np.sum(passage_days >= MAX_DAYS)
    if hit_cap:
        print(f"WARNING: {hit_cap} trial(s) hit the {MAX_DAYS}-day safety cap -- excluding from stats.\n")
        passage_days = passage_days[passage_days < MAX_DAYS]

    if edge_hits:
        print(f"NOTE: {edge_hits} trial(s) ran past the end of the fetched wind data and "
              f"held the last available day's wind for their remaining days. If this count "
              f"is large, widen the Feb buffer in fetch_era5.py.\n")

    mean_d = np.mean(passage_days)
    median_d = np.median(passage_days)
    std_d = np.std(passage_days)
    p5, p95 = np.percentile(passage_days, [5, 95])
    min_d, max_d = passage_days.min(), passage_days.max()

    print(f"Monte Carlo passage-time simulation ({len(passage_days)} trials, real ERA5 wind)")
    print(f"Route: Las Palmas -> Rodney Bay, {route_distance_nm:.0f} nm")
    print("-" * 60)
    print(f"Mean:        {mean_d:.2f} days")
    print(f"Median:      {median_d:.2f} days")
    print(f"Std dev:     {std_d:.2f} days")
    print(f"5th pct:     {p5:.2f} days")
    print(f"95th pct:    {p95:.2f} days")
    print(f"Min:         {min_d} days")
    print(f"Max:         {max_d} days")

    years, counts = np.unique(start_years_used, return_counts=True)
    print(f"\nHistorical start years sampled: {dict(zip(years.tolist(), counts.tolist()))}")

    plt.figure(figsize=(9, 5.5))
    bins = np.arange(passage_days.min(), passage_days.max() + 2) - 0.5
    plt.hist(passage_days, bins=bins, color="#2f6690", edgecolor="white", alpha=0.9)
    plt.axvline(mean_d, color="black", linestyle="--", linewidth=1, label=f"mean = {mean_d:.1f} d")
    plt.axvline(median_d, color="red", linestyle=":", linewidth=1, label=f"median = {median_d:.1f} d")
    plt.xlabel("Passage time (days)")
    plt.ylabel("Number of trials")
    plt.title(f"Simulated Passage Time Distribution (real ERA5 wind, historical passages)\n"
              f"Las Palmas -> Rodney Bay, {route_distance_nm:.0f} nm, HR40 ({N_TRIALS} trials)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("monte_carlo_era5_histogram.png", dpi=150)
    print("\nSaved monte_carlo_era5_histogram.png")

    print("\nWind is now historically persistent -- each trial walks a real consecutive")
    print("sequence of days from a randomly chosen historical passage, so real multi-day")
    print("weather systems (lulls, squally patches) carry through naturally. Expect a")
    print("visibly wider spread here than the Phase 2 toy simulation's i.i.d. daily draws.")


if __name__ == "__main__":
    main()
