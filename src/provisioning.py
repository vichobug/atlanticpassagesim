"""
provisioning.py

Turns a simulated passage-time distribution into a food/water/fuel
provisioning plan, sized to a chosen percentile of passage time plus a fixed
contingency buffer -- not the mean, since provisioning for the average case
means running short on every slower-than-average passage.

Consumption rates are bluewater-cruising rules of thumb (per person per day):
    water: 4 L  (drinking + cooking; excludes washing -- assumes a watermaker
                 or strict rationing is not being modeled, just baseline need)
    food:  1.8 kg (dry-provisions equivalent weight)
    fuel:  not modeled -- an ARC-route trade-wind passage is primarily sailed,
           and engine hours depend on tactics (calms motored through) far more
           than on passage length, so a days-based rate would be misleading.
"""

from dataclasses import dataclass

import numpy as np

WATER_L_PER_PERSON_DAY = 4.0
FOOD_KG_PER_PERSON_DAY = 1.8


@dataclass
class ProvisioningPlan:
    crew_size: int
    percentile: float
    contingency_days: float
    sim_days_at_percentile: float
    planned_days: float
    water_liters: float
    food_kg: float


def plan_for_percentile(
    passage_days: np.ndarray,
    crew_size: int,
    percentile: float = 95,
    contingency_days: float = 3.0,
) -> ProvisioningPlan:
    """Build a provisioning plan sized to a percentile of simulated passage
    time plus a fixed contingency buffer (e.g. for becalming, gear failure,
    or a diversion).

    percentile=100 (or passing np.max) sizes to the single worst simulated
    passage instead of a percentile cut.
    """
    if percentile >= 100:
        sim_days = float(np.max(passage_days))
    else:
        sim_days = float(np.percentile(passage_days, percentile))

    planned_days = sim_days + contingency_days

    return ProvisioningPlan(
        crew_size=crew_size,
        percentile=percentile,
        contingency_days=contingency_days,
        sim_days_at_percentile=sim_days,
        planned_days=planned_days,
        water_liters=planned_days * crew_size * WATER_L_PER_PERSON_DAY,
        food_kg=planned_days * crew_size * FOOD_KG_PER_PERSON_DAY,
    )


def format_plan(plan: ProvisioningPlan) -> str:
    pct_label = "worst-case (max)" if plan.percentile >= 100 else f"{plan.percentile:.0f}th percentile"
    lines = [
        f"Provisioning plan -- crew of {plan.crew_size}, sized to {pct_label} passage time",
        "-" * 60,
        f"Simulated passage time ({pct_label}): {plan.sim_days_at_percentile:.1f} days",
        f"Contingency buffer:                  +{plan.contingency_days:.1f} days",
        f"Planned provisioning duration:        {plan.planned_days:.1f} days",
        "",
        f"Water: {plan.water_liters:.0f} L  ({WATER_L_PER_PERSON_DAY:.1f} L/person/day)",
        f"Food:  {plan.food_kg:.0f} kg  ({FOOD_KG_PER_PERSON_DAY:.1f} kg/person/day)",
    ]
    return "\n".join(lines)
