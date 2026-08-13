import sys
sys.path.insert(0, "../src")

import numpy as np
import matplotlib.pyplot as plt
from polar import Polar

boat = Polar("../data/hallberg-rassy40.pol")

# Plot a subset of representative wind speeds as classic polar curves
wind_speeds_to_plot = [6, 10, 14, 20, 30]
twa_range = np.linspace(0, 180, 181)  # degrees

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})

for tws in wind_speeds_to_plot:
    speeds = [boat.boat_speed(tws, twa) for twa in twa_range]
    theta = np.radians(twa_range)
    ax.plot(theta, speeds, label=f"{tws} kn TWS")

ax.set_theta_zero_location("N")   # 0 deg TWA (wind ahead) points "up"
ax.set_theta_direction(-1)        # clockwise, like a real polar diagram
ax.set_thetamin(0)
ax.set_thetamax(180)
ax.set_title("Hallberg-Rassy 40 Polar Diagram", pad=30)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
ax.set_rlabel_position(135)

plt.tight_layout()
plt.savefig("hr40_polar_diagram.png", dpi=150)
print("Saved hr40_polar_diagram.png")
