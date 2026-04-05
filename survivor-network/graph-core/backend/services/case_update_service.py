from sqlalchemy.orm import Session

from models.graph import GraphNodeDB


class CaseUpdateService:
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

        case_node.metadata_json = metadata
        db.add(case_node)
        db.commit()
        db.refresh(case_node)

        return {
            "case_id": str(case_node.id),
            "updated": True,
            "message": "Case context updated",
        }