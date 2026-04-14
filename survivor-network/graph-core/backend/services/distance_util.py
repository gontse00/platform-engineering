"""Haversine distance utility for coordinate-based resource ranking.

Used by the routing service to prefer nearby resources when the user
has shared their location.  No external dependencies — pure math.
"""

from __future__ import annotations

import math
from typing import Any

# Earth radius in kilometres
_EARTH_RADIUS_KM = 6_371.0


def haversine_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Return great-circle distance in km between two (lat, lon) pairs."""
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return _EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def extract_coords(node_or_meta: dict[str, Any]) -> tuple[float, float] | None:
    """Try to pull (lat, lon) from a node dict or its metadata.

    Supports both:
      - top-level ``lat`` / ``lon`` (raw seed metadata)
      - nested ``metadata.lat`` / ``metadata.lon``
    Returns ``None`` if coordinates are absent or invalid.
    """
    for source in (node_or_meta, node_or_meta.get("metadata") or {}):
        lat = source.get("lat")
        lon = source.get("lon")
        if lat is not None and lon is not None:
            try:
                return (float(lat), float(lon))
            except (TypeError, ValueError):
                continue
    return None


def distance_score(distance_km: float) -> float:
    """Convert a distance in km into a 0.0–0.25 proximity bonus.

    Scoring bands (tuned for the Gauteng metro area):
      <=  5 km  →  0.25  (walking / short taxi)
      <= 10 km  →  0.20
      <= 20 km  →  0.15
      <= 40 km  →  0.10
      <= 80 km  →  0.05
      >  80 km  →  0.00
    """
    if distance_km <= 5:
        return 0.25
    if distance_km <= 10:
        return 0.20
    if distance_km <= 20:
        return 0.15
    if distance_km <= 40:
        return 0.10
    if distance_km <= 80:
        return 0.05
    return 0.0
