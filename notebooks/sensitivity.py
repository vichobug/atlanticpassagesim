"""
sensitivity.py

Phase 5: how much do results actually depend on two choices the sailor
controls -- departure month and crew size?

Departure month: re-runs the Phase 3 historical-passage Monte Carlo three
times, restricting eligible start dates to Nov-only, Dec-only, and Jan-only
respectively, and compares the resulting passage-time distributions. The
main simulation pools all three months together; this checks whether that
pooling is hiding a meaningfully different risk profile for an earlier vs.
later departure.

Crew size: unlike departure month, this doesn't need a re-simulation --
water/food scale linearly with crew_size in provisioning.py, and fuel
doesn't depend on crew_size at all -- so this just tabulates
plan_for_percentile() across a few crew sizes for comparison.
"""

import sys
sys.path.insert(0, "../src")

import numpy as np

from monte_carlo_era5 import run_simulation
from provisioning import plan_for_percentile

MONTHS_TO_COMPARE = [("November", [11]), ("December", [12]), ("January", [1])]
N_TRIALS_PER_MONTH = 2000  # smaller than the pooled 5000 -- fewer start dates per month

PERCENTILE = 95
CONTINGENCY_DAYS = 3.0
CREW_SIZES_TO_COMPARE = [2, 4, 6]


def month_sensitivity():
    print("Departure-month sensitivity")
    print("-" * 70)
    print(f"{'Month':<10} {'n':>5} {'mean':>7} {'median':>8} {'5th pct':>9} {'95th pct':>9} {'max':>6}")

    results = {}
    for label, months in MONTHS_TO_COMPARE:
        passage_days, _, _ = run_simulation(n_trials=N_TRIALS_PER_MONTH, verbose=False, start_months=months)
        results[label] = passage_days
        p5, p95 = np.percentile(passage_days, [5, 95])
        print(f"{label:<10} {len(passage_days):>5} {np.mean(passage_days):>7.1f} "
              f"{np.median(passage_days):>8.1f} {p5:>9.1f} {p95:>9.1f} {passage_days.max():>6.0f}")

    print()
    return results


def crew_size_sensitivity(passage_days):
    print("Crew-size sensitivity (at the planned 95th-percentile sizing)")
    print("-" * 70)
    print(f"{'Crew':>5} {'days':>6} {'water (L)':>10} {'food (kg)':>10} {'fuel (L)':>9}")
    for crew_size in CREW_SIZES_TO_COMPARE:
        plan = plan_for_percentile(passage_days, crew_size, percentile=PERCENTILE, contingency_days=CONTINGENCY_DAYS)
        print(f"{crew_size:>5} {plan.planned_days:>6.1f} {plan.water_liters:>10.0f} "
              f"{plan.food_kg:>10.0f} {plan.fuel_liters:>9.0f}")
    print()


def main():
    month_results = month_sensitivity()

    means = {label: np.mean(days) for label, days in month_results.items()}
    spread = max(means.values()) - min(means.values())
    slowest = max(means, key=means.get)
    print(f"Mean passage time spans {spread:.1f} days across departure months "
          f"(slowest: {slowest}, {means[slowest]:.1f} days).")
    print("If that spread is small relative to the pooled distribution's own std dev,")
    print("the pooled Nov-Jan simulation used elsewhere in this project is a reasonable")
    print("single distribution to provision against; if it's large, provisioning should")
    print("be sized per-month instead of pooling all three together.\n")

    # Crew-size table uses the full pooled (all-months) distribution, matching
    # what provisioning_plan.py actually plans against.
    pooled_passage_days, _, _ = run_simulation(verbose=False)
    print(f"(Pooled Nov-Jan std dev: {np.std(pooled_passage_days):.1f} days, for comparison.)\n")
    crew_size_sensitivity(pooled_passage_days)

    print("Water and food scale linearly with crew size, as expected. Fuel doesn't --")
    print("it's a boat-level rate (see src/provisioning.py), not a per-person one.")


if __name__ == "__main__":
    main()
