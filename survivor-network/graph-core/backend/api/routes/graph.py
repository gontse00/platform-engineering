from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from models.schemas import (
    CaseGraphResponse,
    CaseSupportOptionsResponse,
    EdgeCreate,
    EdgeResponse,
    EdgeUpdate,
    LocationSupportOptionsResponse,
    MatchmakingResult,
    NeighborResponse,
    NodeCreate,
    NodeResponse,
    NodeUpdate,
    SupportOptionsResponse,
)
from services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/health")
def graph_health():
    return {"status": "ok"}


@router.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("select 1")).scalar()
        return {"status": "ok", "db": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database check failed: {str(exc)}")


@router.post("/nodes", response_model=NodeResponse, status_code=201)
def create_node(payload: NodeCreate, db: Session = Depends(get_db)):
    node = GraphService.create_node(db, payload)
    return {
        "id": node.id,
        "node_type": node.node_type,
        "label": node.label,
        "metadata": node.metadata_json,
        "created_at": node.created_at,
    }


@router.post("/edges", response_model=EdgeResponse, status_code=201)
def create_edge(payload: EdgeCreate, db: Session = Depends(get_db)):
    edge = GraphService.create_edge(db, payload)
    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "edge_type": edge.edge_type,
        "metadata": edge.metadata_json,
        "created_at": edge.created_at,
    }


@router.get("/nodes/{node_id}", response_model=NodeResponse)
def get_node(node_id: UUID, db: Session = Depends(get_db)):
    node = GraphService.get_node(db, node_id)
    return {
        "id": node.id,
        "node_type": node.node_type,
        "label": node.label,
        "metadata": node.metadata_json,
        "created_at": node.created_at,
    }


@router.get("/nodes/{node_id}/neighbors", response_model=list[NeighborResponse])
def get_neighbors(node_id: UUID, db: Session = Depends(get_db)):
    return GraphService.get_neighbors(db, node_id)


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(
    node_type: str | None = Query(default=None),
    label: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    nodes = GraphService.list_nodes(db, node_type=node_type, label=label)
    return [
        {
            "id": node.id,
            "node_type": node.node_type,
            "label": node.label,
            "metadata": node.metadata_json,
            "created_at": node.created_at,
        }
        for node in nodes
    ]


@router.delete("/nodes/{node_id}")
def delete_node(node_id: UUID, db: Session = Depends(get_db)):
    return GraphService.delete_node(db, node_id)


@router.delete("/edges/{edge_id}")
def delete_edge(edge_id: UUID, db: Session = Depends(get_db)):
    return GraphService.delete_edge(db, edge_id)


@router.get("/cases/{case_id}/graph", response_model=CaseGraphResponse)
def get_case_graph(case_id: UUID, db: Session = Depends(get_db)):
    return GraphService.get_case_graph(db, case_id)


@router.get("/matchmaking", response_model=MatchmakingResult)
def get_matchmaking(
    need: str,
    location: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return GraphService.get_matches_for_need(
        db,
        need,
        location=location,
        priority=priority,
    )


@router.get("/survivors/{survivor_id}/support-options", response_model=SupportOptionsResponse)
def get_support_options_for_survivor(
    survivor_id: UUID,
    location: str | None = Query(default=None),
    need_priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return GraphService.get_support_options_for_survivor(
        db,
        survivor_id,
        location=location,
        need_priority=need_priority,
    )


@router.get("/cases/{case_id}/support-options", response_model=CaseSupportOptionsResponse)
def get_support_options_for_case(
    case_id: UUID,
    location: str | None = Query(default=None),
    case_status: str | None = Query(default=None),
    need_priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return GraphService.get_support_options_for_case(
        db,
        case_id,
        location=location,
        case_status=case_status,
        need_priority=need_priority,
    )


@router.get("/locations/{location_id}/support-options", response_model=LocationSupportOptionsResponse)
def get_support_options_for_location(
    location_id: UUID,
    case_status: str | None = Query(default=None),
    need_priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return GraphService.get_support_options_for_location(
        db,
        location_id,
        case_status=case_status,
        need_priority=need_priority,
    )


@router.patch("/nodes/{node_id}", response_model=NodeResponse)
def update_node(node_id: UUID, payload: NodeUpdate, db: Session = Depends(get_db)):
    node = GraphService.update_node(db, node_id, payload)
    return {
        "id": node.id,
        "node_type": node.node_type,
        "label": node.label,
        "metadata": node.metadata_json,
        "created_at": node.created_at,
    }


@router.patch("/edges/{edge_id}", response_model=EdgeResponse)
def update_edge(edge_id: UUID, payload: EdgeUpdate, db: Session = Depends(get_db)):
    edge = GraphService.update_edge(db, edge_id, payload)
    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "edge_type": edge.edge_type,
        "metadata": edge.metadata_json,
        "created_at": edge.created_at,
    }
