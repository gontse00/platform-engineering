"""Deterministic location resolver for known Gauteng areas.

Maps common place names to approximate GPS coordinates for local/dev use.
These are NOT precise emergency locations — they are suburb-center approximations
for development, testing, and resource matching.

Do not use for real emergency dispatch without proper geocoding.
"""

# Approximate center coordinates for known Gauteng areas
_KNOWN_LOCATIONS: dict[str, tuple[float, float]] = {
    "randburg": (-26.094, 28.006),
    "hillbrow": (-26.192, 28.048),
    "alexandra": (-26.108, 28.089),
    "tembisa": (-26.001, 28.227),
    "soweto": (-26.228, 27.905),
    "benoni": (-26.188, 28.321),
    "centurion": (-25.860, 28.190),
    "boksburg": (-26.212, 28.256),
    "vosloorus": (-26.350, 28.200),
    "daveyton": (-26.154, 28.412),
    "midrand": (-25.987, 28.127),
    "diepkloof": (-26.243, 27.896),
    "katlehong": (-26.345, 28.151),
    "johannesburg": (-26.204, 28.047),
    "pretoria": (-25.746, 28.188),
    "germiston": (-26.220, 28.170),
    "mamelodi": (-25.720, 28.396),
    "orlando west": (-26.229, 27.905),
    "sunnyside": (-25.756, 28.209),
}


def resolve_location(location_text: str | None) -> tuple[float | None, float | None]:
    """Resolve location_text to approximate (latitude, longitude).

    Returns (None, None) if location is not recognized.
    """
    if not location_text:
        return None, None

    lower = location_text.lower().strip()

    # Direct match
    if lower in _KNOWN_LOCATIONS:
        return _KNOWN_LOCATIONS[lower]

    # Substring match (e.g., "near Randburg" or "Hillbrow, Johannesburg")
    for name, coords in _KNOWN_LOCATIONS.items():
        if name in lower:
            return coords

    return None, None
