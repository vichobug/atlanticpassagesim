"""
route.py

Rhumb-line (constant-bearing) geometry for the Las Palmas (Gran Canaria) ->
Rodney Bay (St Lucia) trade-wind route (~2700 nm).

Rhumb line is used instead of great circle: over this route's ~16 degrees of
latitude the two diverge by only ~1-2% in distance, and a rhumb line matches
how trade-wind passages are actually sailed (a near-constant compass heading),
which is exactly what "course bearing" needs to mean for TWA calculations
downstream in wind_data.py.

Because a rhumb line holds one constant bearing for its whole length,
latlon_at_distance() is a direct closed-form projection from the start point
-- it does not interpolate between waypoints. generate_waypoints() exists only
to define the ERA5 fetch bounding box and for optional plotting.
"""

import math

LAS_PALMAS = (28.15, -17.10)   # (lat, lon)
RODNEY_BAY = (14.08, -60.95)

EARTH_RADIUS_NM = 3440.065


def _rhumb_components(lat1, lon1, lat2, lon2):
    """Shared rhumb-line math: returns (distance_nm, bearing_deg)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1

    d_lambda = math.radians(lon2 - lon1)
    # shortest way round the globe
    if abs(d_lambda) > math.pi:
        d_lambda -= math.copysign(2 * math.pi, d_lambda)

    d_psi = math.log(math.tan(math.pi / 4 + phi2 / 2) / math.tan(math.pi / 4 + phi1 / 2))
    q = d_phi / d_psi if abs(d_psi) > 1e-12 else math.cos(phi1)

    distance_nm = math.sqrt(d_phi ** 2 + (q ** 2) * (d_lambda ** 2)) * EARTH_RADIUS_NM
    bearing_deg = math.degrees(math.atan2(d_lambda, d_psi)) % 360

    return distance_nm, bearing_deg


def rhumb_line_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    distance_nm, _ = _rhumb_components(lat1, lon1, lat2, lon2)
    return distance_nm


def rhumb_line_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    _, bearing_deg = _rhumb_components(lat1, lon1, lat2, lon2)
    return bearing_deg


def rhumb_line_destination(lat1: float, lon1: float, bearing_deg: float, distance_nm: float):
    """Given a start point, bearing, and distance, return the (lat, lon) reached."""
    phi1 = math.radians(lat1)
    lambda1 = math.radians(lon1)
    theta = math.radians(bearing_deg)
    delta = distance_nm / EARTH_RADIUS_NM  # angular distance

    phi2 = phi1 + delta * math.cos(theta)

    d_psi = math.log(math.tan(math.pi / 4 + phi2 / 2) / math.tan(math.pi / 4 + phi1 / 2))
    q = (phi2 - phi1) / d_psi if abs(d_psi) > 1e-12 else math.cos(phi1)

    d_lambda = delta * math.sin(theta) / q if abs(q) > 1e-12 else 0.0
    lambda2 = lambda1 + d_lambda

    lat2 = math.degrees(phi2)
    lon2 = ((math.degrees(lambda2) + 180) % 360) - 180
    return lat2, lon2


def total_route_distance_nm(start=LAS_PALMAS, end=RODNEY_BAY) -> float:
    return rhumb_line_distance_nm(start[0], start[1], end[0], end[1])


def course_bearing_deg(start=LAS_PALMAS, end=RODNEY_BAY) -> float:
    return rhumb_line_bearing_deg(start[0], start[1], end[0], end[1])


def latlon_at_distance(distance_nm: float, start=LAS_PALMAS, end=RODNEY_BAY):
    """Lat/lon reached after sailing distance_nm along the rhumb line from start.

    Clipped to the endpoint if distance_nm exceeds the total route length.
    """
    bearing = rhumb_line_bearing_deg(start[0], start[1], end[0], end[1])
    total = rhumb_line_distance_nm(start[0], start[1], end[0], end[1])
    distance_nm = min(distance_nm, total)
    return rhumb_line_destination(start[0], start[1], bearing, distance_nm)


def generate_waypoints(start=LAS_PALMAS, end=RODNEY_BAY, spacing_nm=100):
    """List of (lat, lon, dist_from_start_nm) evenly spaced along the rhumb line."""
    total = rhumb_line_distance_nm(start[0], start[1], end[0], end[1])
    waypoints = []
    dist = 0.0
    while dist < total:
        waypoints.append((*latlon_at_distance(dist, start, end), dist))
        dist += spacing_nm
    waypoints.append((*end, total))
    return waypoints


if __name__ == "__main__":
    dist = total_route_distance_nm()
    bearing = course_bearing_deg()
    print(f"Las Palmas -> Rodney Bay: {dist:.1f} nm, course bearing {bearing:.1f} deg")

    wps = generate_waypoints()
    lats = [w[0] for w in wps]
    lons = [w[1] for w in wps]
    print(f"{len(wps)} waypoints, lat range [{min(lats):.2f}, {max(lats):.2f}], "
          f"lon range [{min(lons):.2f}, {max(lons):.2f}]")

    # sanity check: midpoint distance should round-trip through latlon_at_distance
    mid_lat, mid_lon = latlon_at_distance(dist / 2)
    print(f"Midpoint (~{dist/2:.0f} nm along track): {mid_lat:.2f}, {mid_lon:.2f}")
