"""Intake parsing service.

Now accepts pre-parsed data from chatbot-service to avoid redundant LLM calls.
Falls back to basic text extraction if no pre-parsed data is provided.

Coordinates (latitude/longitude) are preserved through the full parse result
so downstream routing and ranking can use them.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from models.graph import GraphNodeDB

logger = logging.getLogger(__name__)


@dataclass
class IntakeParseResult:
    message: str
    normalized_location: str | None
    primary_needs: list[str]
    derived_support_needs: list[str]
    normalized_barriers: list[str]
    # Coordinates — carried through from pre_parsed or request-level fields
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy: float | None = None
    location_source: str | None = None  # browser, manual, text_inferred


class IntakeService:
    """Intake parser that maps structured data into ontology labels."""

    @staticmethod
    def _resolve_known_label(db: Session, label: str, allowed_types: list[str]) -> str | None:
        """Look up a label in the graph to get the canonical version."""
        if not label:
            return None
        # Try exact match first
        node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label == label,
                GraphNodeDB.node_type.in_(allowed_types),
            )
            .first()
        )
        if node:
            return node.label

        # Try case-insensitive match
        node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label.ilike(label),
                GraphNodeDB.node_type.in_(allowed_types),
            )
            .first()
        )
        return node.label if node else None

    @staticmethod
    def parse_message(
        db: Session,
        message: str,
        explicit_location: str | None = None,
        pre_parsed: dict | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IntakeParseResult:
        """Parse intake from pre-parsed data or basic text extraction.

        Args:
            db: Database session for resolving graph labels.
            message: Raw user message text.
            explicit_location: Optional explicit location override.
            pre_parsed: Pre-parsed data from chatbot-service LLM.
                        Expected keys: location, primary_needs, barriers,
                                       incident_summary, immediate_danger, injury_status,
                                       latitude, longitude, location_accuracy, location_source
            latitude: Top-level latitude (fallback if not in pre_parsed).
            longitude: Top-level longitude (fallback if not in pre_parsed).
        """
        # Extract coordinates — prefer pre_parsed, fall back to top-level args
        coord_lat: float | None = None
        coord_lon: float | None = None
        coord_accuracy: float | None = None
        coord_source: str | None = None

        if pre_parsed:
            # Use pre-parsed data from chatbot-service (avoids LLM call)
            # Handle both Pydantic models and plain dicts
            if hasattr(pre_parsed, "model_dump"):
                pre_parsed = pre_parsed.model_dump()
            raw_location = pre_parsed.get("location") or explicit_location
            primary_needs = pre_parsed.get("primary_needs", [])
            barriers = pre_parsed.get("barriers", [])

            # Coordinates from pre_parsed
            coord_lat = pre_parsed.get("latitude")
            coord_lon = pre_parsed.get("longitude")
            coord_accuracy = pre_parsed.get("location_accuracy")
            coord_source = pre_parsed.get("location_source")
        else:
            # No pre-parsed data — use basic extraction from message text
            # (This is the fallback path when chatbot-service is unavailable)
            raw_location = explicit_location
            primary_needs = _extract_needs_from_text(message)
            barriers = _extract_barriers_from_text(message)

        # Top-level coordinates override if pre_parsed didn't have them
        if coord_lat is None and latitude is not None:
            coord_lat = latitude
            coord_lon = longitude

        # Resolve location against known graph nodes
        normalized_location: str | None = None
        if raw_location:
            normalized_location = (
                IntakeService._resolve_known_label(db, raw_location, ["Location"])
                or raw_location
            )

        # Resolve needs against known graph node labels
        resolved_primary: list[str] = []
        for need in primary_needs:
            resolved = IntakeService._resolve_known_label(
                db, need, ["NeedType", "NeedCategory"]
            )
            resolved_primary.append(resolved or need)

        # Derive support needs from barriers
        derived_support: list[str] = []
        for barrier in barriers:
            if "transport" in barrier.lower():
                derived_support.append("Transport")

        resolved_barriers: list[str] = []
        for barrier in barriers:
            resolved = IntakeService._resolve_known_label(db, barrier, ["Barrier"])
            resolved_barriers.append(resolved or barrier)

        return IntakeParseResult(
            message=message,
            normalized_location=normalized_location,
            primary_needs=sorted(set(resolved_primary)),
            derived_support_needs=sorted(
                set(n for n in derived_support if n not in resolved_primary)
            ),
            normalized_barriers=sorted(set(resolved_barriers)),
            latitude=coord_lat,
            longitude=coord_lon,
            location_accuracy=coord_accuracy,
            location_source=coord_source,
        )


# ---------------------------------------------------------------------------
# Basic text extraction fallbacks (no LLM needed)
# ---------------------------------------------------------------------------

_NEED_KEYWORDS: dict[str, str] = {
    "bleed": "Emergency Medical",
    "injur": "Emergency Medical",
    "hospital": "Emergency Medical",
    "ambulance": "Emergency Medical",
    "medic": "Emergency Medical",
    "medication": "Medication Access",
    "prescription": "Medication Access",
    "pills": "Medication Access",
    "counsel": "Mental Health Support",
    "trauma": "Mental Health Support",
    "anxiety": "Mental Health Support",
    "depress": "Mental Health Support",
    "mental": "Mental Health Support",
    "shelter": "Emergency Shelter",
    "homeless": "Emergency Shelter",
    "nowhere to stay": "Emergency Shelter",
    "safe place": "Emergency Shelter",
    "legal": "Protection Order Support",
    "protection order": "Protection Order Support",
    "restraining": "Protection Order Support",
    "court": "Protection Order Support",
    "transport": "Transport",
    "ride": "Transport",
    "stranded": "Transport",
}

_BARRIER_KEYWORDS: dict[str, str] = {
    "no transport": "No Transport",
    "can't travel": "No Transport",
    "no taxi": "No Transport",
    "no phone": "No Phone",
    "phone stolen": "No Phone",
    "no airtime": "No Phone",
    "unsafe to travel": "Unsafe To Travel",
    "afraid to go out": "Unsafe To Travel",
    "scared to leave": "Unsafe To Travel",
    "no id": "No ID Document",
    "no identity": "No ID Document",
}


def _extract_needs_from_text(message: str) -> list[str]:
    lower = message.lower()
    found: set[str] = set()
    for keyword, need in _NEED_KEYWORDS.items():
        if keyword in lower:
            found.add(need)
    return sorted(found)


def _extract_barriers_from_text(message: str) -> list[str]:
    lower = message.lower()
    found: set[str] = set()
    for keyword, barrier in _BARRIER_KEYWORDS.items():
        if keyword in lower:
            found.add(barrier)
    return sorted(found)
