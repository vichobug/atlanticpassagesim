"""
provisioning.py

Turns a simulated passage-time distribution into a food/water/fuel
provisioning plan, sized to a chosen percentile of passage time plus a fixed
contingency buffer -- not the mean, since provisioning for the average case
means running short on every slower-than-average passage.

Consumption rates are bluewater-cruising rules of thumb:
    water: 4 L/person/day  (drinking + cooking; excludes washing -- assumes a
                            watermaker or strict rationing is not being
                            modeled, just baseline need)
    food:  1.8 kg/person/day  (dry-provisions equivalent weight)
    fuel:  a boat-level (not per-person) rate, not tied to this route's
           actual simulated wind -- the passage-time simulation doesn't track
           per-trial calm/motoring days, so this uses the commonly-cited ARC
           rule of thumb instead: most boats motor through ~10-20% of the
           crossing during calms, budgeting 200-400 L of diesel for a
           passage this length at a small cruising-diesel burn rate
           (~3.5 L/hr). FUEL_L_PER_DAY blends that into a flat per-day rate:
           0.15 motored fraction * 24 h/day * 3.5 L/hr ~= 12.5 L/day, which
           lands in the middle of that 200-400 L budget over a typical
           3-week passage. Check against your boat's actual tank capacity --
           if the planned total exceeds it, you're planning to sail through
           calms rather than motor, not carry extra fuel.
"""

from dataclasses import dataclass

import numpy as np

WATER_L_PER_PERSON_DAY = 4.0
FOOD_KG_PER_PERSON_DAY = 1.8
FUEL_L_PER_DAY = 12.5


@dataclass
class ProvisioningPlan:
    crew_size: int
    percentile: float
    contingency_days: float
    sim_days_at_percentile: float
    planned_days: float
    water_liters: float
    food_kg: float
    fuel_liters: float


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
        fuel_liters=planned_days * FUEL_L_PER_DAY,
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
        f"Fuel:  {plan.fuel_liters:.0f} L  ({FUEL_L_PER_DAY:.1f} L/day, boat-level -- ARC rule of thumb, "
        f"not simulated per-trial)",
    ]
    return "\n".join(lines)
