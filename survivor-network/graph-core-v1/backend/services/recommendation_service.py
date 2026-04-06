from sqlalchemy.orm import Session

from models.graph import GraphNodeDB
from services.graph_service import GraphService
from services.intake_service import IntakeParseResult
from services.search_service import SearchService


class RecommendationService:
    @staticmethod
    def _dedupe_dict_nodes(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for item in items:
            node_id = item.get("id")
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            result.append(item)
        return result

    @staticmethod
    def _get_need_nodes(db: Session, need_labels: list[str]) -> list[GraphNodeDB]:
        if not need_labels:
            return []

        return (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label.in_(need_labels),
                GraphNodeDB.node_type.in_(["NeedType", "NeedCategory"]),
            )
            .all()
        )

    @staticmethod
    def _get_location_node(db: Session, location_label: str | None) -> GraphNodeDB | None:
        if not location_label:
            return None

        return (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label == location_label,
                GraphNodeDB.node_type == "Location",
            )
            .first()
        )

    @staticmethod
    def _build_summary(
        location: str | None,
        primary_needs: list[str],
        derived_support_needs: list[str],
        barriers: list[str],
        matched_resources: list[dict],
        matched_helpers: list[dict],
    ) -> str:
        parts: list[str] = []

        if primary_needs:
            parts.append(f"Primary needs identified: {', '.join(primary_needs)}")
        if location:
            parts.append(f"location: {location}")
        if matched_resources:
            parts.append(f"top resource match: {matched_resources[0]['label']}")
        if derived_support_needs:
            parts.append(f"support needs inferred from barriers: {', '.join(derived_support_needs)}")
        if matched_helpers:
            parts.append(f"top helper match: {matched_helpers[0]['label']}")
        if barriers:
            parts.append(f"barriers detected: {', '.join(barriers)}")

        if not parts:
            return "No strong structured matches were identified."

        return ". ".join(parts) + "."

    @staticmethod
    def assess_intake(
        db: Session,
        parsed: IntakeParseResult,
        top_k: int = 5,
    ) -> dict:
        primary_need_nodes = RecommendationService._get_need_nodes(db, parsed.primary_needs)
        derived_need_nodes = RecommendationService._get_need_nodes(db, parsed.derived_support_needs)
        all_need_nodes = primary_need_nodes + [n for n in derived_need_nodes if n.id not in {x.id for x in primary_need_nodes}]

        location_node = RecommendationService._get_location_node(db, parsed.normalized_location)

        primary_resources: list[dict] = []
        primary_helpers: list[dict] = []
        barrier_helpers: list[dict] = []

        # Resources: mainly for primary needs
        for need_node in primary_need_nodes:
            resources = GraphService._get_resources_for_need(db, need_node.id)
            helpers = GraphService._get_helpers_for_need(db, need_node.id)

            primary_resources.extend(GraphService._node_to_dict(r) for r in resources)
            primary_helpers.extend(GraphService._node_to_dict(h) for h in helpers)

        # Helpers: also for barrier-derived support needs
        for need_node in derived_need_nodes:
            helpers = GraphService._get_helpers_for_need(db, need_node.id)
            barrier_helpers.extend(GraphService._node_to_dict(h) for h in helpers)

        matched_resources = RecommendationService._dedupe_dict_nodes(primary_resources)
        primary_helpers = RecommendationService._dedupe_dict_nodes(primary_helpers)
        barrier_helpers = RecommendationService._dedupe_dict_nodes(barrier_helpers)

        matched_resources = [
            r for r in matched_resources
            if GraphService._is_node_available(db, r["id"])
        ]

        # Merge helper lists, keeping primary-need helpers first
        matched_helpers = RecommendationService._dedupe_dict_nodes(primary_helpers + barrier_helpers)

        # Prioritize same-location resources/helpers
        if location_node:
            location_payload = GraphService.get_support_options_for_location(db, location_node.id)
            local_resource_ids = {r["id"] for r in location_payload.get("resources", [])}
            local_helper_ids = {h["id"] for h in location_payload.get("helpers", [])}

            local_resources = [r for r in matched_resources if r["id"] in local_resource_ids]
            non_local_resources = [r for r in matched_resources if r["id"] not in local_resource_ids]
            matched_resources = local_resources + non_local_resources

            local_helpers = [h for h in matched_helpers if h["id"] in local_helper_ids]
            non_local_helpers = [h for h in matched_helpers if h["id"] not in local_helper_ids]
            matched_helpers = local_helpers + non_local_helpers

        semantic_payload = SearchService.semantic_search_documents(
            db=db,
            query=parsed.message,
            limit=top_k,
        )

        if isinstance(semantic_payload, dict):
            semantic_results = semantic_payload.get("results", [])
        else:
            semantic_results = semantic_payload

        recommended_actions: list[dict] = []

        for resource in matched_resources[:3]:
            recommended_actions.append(
                {
                    "kind": "resource",
                    "category": "primary_support",
                    "reason": "Resource matches a primary need and is prioritized by location",
                    "node": resource,
                }
            )

        for helper in primary_helpers[:2]:
            recommended_actions.append(
                {
                    "kind": "helper",
                    "category": "primary_support",
                    "reason": "Helper capability matches a primary need",
                    "node": helper,
                }
            )

        for helper in barrier_helpers[:2]:
            recommended_actions.append(
                {
                    "kind": "helper",
                    "category": "barrier_mitigation",
                    "reason": "Helper capability matches support needed to overcome a detected barrier",
                    "node": helper,
                }
            )

        for barrier in parsed.normalized_barriers:
            recommended_actions.append(
                {
                    "kind": "barrier",
                    "category": "barrier_detection",
                    "reason": f"Barrier detected: {barrier}",
                    "node": None,
                }
            )

        summary = RecommendationService._build_summary(
            location=parsed.normalized_location,
            primary_needs=parsed.primary_needs,
            derived_support_needs=parsed.derived_support_needs,
            barriers=parsed.normalized_barriers,
            matched_resources=matched_resources,
            matched_helpers=matched_helpers,
        )

        return {
            "message": parsed.message,
            "summary": summary,
            "normalized_location": parsed.normalized_location,
            "primary_needs": parsed.primary_needs,
            "derived_support_needs": parsed.derived_support_needs,
            "normalized_barriers": parsed.normalized_barriers,
            "matched_need_nodes": [GraphService._node_to_dict(n) for n in all_need_nodes],
            "matched_resources": matched_resources[:top_k],
            "matched_helpers": matched_helpers[:top_k],
            "semantic_results": semantic_results,
            "recommended_actions": recommended_actions[:top_k],
        }