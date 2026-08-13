"""
provisioning_plan.py

Phase 4: turns the Phase 3 historical-passage Monte Carlo into a food/water
provisioning plan for a given crew size.

Reuses monte_carlo_era5.run_simulation() rather than re-implementing the
passage simulation, and sizes provisioning to the 95th percentile of
simulated passage time plus a fixed contingency buffer -- not the mean, so
the plan covers all but the slowest ~5% of historical-equivalent passages
rather than leaving a coin-flip's worth of crews short on food.
"""

import sys
sys.path.insert(0, "../src")

from monte_carlo_era5 import run_simulation
from provisioning import plan_for_percentile, format_plan

CREW_SIZE = 4
PERCENTILE = 95
CONTINGENCY_DAYS = 3.0


def main():
    passage_days, route_distance_nm, _ = run_simulation()

    plan = plan_for_percentile(
        passage_days,
        crew_size=CREW_SIZE,
        percentile=PERCENTILE,
        contingency_days=CONTINGENCY_DAYS,
    )

    print()
    print(format_plan(plan))

    print()
    print("For comparison, at other sizing choices:")
    for label, pct in [("median", 50), ("95th pct (planned)", 95), ("worst-case", 100)]:
        p = plan_for_percentile(passage_days, CREW_SIZE, percentile=pct, contingency_days=CONTINGENCY_DAYS)
        print(f"  {label:<20} {p.planned_days:5.1f} days  ->  {p.water_liters:6.0f} L water, "
              f"{p.food_kg:6.0f} kg food, {p.fuel_liters:5.0f} L fuel")


if __name__ == "__main__":
    main()
