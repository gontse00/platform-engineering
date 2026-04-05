from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from services.search_service import SearchService
from models.schemas import SearchResultsResponse, SemanticSearchResultsResponse
router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResultsResponse)
def search(
    q: str = Query(..., min_length=1),
    doc_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    province: str | None = Query(default=None),
    node_type: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    payload = SearchService.search_documents(
        db=db,
        query=q,
        doc_type=doc_type,
        status=status,
        province=province,
        node_type=node_type,
        limit=limit,
        offset=offset,
    )

    return {
        "query": q,
        "filters": {
            "doc_type": doc_type,
            "status": status,
            "province": province,
            "node_type": node_type,
        },
        "total": payload["total"],
        "limit": limit,
        "offset": offset,
        "results": payload["results"],
    }

@router.get("/semantic", response_model=SemanticSearchResultsResponse)
def semantic_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    payload = SearchService.semantic_search_documents(
        db=db,
        query=q,
        limit=limit,
    )

    return {
        "query": q,
        "total": payload["total"],
        "limit": limit,
        "results": payload["results"],
    }