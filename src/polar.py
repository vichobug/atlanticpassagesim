"""
polar.py

Parses a standard .pol polar file (TWA rows x TWS columns -> boat speed in knots)
and provides a boat-speed lookup function via 2D interpolation.

Polar file format (tab-separated):
    TWA\\TWS   0   4   6   8   10  12  ...
    0         0.0 0.0 0.0 ...
    5         0.0 0.3 0.4 ...
    ...
    180       0.0 2.0 3.0 ...

Usage:
    from polar import Polar
    boat = Polar("data/hallberg-rassy40.pol")
    speed = boat.boat_speed(tws=15, twa=110)   # knots
"""

import numpy as np
from scipy.interpolate import RegularGridInterpolator


class Polar:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.tws_grid, self.twa_grid, self.speed_table = self._parse(filepath)

        # RegularGridInterpolator expects points sorted ascending on each axis,
        # which our parsed grids already are (0->180 TWA, 0->60 TWS).
        # bounds_error=False + fill_value=None -> linear extrapolation at edges,
        # which we then clip manually to avoid nonsense values.
        self._interp = RegularGridInterpolator(
            (self.twa_grid, self.tws_grid),
            self.speed_table,
            method="linear",
            bounds_error=False,
            fill_value=None,
        )

    @staticmethod
    def _parse(filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        header = lines[0].split("\t")
        tws_grid = np.array([float(x) for x in header[1:]])  # skip "TWA\TWS" label

        twa_grid = []
        speed_rows = []
        for line in lines[1:]:
            parts = line.split("\t")
            twa_grid.append(float(parts[0]))
            speed_rows.append([float(x) for x in parts[1:]])

        twa_grid = np.array(twa_grid)
        speed_table = np.array(speed_rows)  # shape (n_twa, n_tws)

        return tws_grid, twa_grid, speed_table

    def boat_speed(self, tws: float, twa: float) -> float:
        """
        Return interpolated boat speed (knots) for a given true wind speed (kn)
        and true wind angle (degrees, 0-180; angles are mirrored port/starboard
        so 200 deg TWA behaves the same as 160 deg).

        tws is clipped to the polar's data range [0, max_tws] -- extreme storm
        wind speeds beyond what's in the table fall back to the fastest known
        (reefed) speed rather than extrapolating into nonsense.
        """
        # Fold TWA into 0-180 range (symmetric port/starboard)
        twa = abs(((twa + 180) % 360) - 180)

        # Clip TWS to table range (no sane extrapolation past a VPP's max wind)
        tws_clipped = np.clip(tws, self.tws_grid.min(), self.tws_grid.max())

        speed = self._interp([[twa, tws_clipped]])[0]
        return max(0.0, float(speed))

    def max_tws(self) -> float:
        return float(self.tws_grid.max())

    def max_twa(self) -> float:
        return float(self.twa_grid.max())


if __name__ == "__main__":
    # quick sanity check
    boat = Polar("../data/hallberg-rassy40.pol")
    tests = [(10, 45), (15, 90), (20, 120), (25, 150), (14, 40)]
    for tws, twa in tests:
        print(f"TWS={tws:>4} kn  TWA={twa:>4} deg  ->  boat speed = {boat.boat_speed(tws, twa):.2f} kn")
