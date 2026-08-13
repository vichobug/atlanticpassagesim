"""
export_site_data.py

Phase 6: runs the pooled Phase 3 simulation and the Phase 5 departure-month
sensitivity, and dumps everything the GitHub Pages showcase site
(docs/index.html) needs as one JSON file -- the raw passage-time arrays (so
the site can compute any percentile client-side, not just the ones printed
here), plus summary stats and the real-ARC validation numbers.

The site has no backend, so this is a build step: run it, commit the
resulting docs/data.json, push. It is not regenerated automatically.
"""

import json
import sys
sys.path.insert(0, "../src")

import numpy as np

import route
from monte_carlo_era5 import run_simulation
from provisioning import WATER_L_PER_PERSON_DAY, FOOD_KG_PER_PERSON_DAY, FUEL_L_PER_DAY

OUTPUT_PATH = "../docs/data.json"

MONTHS_TO_COMPARE = [("November", [11]), ("December", [12]), ("January", [1])]
N_TRIALS_PER_MONTH = 2000


def summarize(passage_days):
    p5, p95 = np.percentile(passage_days, [5, 95])
    return {
        "n": int(len(passage_days)),
        "mean": round(float(np.mean(passage_days)), 2),
        "median": round(float(np.median(passage_days)), 2),
        "std": round(float(np.std(passage_days)), 2),
        "p5": round(float(p5), 2),
        "p95": round(float(p95), 2),
        "min": int(passage_days.min()),
        "max": int(passage_days.max()),
    }


def main():
    print("Running pooled Nov-Jan simulation (5000 trials)...")
    pooled_days, route_distance_nm, _ = run_simulation(verbose=False)

    month_data = {}
    for label, months in MONTHS_TO_COMPARE:
        print(f"Running {label}-only simulation ({N_TRIALS_PER_MONTH} trials)...")
        days, _, _ = run_simulation(n_trials=N_TRIALS_PER_MONTH, verbose=False, start_months=months)
        month_data[label] = {
            "passage_days": days.tolist(),
            "summary": summarize(days),
        }

    data = {
        "route": {
            "start": "Las Palmas, Gran Canaria",
            "end": "Rodney Bay, St Lucia",
            "distance_nm": round(route_distance_nm, 1),
            "bearing_deg": round(route.course_bearing_deg(), 1),
        },
        "boat": "Hallberg-Rassy 40",
        "pooled": {
            "passage_days": pooled_days.tolist(),
            "summary": summarize(pooled_days),
        },
        "by_month": month_data,
        "provisioning_rates": {
            "water_l_per_person_day": WATER_L_PER_PERSON_DAY,
            "food_kg_per_person_day": FOOD_KG_PER_PERSON_DAY,
            "fuel_l_per_day": FUEL_L_PER_DAY,
        },
        "validation": {
            "real_arc_avg_days_low": 18,
            "real_arc_avg_days_high": 21,
            "note": "Widely-cited real ARC average crossing time for the whole "
                    "(mixed-boat-type) fleet; the simulated mean/median fall inside "
                    "this band. See README.md Validation section for sources.",
        },
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
