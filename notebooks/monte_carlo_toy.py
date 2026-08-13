"""
monte_carlo_toy.py

Phase 2: toy Monte Carlo passage simulation using SYNTHETIC wind data.

Each simulated day draws an independent (TWS, TWA) pair from distributions
roughly matching Atlantic trade-wind conditions, looks up boat speed via
polar.boat_speed(), and accumulates distance until the route length is
covered. Repeating this many times builds a distribution of passage times.

NOTE: daily wind draws are i.i.d. here. Real trade-wind passages have
multi-day correlated weather systems (a squally patch, a multi-day lull),
so this toy model understates the spread of real passage times -- see the
printed caveat at the end of this script.
"""

import sys
sys.path.insert(0, "../src")

import numpy as np
import matplotlib.pyplot as plt
from polar import Polar

ROUTE_DISTANCE_NM = 2700
N_TRIALS = 5000
MAX_DAYS = 200  # safety cap against pathological all-calm draws

# Synthetic trade-wind TWS: gamma distribution, mean ~16 kn, long right tail
# (occasional squalls) and a floor near 0 (occasional calms).
TWS_SHAPE = 4.0
TWS_SCALE = 4.0  # mean = shape * scale = 16 kn

# Synthetic TWA: broad reach centered ~120 deg, with spread; clipped to [0, 180].
TWA_MEAN = 120.0
TWA_STD = 20.0

rng = np.random.default_rng(seed=42)


def simulate_passage(boat: Polar) -> int:
    distance_covered = 0.0
    days = 0
    while distance_covered < ROUTE_DISTANCE_NM and days < MAX_DAYS:
        tws = rng.gamma(TWS_SHAPE, TWS_SCALE)
        twa = np.clip(rng.normal(TWA_MEAN, TWA_STD), 0, 180)
        speed_kn = boat.boat_speed(tws, twa)
        distance_covered += speed_kn * 24.0
        days += 1
    return days


def main():
    boat = Polar("../data/hallberg-rassy40.pol")

    passage_days = np.array([simulate_passage(boat) for _ in range(N_TRIALS)])

    hit_cap = np.sum(passage_days >= MAX_DAYS)
    if hit_cap:
        print(f"WARNING: {hit_cap} trial(s) hit the {MAX_DAYS}-day safety cap "
              f"(likely repeated near-calm draws) -- excluding from stats.\n")
        passage_days = passage_days[passage_days < MAX_DAYS]

    mean_d = np.mean(passage_days)
    median_d = np.median(passage_days)
    std_d = np.std(passage_days)
    p5, p95 = np.percentile(passage_days, [5, 95])
    min_d, max_d = passage_days.min(), passage_days.max()

    print(f"Monte Carlo passage-time simulation ({len(passage_days)} trials)")
    print(f"Route: {ROUTE_DISTANCE_NM} nm, synthetic trade winds "
          f"(TWS ~ Gamma(mean={TWS_SHAPE * TWS_SCALE:.0f} kn), "
          f"TWA ~ N({TWA_MEAN:.0f}, {TWA_STD:.0f} deg))")
    print("-" * 60)
    print(f"Mean:        {mean_d:.2f} days")
    print(f"Median:      {median_d:.2f} days")
    print(f"Std dev:     {std_d:.2f} days")
    print(f"5th pct:     {p5:.2f} days")
    print(f"95th pct:    {p95:.2f} days")
    print(f"Min:         {min_d} days")
    print(f"Max:         {max_d} days")

    plt.figure(figsize=(9, 5.5))
    bins = np.arange(passage_days.min(), passage_days.max() + 2) - 0.5
    plt.hist(passage_days, bins=bins, color="#2f6690", edgecolor="white", alpha=0.9)
    plt.axvline(mean_d, color="black", linestyle="--", linewidth=1, label=f"mean = {mean_d:.1f} d")
    plt.axvline(median_d, color="red", linestyle=":", linewidth=1, label=f"median = {median_d:.1f} d")
    plt.xlabel("Passage time (days)")
    plt.ylabel("Number of trials")
    plt.title(f"Simulated Passage Time Distribution\nCanary Islands -> Caribbean, {ROUTE_DISTANCE_NM} nm, HR40 "
              f"({N_TRIALS} trials, synthetic wind)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("monte_carlo_toy_histogram.png", dpi=150)
    print("\nSaved monte_carlo_toy_histogram.png")

    print("\nCAVEAT: TWS/TWA are drawn independently each day (no day-to-day")
    print("weather correlation). Real trade-wind routes have multi-day systems")
    print("(persistent lulls, multi-day squally patches), so real passage-time")
    print("variance is very likely UNDERSTATED here -- this distribution should")
    print("look narrower than reality. Phase 3 (real wind data) should widen it.")


if __name__ == "__main__":
    main()
