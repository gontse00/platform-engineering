import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models.graph import GraphEdgeDB, GraphNodeDB
from services.escalation_resolver_service import EscalationResolverService
from services.escalation_service import EscalationService
from services.intake_service import IntakeService
from services.recommendation_service import RecommendationService
from services.triage_service import TriageService


class CaseOrchestrationService:
    @staticmethod
    def _json_safe(value):
        if isinstance(value, dict):
            return {k: CaseOrchestrationService._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [CaseOrchestrationService._json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [CaseOrchestrationService._json_safe(v) for v in value]
        if isinstance(value, UUID):
            return str(value)
        return value

    @staticmethod
    def _node_to_dict(node: GraphNodeDB | None) -> dict[str, Any] | None:
        if node is None:
            return None
        return {
            "id": str(node.id),
            "node_type": node.node_type,
            "label": node.label,
            "metadata": node.metadata_json,
            "created_at": node.created_at.isoformat() if node.created_at else None,
        }

    @staticmethod
    def _extract_survivor_label(message: str) -> str:
        cleaned = re.sub(r"\s+", " ", message.strip())
        short = cleaned[:50].strip()
        return f"Live Intake Survivor - {short}" if short else "Live Intake Survivor"

    @staticmethod
    def _get_node_by_label_and_type(
        db: Session,
        label: str,
        node_type: str,
    ) -> GraphNodeDB | None:
        return (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label == label,
                GraphNodeDB.node_type == node_type,
            )
            .first()
        )

    @staticmethod
    def _create_node(
        db: Session,
        node_type: str,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> GraphNodeDB:
        node = GraphNodeDB(
            node_type=node_type,
            label=label,
            metadata_json=CaseOrchestrationService._json_safe(metadata or {}),
        )
        db.add(node)
        db.flush()
        return node

    @staticmethod
    def _create_edge(
        db: Session,
        from_node_id: UUID,
        to_node_id: UUID,
        edge_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> GraphEdgeDB:
        edge = GraphEdgeDB(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            metadata_json=metadata or {},
        )
        db.add(edge)
        db.flush()
        return edge

    @staticmethod
    def _persist_case_graph(
        db: Session,
        message: str,
        intake: dict[str, Any],
        triage: dict[str, Any],
        escalation: dict[str, Any],
        create_referrals: bool,
    ) -> dict[str, Any]:
        survivor = CaseOrchestrationService._create_node(
            db=db,
            node_type="Survivor",
            label=CaseOrchestrationService._extract_survivor_label(message),
            metadata={
                "source": "live_intake",
                "message": message,
            },
        )

        case_node = CaseOrchestrationService._create_node(
            db=db,
            node_type="Case",
            label=f"Live Case - {survivor.id}",
            metadata={
                "source": "live_intake",
                "status": "open",
                "normalized_location": intake.get("normalized_location"),
                "urgency": triage.get("urgency"),
                "safety_risk": triage.get("safety_risk"),
                "queue": escalation.get("queue"),
            },
        )

        assessment_node = CaseOrchestrationService._create_node(
            db=db,
            node_type="Assessment",
            label=f"Assessment - {case_node.id}",
            metadata={
                "source": "live_intake",
                "message": message,
                "primary_needs": intake.get("primary_needs", []),
                "derived_support_needs": intake.get("derived_support_needs", []),
                "normalized_barriers": intake.get("normalized_barriers", []),
                "incident_types": triage.get("incident_types", []),
                "urgency": triage.get("urgency"),
                "safety_risk": triage.get("safety_risk"),
                "requires_human_review": triage.get("requires_human_review"),
                "escalation_recommended": triage.get("escalation_recommended"),
                "escalation_target": triage.get("escalation_target"),
                "queue": escalation.get("queue"),
            },
        )

        CaseOrchestrationService._create_edge(
            db, survivor.id, case_node.id, "INVOLVED_IN"
        )
        CaseOrchestrationService._create_edge(
            db, case_node.id, assessment_node.id, "ASSESSED_AS"
        )

        location_label = intake.get("normalized_location")
        if location_label:
            location_node = CaseOrchestrationService._get_node_by_label_and_type(
                db, location_label, "Location"
            )
            if location_node:
                CaseOrchestrationService._create_edge(
                    db, survivor.id, location_node.id, "LOCATED_IN"
                )
                CaseOrchestrationService._create_edge(
                    db, case_node.id, location_node.id, "LOCATED_IN"
                )

        for need_label in intake.get("primary_needs", []):
            need_node = (
                db.query(GraphNodeDB)
                .filter(GraphNodeDB.label == need_label)
                .filter(GraphNodeDB.node_type.in_(["NeedType", "NeedCategory"]))
                .first()
            )
            if need_node:
                CaseOrchestrationService._create_edge(
                    db, survivor.id, need_node.id, "HAS_NEED"
                )

        for barrier_label in intake.get("normalized_barriers", []):
            barrier_node = CaseOrchestrationService._get_node_by_label_and_type(
                db, barrier_label, "Barrier"
            )
            if barrier_node:
                CaseOrchestrationService._create_edge(
                    db, survivor.id, barrier_node.id, "BLOCKED_BY"
                )

        for incident_label in triage.get("incident_types", []):
            incident_type_node = CaseOrchestrationService._get_node_by_label_and_type(
                db, incident_label, "IncidentType"
            )
            if incident_type_node:
                incident_instance = CaseOrchestrationService._create_node(
                    db=db,
                    node_type="Incident",
                    label=f"{incident_label} - {case_node.id}",
                    metadata={"source": "live_intake"},
                )
                CaseOrchestrationService._create_edge(
                    db, case_node.id, incident_instance.id, "TRIGGERED_BY"
                )
                CaseOrchestrationService._create_edge(
                    db, incident_instance.id, incident_type_node.id, "INSTANCE_OF"
                )

        referrals: list[GraphNodeDB] = []
        if create_referrals:
            referral_targets = []
            referral_targets.extend(intake.get("matched_resources", [])[:2])
            referral_targets.extend(intake.get("matched_helpers", [])[:2])

            seen_ids: set[str] = set()
            for target in referral_targets:
                target_id = target.get("id")
                if not target_id or target_id in seen_ids:
                    continue
                seen_ids.add(target_id)

                referral = CaseOrchestrationService._create_node(
                    db=db,
                    node_type="Referral",
                    label=f"Referral - {target.get('label', 'Unknown')}",
                    metadata={
                        "source": "live_intake",
                        "target_id": str(target_id),
                        "target_label": target.get("label"),
                        "target_type": target.get("node_type"),
                        "queue": escalation.get("queue"),
                    },
                )
                referrals.append(referral)

                CaseOrchestrationService._create_edge(
                    db, referral.id, case_node.id, "FOR_CASE"
                )

                try:
                    target_uuid = UUID(target_id)
                    CaseOrchestrationService._create_edge(
                        db, referral.id, target_uuid, "TO_RESOURCE"
                    )
                except Exception:
                    pass

        db.commit()
        db.refresh(survivor)
        db.refresh(case_node)
        db.refresh(assessment_node)
        for referral in referrals:
            db.refresh(referral)

        return {
            "survivor": CaseOrchestrationService._node_to_dict(survivor),
            "case": CaseOrchestrationService._node_to_dict(case_node),
            "assessment": CaseOrchestrationService._node_to_dict(assessment_node),
            "referrals": [
                CaseOrchestrationService._node_to_dict(referral) for referral in referrals
            ],
        }

    @staticmethod
    def intake_case(
        db: Session,
        message: str,
        location: str | None = None,
        top_k: int = 5,
        create_referrals: bool = True,
    ) -> dict[str, Any]:
        parsed = IntakeService.parse_message(
            db=db,
            message=message,
            explicit_location=location,
        )

        triage = TriageService.assess_triage(
            message=message,
            parsed=parsed,
        )

        escalation = EscalationService.assess_escalation(
            triage=triage,
            parsed=parsed,
        )

        escalation_destinations = EscalationResolverService.resolve_destinations(
            db=db,
            triage=triage,
            escalation=escalation,
            parsed=parsed,
        )

        intake = RecommendationService.assess_intake(
            db=db,
            parsed=parsed,
            top_k=top_k,
        )

        persisted = CaseOrchestrationService._persist_case_graph(
            db=db,
            message=message,
            intake=intake,
            triage=triage,
            escalation=escalation,
            create_referrals=create_referrals,
        )

        summary = (
            f"Case created with urgency '{triage['urgency']}'"
            f" and queue '{escalation.get('queue') or 'none'}'."
        )

        return {
            "message": message,
            "summary": summary,
            "intake": intake,
            "triage": triage,
            "escalation": escalation,
            "escalation_destinations": escalation_destinations,
            "persisted": persisted,
        }