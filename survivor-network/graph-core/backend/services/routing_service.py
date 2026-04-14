"""Routing / ranking service.

Scores candidate resources and helpers by need match, location proximity,
urgency fit, barrier support, and availability.

When user coordinates are available, a haversine-based proximity bonus
replaces the text-only location match — nearby resources score higher.
Falls back to text-based covered_locations matching when no coordinates
are available.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from models.schemas import RankedDestination, RouteScoreBreakdown, RoutingSummary
from services.distance_util import distance_score, extract_coords, haversine_km


class RoutingService:
    def __init__(self) -> None:
        pass

    def rank_destinations(
        self,
        *,
        resources: List[dict],
        helpers: List[dict],
        primary_needs: List[str],
        derived_support_needs: List[str],
        normalized_barriers: List[str],
        normalized_location: Optional[str],
        urgency: str,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
    ) -> Tuple[List[RankedDestination], RoutingSummary]:
        ranked: List[RankedDestination] = []

        for node in resources:
            ranked.append(
                self._score_node(
                    node=node,
                    node_kind="Resource",
                    primary_needs=primary_needs,
                    support_needs=derived_support_needs,
                    normalized_barriers=normalized_barriers,
                    normalized_location=normalized_location,
                    urgency=urgency,
                    user_latitude=user_latitude,
                    user_longitude=user_longitude,
                )
            )

        for node in helpers:
            ranked.append(
                self._score_node(
                    node=node,
                    node_kind="Helper",
                    primary_needs=primary_needs,
                    support_needs=derived_support_needs,
                    normalized_barriers=normalized_barriers,
                    normalized_location=normalized_location,
                    urgency=urgency,
                    user_latitude=user_latitude,
                    user_longitude=user_longitude,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)

        summary = RoutingSummary(
            top_destination_label=ranked[0].label if ranked else None,
            top_destination_type=ranked[0].node_type if ranked else None,
            total_ranked=len(ranked),
            notes=self._build_summary_notes(
                ranked=ranked,
                normalized_barriers=normalized_barriers,
                urgency=urgency,
                normalized_location=normalized_location,
                user_latitude=user_latitude,
                user_longitude=user_longitude,
            ),
        )

        return ranked, summary

    def _score_node(
        self,
        *,
        node: dict,
        node_kind: str,
        primary_needs: List[str],
        support_needs: List[str],
        normalized_barriers: List[str],
        normalized_location: Optional[str],
        urgency: str,
        user_latitude: float | None = None,
        user_longitude: float | None = None,
    ) -> RankedDestination:
        metadata = node.get("metadata", {}) or {}
        label = node.get("label", "Unknown")
        node_id = str(node.get("id", ""))
        node_type = node.get("node_type", node_kind)

        breakdown = RouteScoreBreakdown()
        reasons: List[str] = []

        provides = self._normalize_list(metadata.get("provides"))
        support_tags = self._normalize_list(metadata.get("support_tags"))
        accepted_urgencies = self._normalize_list(metadata.get("accepted_urgencies"))
        barrier_support = self._normalize_list(metadata.get("barrier_support"))
        covered_locations = self._normalize_list(metadata.get("covered_locations"))
        availability_status = str(metadata.get("availability_status", "unknown")).lower()

        primary_need_l = self._lower(primary_needs)
        all_support_l = self._lower(primary_needs + support_needs)

        # --- Need match ---
        if any(need in provides for need in primary_need_l):
            breakdown.need_match = 0.40
            reasons.append("Matches a primary need")
        elif any(need in support_tags for need in all_support_l):
            breakdown.need_match = 0.25
            reasons.append("Matches a related support need")

        # --- Location match ---
        # Prefer coordinate-based proximity when both user and resource have coords
        used_coordinates = False
        if user_latitude is not None and user_longitude is not None:
            resource_coords = extract_coords(node)
            if resource_coords:
                dist_km = haversine_km(
                    user_latitude, user_longitude,
                    resource_coords[0], resource_coords[1],
                )
                prox_score = distance_score(dist_km)
                if prox_score > 0:
                    breakdown.location_match = prox_score
                    reasons.append(f"{dist_km:.1f} km away (coordinate match)")
                    used_coordinates = True
                else:
                    reasons.append(f"{dist_km:.0f} km away (too far for proximity bonus)")

        # Fall back to text-based location matching
        if not used_coordinates and normalized_location:
            location_l = normalized_location.lower()
            if location_l in covered_locations:
                breakdown.location_match = 0.25
                reasons.append(f"Supports location: {normalized_location}")
            elif not covered_locations:
                breakdown.location_match = 0.10
                reasons.append("No explicit coverage data; treated as generic location match")

        # --- Urgency fit ---
        if urgency:
            urgency_l = urgency.lower()
            if urgency_l in accepted_urgencies:
                breakdown.urgency_fit = 0.15
                reasons.append(f"Accepts urgency level: {urgency}")
            elif not accepted_urgencies:
                breakdown.urgency_fit = 0.05
                reasons.append("No urgency restrictions recorded")

        # --- Barrier support ---
        if normalized_barriers:
            barrier_hits = [
                barrier for barrier in normalized_barriers
                if barrier.lower() in barrier_support
            ]
            if barrier_hits:
                breakdown.barrier_support = 0.10
                reasons.append(f"Can mitigate barriers: {', '.join(barrier_hits)}")

        # --- Availability ---
        if availability_status == "available":
            breakdown.availability = 0.10
            reasons.append("Currently marked available")
        elif availability_status == "limited":
            breakdown.availability = 0.05
            reasons.append("Availability is limited")
        elif availability_status == "unavailable":
            breakdown.availability = -0.20
            reasons.append("Currently marked unavailable")

        score = round(
            breakdown.need_match
            + breakdown.location_match
            + breakdown.urgency_fit
            + breakdown.barrier_support
            + breakdown.availability,
            4,
        )

        return RankedDestination(
            node_id=node_id,
            node_type=node_type,
            label=label,
            score=score,
            score_breakdown=breakdown,
            why_selected=reasons,
            metadata=metadata,
        )

    def _build_summary_notes(
        self,
        *,
        ranked: List[RankedDestination],
        normalized_barriers: List[str],
        urgency: str,
        normalized_location: Optional[str],
        user_latitude: float | None = None,
        user_longitude: float | None = None,
    ) -> List[str]:
        notes: List[str] = []

        if ranked:
            notes.append(f"Top ranked destination: {ranked[0].label}")
        if user_latitude is not None:
            notes.append(f"Routing used GPS coordinates ({user_latitude:.4f}, {user_longitude:.4f})")
        elif normalized_location:
            notes.append(f"Routing considered location: {normalized_location}")
        if urgency:
            notes.append(f"Routing considered urgency: {urgency}")
        if normalized_barriers:
            notes.append(f"Routing considered barriers: {', '.join(normalized_barriers)}")

        return notes

    def _normalize_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip().lower() for v in value if str(v).strip()]
        value_str = str(value).strip().lower()
        return [value_str] if value_str else []

    def _lower(self, values: List[str]) -> List[str]:
        return [str(v).lower() for v in values]
