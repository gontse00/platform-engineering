import logging

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.graph import GraphEdgeDB, GraphNodeDB
from models.schemas import EdgeCreate, NodeCreate

logger = logging.getLogger(__name__)


class GraphService:
    @staticmethod
    def _node_to_dict(node: GraphNodeDB):
        return {
            "id": node.id,
            "node_type": node.node_type,
            "label": node.label,
            "metadata": node.metadata_json,
            "created_at": node.created_at,
        }

    @staticmethod
    def _dedupe_nodes(nodes: list[GraphNodeDB]):
        return list({str(node.id): node for node in nodes}.values())

    @staticmethod
    def _get_needs_for_survivor(db: Session, survivor_id):
        need_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.from_node_id == survivor_id,
                GraphEdgeDB.edge_type == "HAS_NEED",
            )
            .all()
        )

        needs = []
        for edge in need_edges:
            need_node = db.get(GraphNodeDB, edge.to_node_id)
            if need_node:
                needs.append(need_node)

        return GraphService._dedupe_nodes(needs)

    @staticmethod
    def _get_resources_for_need(db: Session, need_id):
        resource_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == need_id,
                GraphEdgeDB.edge_type == "PROVIDES",
            )
            .all()
        )

        resources = []
        for edge in resource_edges:
            resource_node = db.get(GraphNodeDB, edge.from_node_id)
            if resource_node:
                resources.append(resource_node)

        return GraphService._dedupe_nodes(resources)

    @staticmethod
    def _get_helpers_for_need(db: Session, need_id, exclude_helper_id=None):
        helper_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == need_id,
                GraphEdgeDB.edge_type == "CAN_SUPPORT",
            )
            .all()
        )

        helpers = []
        for edge in helper_edges:
            helper_node = db.get(GraphNodeDB, edge.from_node_id)
            if helper_node and helper_node.id != exclude_helper_id:
                helpers.append(helper_node)

        return GraphService._dedupe_nodes(helpers)

    @staticmethod
    def _build_support_options_for_survivor(
        db: Session,
        survivor: GraphNodeDB,
        location: str | None = None,
        need_priority: str | None = None,
    ):
        needs = GraphService._get_needs_for_survivor(db, survivor.id)
        needs = GraphService._filter_nodes_by_metadata(needs, "priority", need_priority)

        all_resources = []
        all_helpers = []

        for need_node in needs:
            all_resources.extend(GraphService._get_resources_for_need(db, need_node.id))
            all_helpers.extend(
                GraphService._get_helpers_for_need(
                    db,
                    need_node.id,
                    exclude_helper_id=survivor.id,
                )
            )   
        resources = GraphService._dedupe_nodes(all_resources)
        helpers = GraphService._dedupe_nodes(all_helpers)

        if location:
            resources = GraphService._filter_nodes_by_location(db, resources, location)
            helpers = GraphService._filter_nodes_by_location(db, helpers, location)

        return {
            "survivor": GraphService._node_to_dict(survivor),
            "needs": [GraphService._node_to_dict(node) for node in needs],
            "resources": [GraphService._node_to_dict(node) for node in resources],
            "helpers": [GraphService._node_to_dict(node) for node in helpers],
        }

    @staticmethod
    def create_node(db: Session, payload: NodeCreate) -> GraphNodeDB:
        try:
            logger.info(
                "Creating node",
                extra={"node_type": payload.node_type, "label": payload.label},
            )
            node = GraphNodeDB(
                node_type=payload.node_type,
                label=payload.label,
                metadata_json=payload.metadata,
            )
            db.add(node)
            db.commit()
            db.refresh(node)
            logger.info("Node created", extra={"node_id": str(node.id)})
            return node
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to create node")
            raise HTTPException(status_code=500, detail="Failed to create node")

    @staticmethod
    def create_edge(db: Session, payload: EdgeCreate) -> GraphEdgeDB:
        try:
            logger.info(
                "Creating edge",
                extra={
                    "from_node_id": str(payload.from_node_id),
                    "to_node_id": str(payload.to_node_id),
                    "edge_type": payload.edge_type,
                },
            )

            if payload.from_node_id == payload.to_node_id:
                raise HTTPException(status_code=400, detail="Self-loop edges are not allowed")

            from_node = db.get(GraphNodeDB, payload.from_node_id)
            to_node = db.get(GraphNodeDB, payload.to_node_id)

            if not from_node or not to_node:
                logger.warning("Edge creation failed: one or both nodes missing")
                raise HTTPException(status_code=404, detail="One or both nodes do not exist")

            edge = GraphEdgeDB(
                from_node_id=payload.from_node_id,
                to_node_id=payload.to_node_id,
                edge_type=payload.edge_type,
                metadata_json=payload.metadata,
            )
            db.add(edge)
            db.commit()
            db.refresh(edge)
            logger.info("Edge created", extra={"edge_id": str(edge.id)})
            return edge

        except HTTPException:
            raise
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to create edge")
            raise HTTPException(status_code=500, detail="Failed to create edge")

    @staticmethod
    def get_node(db: Session, node_id):
        node = db.get(GraphNodeDB, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return node

    @staticmethod
    def get_neighbors(db: Session, node_id):
        node = db.get(GraphNodeDB, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        edges = (
            db.query(GraphEdgeDB)
            .filter(or_(GraphEdgeDB.from_node_id == node_id, GraphEdgeDB.to_node_id == node_id))
            .all()
        )

        results = []
        for edge in edges:
            if edge.from_node_id == node_id:
                neighbor = db.get(GraphNodeDB, edge.to_node_id)
                direction = "outgoing"
            else:
                neighbor = db.get(GraphNodeDB, edge.from_node_id)
                direction = "incoming"

            results.append(
                {
                    "edge_id": edge.id,
                    "edge_type": edge.edge_type,
                    "direction": direction,
                    "node": GraphService._node_to_dict(neighbor),
                    "metadata": edge.metadata_json,
                }
            )

        return results

    @staticmethod
    def list_nodes(db: Session, node_type: str | None = None, label: str | None = None):
        query = db.query(GraphNodeDB)

        if node_type:
            query = query.filter(GraphNodeDB.node_type == node_type)

        if label:
            query = query.filter(GraphNodeDB.label.ilike(f"%{label}%"))

        return query.order_by(GraphNodeDB.created_at.desc()).all()

    @staticmethod
    def delete_node(db: Session, node_id):
        node = db.get(GraphNodeDB, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        try:
            db.delete(node)
            db.commit()
            logger.info("Node deleted", extra={"node_id": str(node_id)})
            return {"status": "deleted", "node_id": str(node_id)}
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to delete node")
            raise HTTPException(status_code=500, detail="Failed to delete node")

    @staticmethod
    def delete_edge(db: Session, edge_id):
        edge = db.get(GraphEdgeDB, edge_id)
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")

        try:
            db.delete(edge)
            db.commit()
            logger.info("Edge deleted", extra={"edge_id": str(edge_id)})
            return {"status": "deleted", "edge_id": str(edge_id)}
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to delete edge")
            raise HTTPException(status_code=500, detail="Failed to delete edge")

    @staticmethod
    def get_case_graph(db: Session, case_id):
        case_node = db.get(GraphNodeDB, case_id)

        if not case_node:
            raise HTTPException(status_code=404, detail="Case not found")

        if case_node.node_type != "Case":
            raise HTTPException(status_code=400, detail="Requested node is not a Case")

        edges = (
            db.query(GraphEdgeDB)
            .filter(or_(GraphEdgeDB.from_node_id == case_id, GraphEdgeDB.to_node_id == case_id))
            .all()
        )

        neighbors = []
        for edge in edges:
            if edge.from_node_id == case_id:
                neighbor = db.get(GraphNodeDB, edge.to_node_id)
                direction = "outgoing"
            else:
                neighbor = db.get(GraphNodeDB, edge.from_node_id)
                direction = "incoming"

            neighbors.append(
                {
                    "edge_id": edge.id,
                    "edge_type": edge.edge_type,
                    "direction": direction,
                    "node": GraphService._node_to_dict(neighbor),
                    "metadata": edge.metadata_json,
                }
            )

        return {
            "case": GraphService._node_to_dict(case_node),
            "neighbors": neighbors,
        }

    @staticmethod
    def get_matches_for_need(
        db: Session,
        need_label: str,
        location: str | None = None,
        priority: str | None = None,
    ):
        need_query = db.query(GraphNodeDB).filter(
            GraphNodeDB.node_type.in_(["NeedType", "NeedCategory"]),
            GraphNodeDB.label.ilike(f"%{need_label}%"),
        )

        need_nodes = need_query.all()

        if priority:
            need_nodes = [
                node
                for node in need_nodes
                if (node.metadata_json or {}).get("priority", "").lower() == priority.lower()
            ]

        if not need_nodes:
            raise HTTPException(status_code=404, detail="Need not found")

        # for now use the first matching need node
        need_node = need_nodes[0]

        incoming_need_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == need_node.id,
                GraphEdgeDB.edge_type == "HAS_NEED",
            )
            .all()
        )

        matches = []

        for edge in incoming_need_edges:
            source_node = db.get(GraphNodeDB, edge.from_node_id)
            if source_node:
                matches.append(source_node)

        matches.extend(GraphService._get_resources_for_need(db, need_node.id))
        matches.extend(GraphService._get_helpers_for_need(db, need_node.id))

        unique_matches = GraphService._dedupe_nodes(matches)

        if location:
            unique_matches = GraphService._filter_nodes_by_location(db, unique_matches, location)

        return {
            "need": GraphService._node_to_dict(need_node),
            "matches": [GraphService._node_to_dict(node) for node in unique_matches],
        }

    @staticmethod
    def get_support_options_for_survivor(
        db: Session,
        survivor_id,
        location: str | None = None,
        need_priority: str | None = None,
    ):
        survivor = db.get(GraphNodeDB, survivor_id)

        if not survivor:
            raise HTTPException(status_code=404, detail="Survivor not found")

        if survivor.node_type != "Survivor":
            raise HTTPException(status_code=400, detail="Requested node is not a Survivor")

        return GraphService._build_support_options_for_survivor(
            db,
            survivor,
            location=location,
            need_priority=need_priority,
        )

    
    @staticmethod
    def get_support_options_for_case(
        db: Session,
        case_id,
        location: str | None = None,
        case_status: str | None = None,
        need_priority: str | None = None,
    ):
        case_node = db.get(GraphNodeDB, case_id)

        if not case_node:
            raise HTTPException(status_code=404, detail="Case not found")

        if case_node.node_type != "Case":
            raise HTTPException(status_code=400, detail="Requested node is not a Case")

        if case_status and not GraphService._node_metadata_matches(case_node, "status", case_status):
            raise HTTPException(status_code=404, detail="Case not found for requested status")

        case_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == case_id,
                GraphEdgeDB.edge_type == "INVOLVED_IN",
            )
            .all()
        )

        survivor_views = []

        for edge in case_edges:
            survivor = db.get(GraphNodeDB, edge.from_node_id)
            if not survivor or survivor.node_type != "Survivor":
                continue

            survivor_views.append(
                GraphService._build_support_options_for_survivor(
                    db,
                    survivor,
                    location=location,
                    need_priority=need_priority,
                )
            )

        return {
            "case": GraphService._node_to_dict(case_node),
            "survivors": survivor_views,
        }
    
    @staticmethod
    def _filter_nodes_by_location(db: Session, nodes: list[GraphNodeDB], location: str | None):
        if not location:
            return nodes

        filtered = []
        for node in nodes:
            if GraphService._node_has_location(db, node, location):
                filtered.append(node)

        return filtered
    
    @staticmethod
    def _get_location_nodes_for_entity(db: Session, entity_id):
        location_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.from_node_id == entity_id,
                GraphEdgeDB.edge_type == "LOCATED_IN",
            )
            .all()
        )

        locations = []
        for edge in location_edges:
            location_node = db.get(GraphNodeDB, edge.to_node_id)
            if location_node and location_node.node_type == "Location":
                locations.append(location_node)

        return GraphService._dedupe_nodes(locations)

    @staticmethod
    def _node_has_location(db: Session, node: GraphNodeDB, location: str | None):
        if not location:
            return True

        location_nodes = GraphService._get_location_nodes_for_entity(db, node.id)

        for location_node in location_nodes:
            if location_node.label.lower() == location.lower():
                return True

        return False
    
    @staticmethod
    def _get_entities_for_location(db: Session, location_id, node_type: str | None = None):
        location_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == location_id,
                GraphEdgeDB.edge_type == "LOCATED_IN",
            )
            .all()
        )

        entities = []
        for edge in location_edges:
            entity = db.get(GraphNodeDB, edge.from_node_id)
            if not entity:
                continue

            if node_type and entity.node_type != node_type:
                continue

            entities.append(entity)

        return GraphService._dedupe_nodes(entities)
    
    @staticmethod
    def get_support_options_for_location(
        db: Session,
        location_id,
        case_status: str | None = None,
        need_priority: str | None = None,
    ):
        location_node = db.get(GraphNodeDB, location_id)

        if not location_node:
            raise HTTPException(status_code=404, detail="Location not found")

        if location_node.node_type != "Location":
            raise HTTPException(status_code=400, detail="Requested node is not a Location")

        survivors = GraphService._get_entities_for_location(db, location_id, node_type="Survivor")
        resources = GraphService._get_entities_for_location(db, location_id, node_type="Resource")
        helpers = GraphService._get_entities_for_location(db, location_id, node_type="Helper")

        all_needs = []
        all_cases = []

        for survivor in survivors:
            all_needs.extend(GraphService._get_needs_for_survivor(db, survivor.id))
            all_cases.extend(GraphService._get_cases_for_survivor(db, survivor.id))

        needs = GraphService._dedupe_nodes(all_needs)
        cases = GraphService._dedupe_nodes(all_cases)

        return {
            "location": GraphService._node_to_dict(location_node),
            "survivors": [GraphService._node_to_dict(node) for node in survivors],
            "cases": [GraphService._node_to_dict(node) for node in cases],
            "needs": [GraphService._node_to_dict(node) for node in needs],
            "resources": [GraphService._node_to_dict(node) for node in resources],
            "helpers": [GraphService._node_to_dict(node) for node in helpers],
        }
    
    
    @staticmethod
    def _get_cases_for_survivor(db: Session, survivor_id):
        case_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.from_node_id == survivor_id,
                GraphEdgeDB.edge_type == "INVOLVED_IN",
            )
            .all()
        )

        cases = []
        for edge in case_edges:
            case_node = db.get(GraphNodeDB, edge.to_node_id)
            if case_node and case_node.node_type == "Case":
                cases.append(case_node)

        return GraphService._dedupe_nodes(cases)
    
    @staticmethod
    def update_node(db: Session, node_id, payload):
        node = db.get(GraphNodeDB, node_id)

        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        try:
            if payload.label is not None:
                label = payload.label.strip()
                if not label:
                    raise HTTPException(status_code=400, detail="Label must not be blank")
                node.label = label

            if payload.metadata is not None:
                node.metadata_json = payload.metadata

            db.commit()
            db.refresh(node)

            logger.info("Node updated", extra={"node_id": str(node.id)})
            return node

        except HTTPException:
            raise
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to update node")
            raise HTTPException(status_code=500, detail="Failed to update node")
        
    @staticmethod
    def update_edge(db: Session, edge_id, payload):
        edge = db.get(GraphEdgeDB, edge_id)

        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")

        try:
            if payload.metadata is not None:
                edge.metadata_json = payload.metadata

            db.commit()
            db.refresh(edge)

            logger.info("Edge updated", extra={"edge_id": str(edge.id)})
            return edge

        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to update edge")
            raise HTTPException(status_code=500, detail="Failed to update edge")
        

    @staticmethod
    def _node_metadata_matches(node: GraphNodeDB, key: str, value: str | None):
        if not value:
            return True

        metadata_value = (node.metadata_json or {}).get(key)
        if metadata_value is None:
            return False

        return str(metadata_value).lower() == value.lower()

    @staticmethod
    def _filter_nodes_by_metadata(
        nodes: list[GraphNodeDB],
        key: str,
        value: str | None,
    ):
        if not value:
            return nodes

        return [
            node
            for node in nodes
            if GraphService._node_metadata_matches(node, key, value)
        ]
    
    @staticmethod
    def _get_status_labels_for_node(db: Session, node_id) -> list[str]:
        status_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.from_node_id == node_id,
                GraphEdgeDB.edge_type == "HAS_STATUS",
            )
            .all()
        )

        labels = []
        for edge in status_edges:
            status_node = db.get(GraphNodeDB, edge.to_node_id)
            if status_node and status_node.node_type == "Status":
                labels.append(status_node.label)

        return sorted(set(labels))
    
    @staticmethod
    def _is_node_available(db: Session, node_id) -> bool:
        statuses = GraphService._get_status_labels_for_node(db, node_id)
        if not statuses:
            return True
        return "Available" in statuses and "Unavailable" not in statuses