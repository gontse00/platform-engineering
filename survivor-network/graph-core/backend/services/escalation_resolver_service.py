from sqlalchemy.orm import Session

from models.graph import GraphNodeDB
from services.graph_service import GraphService
from services.intake_service import IntakeParseResult


class EscalationResolverService:
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
    def _get_need_nodes_for_escalation(db: Session, parsed: IntakeParseResult) -> list[GraphNodeDB]:
        labels = sorted(set(parsed.primary_needs + parsed.derived_support_needs))
        if not labels:
            return []

        return (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label.in_(labels),
                GraphNodeDB.node_type.in_(["NeedType", "NeedCategory"]),
            )
            .all()
        )

    @staticmethod
    def resolve_destinations(db: Session, triage: dict, escalation: dict, parsed: IntakeParseResult) -> list[dict]:
        results: list[dict] = []

        location_node = EscalationResolverService._get_location_node(db, parsed.normalized_location)
        need_nodes = EscalationResolverService._get_need_nodes_for_escalation(db, parsed)

        matched_resources: list[dict] = []
        matched_helpers: list[dict] = []

        for need_node in need_nodes:
            resources = GraphService._get_resources_for_need(db, need_node.id)
            helpers = GraphService._get_helpers_for_need(db, need_node.id)

            matched_resources.extend(GraphService._node_to_dict(r) for r in resources)
            matched_helpers.extend(GraphService._node_to_dict(h) for h in helpers)

        matched_resources = EscalationResolverService._dedupe_dict_nodes(matched_resources)
        matched_helpers = EscalationResolverService._dedupe_dict_nodes(matched_helpers)

        # filter available resources
        matched_resources = [
            r for r in matched_resources
            if GraphService._is_node_available(db, r["id"])
        ]

        # prioritize same-location resources/helpers if a location exists
        if location_node:
            location_payload = GraphService.get_support_options_for_location(db, location_node.id)

            local_resource_ids = {r["id"] for r in location_payload.get("resources", [])}
            local_helper_ids = {h["id"] for h in location_payload.get("helpers", [])}

            local_resources = [r for r in matched_resources if r["id"] in local_resource_ids]
            other_resources = [r for r in matched_resources if r["id"] not in local_resource_ids]
            matched_resources = local_resources + other_resources

            local_helpers = [h for h in matched_helpers if h["id"] in local_helper_ids]
            other_helpers = [h for h in matched_helpers if h["id"] not in local_helper_ids]
            matched_helpers = local_helpers + other_helpers

        queue = escalation.get("queue")
        urgency = triage.get("urgency")
        safety_risk = triage.get("safety_risk")

        if queue == "emergency_response":
            if matched_resources:
                results.append(
                    {
                        "kind": "resource",
                        "reason": "Nearest matching emergency-capable resource resolved from graph",
                        "node": matched_resources[0],
                    }
                )
            results.append(
                {
                    "kind": "queue",
                    "reason": "Critical escalation requires immediate emergency response handling",
                    "node": None,
                }
            )

        elif queue == "human_case_worker":
            if matched_helpers:
                results.append(
                    {
                        "kind": "helper",
                        "reason": "Human-support capable helper resolved for high-risk case",
                        "node": matched_helpers[0],
                    }
                )
            if matched_resources:
                results.append(
                    {
                        "kind": "resource",
                        "reason": "Supporting service resolved for high-risk case",
                        "node": matched_resources[0],
                    }
                )
            results.append(
                {
                    "kind": "queue",
                    "reason": "Case should be handed to a human case worker",
                    "node": None,
                }
            )

        elif queue == "priority_support_queue":
            for resource in matched_resources[:2]:
                results.append(
                    {
                        "kind": "resource",
                        "reason": "Priority support destination resolved from graph",
                        "node": resource,
                    }
                )
            for helper in matched_helpers[:1]:
                results.append(
                    {
                        "kind": "helper",
                        "reason": "Support helper resolved from graph",
                        "node": helper,
                    }
                )

        # extra domain-specific escalation destinations
        if "Protection Order Support" in parsed.primary_needs:
            legal_resources = []
            for resource in matched_resources:
                label = resource.get("label", "").lower()
                if "legal" in label or "saps" in label or "victim" in label:
                    legal_resources.append(resource)

            for resource in legal_resources[:2]:
                results.append(
                    {
                        "kind": "resource",
                        "reason": "Legal protection support destination resolved",
                        "node": resource,
                    }
                )

        if "No Transport" in parsed.normalized_barriers:
            for helper in matched_helpers[:1]:
                results.append(
                    {
                        "kind": "helper",
                        "reason": "Transport barrier mitigation support resolved",
                        "node": helper,
                    }
                )

        # final dedupe on node id + kind
        deduped: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for item in results:
            node = item.get("node")
            node_id = node.get("id") if node else "none"
            key = (item["kind"], node_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped