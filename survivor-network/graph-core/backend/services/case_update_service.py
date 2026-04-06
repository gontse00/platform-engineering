from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.graph import GraphEdgeDB, GraphNodeDB


class CaseUpdateService:
    @staticmethod
    def _node_to_timeline_event(edge: GraphEdgeDB, node: GraphNodeDB) -> dict:
        return {
            "node_id": str(node.id),
            "node_type": node.node_type,
            "label": node.label,
            "edge_type": edge.edge_type,
            "metadata": node.metadata_json or {},
            "created_at": node.created_at,
        }

    @staticmethod
    def update_case_context(
        db: Session,
        case_id: str,
        payload: dict,
    ) -> dict:
        case_node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.id == case_id,
                GraphNodeDB.node_type == "Case",
            )
            .first()
        )

        if not case_node:
            return {
                "case_id": case_id,
                "updated": False,
                "message": "Case not found",
            }

        metadata = dict(case_node.metadata_json or {})
        metadata["session_id"] = payload.get("session_id", metadata.get("session_id"))
        metadata["immediate_danger"] = payload.get("immediate_danger", metadata.get("immediate_danger"))
        metadata["injury_status"] = payload.get("injury_status", metadata.get("injury_status"))
        metadata["safe_contact_method"] = payload.get("safe_contact_method", metadata.get("safe_contact_method"))
        metadata["location"] = payload.get("location", metadata.get("location"))
        metadata["primary_need"] = payload.get("primary_need", metadata.get("primary_need"))
        metadata["conversation_summary"] = payload.get("conversation_summary", metadata.get("conversation_summary"))
        metadata["submission_mode"] = payload.get("submission_mode", metadata.get("submission_mode"))
        metadata["last_context_update_at"] = datetime.now(timezone.utc).isoformat()

        history = list(metadata.get("history", []))
        history.append(
            {
                "event_type": "context_update",
                "at": metadata["last_context_update_at"],
                "patch": {k: v for k, v in payload.items() if v is not None},
            }
        )
        metadata["history"] = history[-25:]

        case_node.metadata_json = metadata
        db.add(case_node)

        update_node = GraphNodeDB(
            node_type="Assessment",
            label=f"Context Update - {case_node.id}",
            metadata_json={
                "source": "case_context_update",
                "updated_at": metadata["last_context_update_at"],
                "patch": {k: v for k, v in payload.items() if v is not None},
            },
        )
        db.add(update_node)
        db.flush()

        update_edge = GraphEdgeDB(
            from_node_id=case_node.id,
            to_node_id=update_node.id,
            edge_type="UPDATED_TO",
            metadata_json={"source": "case_context_update"},
        )
        db.add(update_edge)
        db.commit()
        db.refresh(case_node)

        return {
            "case_id": str(case_node.id),
            "updated": True,
            "message": "Case context updated",
        }

    @staticmethod
    def get_case_timeline(db: Session, case_id: str) -> dict:
        case_node = (
            db.query(GraphNodeDB)
            .filter(GraphNodeDB.id == case_id, GraphNodeDB.node_type == "Case")
            .first()
        )
        if not case_node:
            return {"case_id": case_id, "events": []}

        edges = (
            db.query(GraphEdgeDB)
            .filter(GraphEdgeDB.from_node_id == case_node.id)
            .filter(GraphEdgeDB.edge_type.in_(["ASSESSED_AS", "UPDATED_TO", "TRIGGERED_BY"]))
            .all()
        )

        events = []
        for edge in edges:
            node = db.get(GraphNodeDB, edge.to_node_id)
            if node is None:
                continue
            events.append(CaseUpdateService._node_to_timeline_event(edge, node))

        events.sort(key=lambda item: item.get("created_at") or datetime.min, reverse=True)
        return {
            "case_id": str(case_node.id),
            "events": events,
        }
