from fastapi import HTTPException
from sqlalchemy import case, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import numpy as np
from sentence_transformers import SentenceTransformer

from models.graph import GraphNodeDB, GraphEdgeDB
from models.search import SearchDocumentDB
from services.graph_service import GraphService


class SearchService:
    @staticmethod
    def _upsert_document(
        db: Session,
        doc_type: str,
        source_node_id,
        title: str,
        content: str,
        metadata: dict,
    ):
        existing = (
            db.query(SearchDocumentDB)
            .filter(
                SearchDocumentDB.doc_type == doc_type,
                SearchDocumentDB.source_node_id == source_node_id,
            )
            .first()
        )

        if existing:
            existing.title = title
            existing.content = content
            existing.metadata_json = metadata
            return existing

        doc = SearchDocumentDB(
            doc_type=doc_type,
            source_node_id=source_node_id,
            title=title,
            content=content,
            metadata_json=metadata,
        )
        db.add(doc)
        return doc
    
    _embedding_model = None

    @staticmethod
    def _get_embedding_model():
        if SearchService._embedding_model is None:
            SearchService._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return SearchService._embedding_model

    @staticmethod
    def _embed_text(text: str) -> list[float]:
        model = SearchService._get_embedding_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        a = np.array(vec_a, dtype=float)
        b = np.array(vec_b, dtype=float)

        if a.size == 0 or b.size == 0:
            return 0.0

        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0

        return float(np.dot(a, b) / denom)
    
    @staticmethod
    def build_embedding_for_document(doc: SearchDocumentDB):
        text = f"{doc.title}\n{doc.content}"
        doc.embedding = SearchService._embed_text(text)
        return doc
    
    @staticmethod
    def build_embeddings_for_all_documents(db: Session):
        docs = db.query(SearchDocumentDB).all()

        for doc in docs:
            SearchService.build_embedding_for_document(doc)

        db.commit()
        return len(docs)
    
    @staticmethod
    def semantic_search_documents(
        db: Session,
        query: str,
        limit: int = 10,
    ):
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query must not be blank")

        query = query.strip()
        query_vector = SearchService._embed_text(query)

        docs = (
            db.query(SearchDocumentDB)
            .filter(SearchDocumentDB.embedding.isnot(None))
            .all()
        )

        scored = []
        for doc in docs:
            score = SearchService._cosine_similarity(query_vector, doc.embedding)
            scored.append((doc, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        top_results = scored[:limit]

        results = []
        for doc, score in top_results:
            results.append(
                {
                    "id": str(doc.id),
                    "doc_type": doc.doc_type,
                    "source_node_id": str(doc.source_node_id) if doc.source_node_id else None,
                    "title": doc.title,
                    "content": doc.content,
                    "snippet": SearchService._build_snippet(doc.content, query),
                    "metadata": doc.metadata_json,
                    "score": float(score),
                    "created_at": doc.created_at,
                }
            )

        return {
            "total": len(scored),
            "results": results,
        }


    @staticmethod
    def build_survivor_support_document(db: Session, survivor_id):
        payload = GraphService.get_support_options_for_survivor(db, survivor_id)

        survivor = payload["survivor"]
        needs = payload["needs"]
        resources = payload["resources"]
        helpers = payload["helpers"]

        title = f"Survivor Support: {survivor['label']}"
        content = (
            f"Survivor {survivor['label']}. "
            f"Needs: {', '.join(n['label'] for n in needs) or 'none'}. "
            f"Resources: {', '.join(r['label'] for r in resources) or 'none'}. "
            f"Helpers: {', '.join(h['label'] for h in helpers) or 'none'}."
        )

        metadata = {
            "node_type": "Survivor",
            "survivor_id": str(survivor["id"]),
        }

        return SearchService._upsert_document(
            db=db,
            doc_type="survivor_support",
            source_node_id=survivor["id"],
            title=title,
            content=content,
            metadata=metadata,
        )

    @staticmethod
    def build_case_support_document(db: Session, case_id):
        payload = GraphService.get_support_options_for_case(db, case_id)

        case = payload["case"]
        survivor_views = payload["survivors"]

        survivor_names = [sv["survivor"]["label"] for sv in survivor_views]
        need_names = []
        resource_names = []
        helper_names = []

        for sv in survivor_views:
            need_names.extend([n["label"] for n in sv["needs"]])
            resource_names.extend([r["label"] for r in sv["resources"]])
            helper_names.extend([h["label"] for h in sv["helpers"]])

        title = f"Case Support: {case['label']}"
        content = (
            f"Case {case['label']} with status {(case['metadata'] or {}).get('status', 'unknown')}. "
            f"Survivors: {', '.join(survivor_names) or 'none'}. "
            f"Needs: {', '.join(sorted(set(need_names))) or 'none'}. "
            f"Resources: {', '.join(sorted(set(resource_names))) or 'none'}. "
            f"Helpers: {', '.join(sorted(set(helper_names))) or 'none'}."
        )

        metadata = {
            "node_type": "Case",
            "case_id": str(case["id"]),
            "status": (case["metadata"] or {}).get("status"),
        }

        return SearchService._upsert_document(
            db=db,
            doc_type="case_support",
            source_node_id=case["id"],
            title=title,
            content=content,
            metadata=metadata,
        )

    @staticmethod
    def build_location_support_document(db: Session, location_id):
        payload = GraphService.get_support_options_for_location(db, location_id)

        location = payload["location"]
        survivors = payload["survivors"]
        cases = payload.get("cases", [])
        needs = payload["needs"]
        resources = payload["resources"]
        helpers = payload["helpers"]

        title = f"Location Support: {location['label']}"
        content = (
            f"Location {location['label']}. "
            f"Survivors: {', '.join(s['label'] for s in survivors) or 'none'}. "
            f"Cases: {', '.join(c['label'] for c in cases) or 'none'}. "
            f"Needs: {', '.join(n['label'] for n in needs) or 'none'}. "
            f"Resources: {', '.join(r['label'] for r in resources) or 'none'}. "
            f"Helpers: {', '.join(h['label'] for h in helpers) or 'none'}."
        )

        metadata = {
            "node_type": "Location",
            "location_id": str(location["id"]),
            "province": (location["metadata"] or {}).get("province"),
        }

        return SearchService._upsert_document(
            db=db,
            doc_type="location_support",
            source_node_id=location["id"],
            title=title,
            content=content,
            metadata=metadata,
        )

    from sqlalchemy import case, func, or_


    @staticmethod
    def _build_snippet(content: str, query: str, size: int = 160):
        if not content:
            return ""

        lower_content = content.lower()
        lower_query = query.lower()

        idx = lower_content.find(lower_query)
        if idx == -1:
            return content[:size]

        start = max(0, idx - 40)
        end = min(len(content), idx + len(query) + 80)
        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet


    @staticmethod
    def search_documents(
        db: Session,
        query: str,
        doc_type: str | None = None,
        status: str | None = None,
        province: str | None = None,
        node_type: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ):
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query must not be blank")

        query = query.strip()

        rank_expr = case(
            (func.lower(SearchDocumentDB.title) == func.lower(query), 3),
            (SearchDocumentDB.title.ilike(f"%{query}%"), 2),
            (SearchDocumentDB.content.ilike(f"%{query}%"), 1),
            else_=0,
        )

        base_query = (
            db.query(SearchDocumentDB, rank_expr.label("rank"))
            .filter(
                or_(
                    SearchDocumentDB.title.ilike(f"%{query}%"),
                    SearchDocumentDB.content.ilike(f"%{query}%"),
                )
            )
        )

        if doc_type:
            base_query = base_query.filter(SearchDocumentDB.doc_type == doc_type)

        if status:
            base_query = base_query.filter(SearchDocumentDB.metadata_json["status"].astext.ilike(status))

        if province:
            base_query = base_query.filter(SearchDocumentDB.metadata_json["province"].astext.ilike(province))

        if node_type:
            base_query = base_query.filter(SearchDocumentDB.metadata_json["node_type"].astext.ilike(node_type))

        total = base_query.count()

        rows = (
            base_query
            .order_by(rank_expr.desc(), SearchDocumentDB.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        results = []
        for doc, rank in rows:
            results.append(
                {
                    "id": doc.id,
                    "doc_type": doc.doc_type,
                    "source_node_id": doc.source_node_id,
                    "title": doc.title,
                    "content": doc.content,
                    "snippet": SearchService._build_snippet(doc.content, query),
                    "metadata": doc.metadata_json,
                    "created_at": doc.created_at,
                }
            )

        return {
            "total": total,
            "results": results,
        }
    
    @staticmethod
    def build_resource_profile_document(db: Session, resource_id):
        resource = db.get(GraphNodeDB, resource_id)
        if not resource or resource.node_type != "Resource":
            raise HTTPException(status_code=404, detail="Resource not found")

        neighbors = GraphService.get_neighbors(db, resource_id)

        resource_types = []
        need_types = []
        locations = []
        organizations = []
        statuses = []

        for item in neighbors:
            edge_type = item["edge_type"]
            node = item["node"]

            if edge_type == "INSTANCE_OF":
                resource_types.append(node["label"])
            elif edge_type == "PROVIDES":
                need_types.append(node["label"])
            elif edge_type == "LOCATED_IN":
                locations.append(node["label"])
            elif edge_type == "OPERATED_BY":
                organizations.append(node["label"])
            elif edge_type == "HAS_STATUS":
                statuses.append(node["label"])

        title = f"Resource Profile: {resource.label}"
        content = (
            f"Resource {resource.label}. "
            f"Types: {', '.join(sorted(set(resource_types))) or 'none'}. "
            f"Provides: {', '.join(sorted(set(need_types))) or 'none'}. "
            f"Locations: {', '.join(sorted(set(locations))) or 'none'}. "
            f"Organizations: {', '.join(sorted(set(organizations))) or 'none'}. "
            f"Statuses: {', '.join(sorted(set(statuses))) or 'none'}."
        )

        metadata = {
            "node_type": "Resource",
            "resource_id": str(resource.id),
        }

        return SearchService._upsert_document(
            db=db,
            doc_type="resource_profile",
            source_node_id=resource.id,
            title=title,
            content=content,
            metadata=metadata,
        )


    @staticmethod
    def build_organization_profile_document(db: Session, org_id):
        org = db.get(GraphNodeDB, org_id)
        if not org or org.node_type != "Organization":
            raise HTTPException(status_code=404, detail="Organization not found")

        incoming_edges = (
            db.query(GraphEdgeDB)
            .filter(
                GraphEdgeDB.to_node_id == org_id,
                GraphEdgeDB.edge_type == "OPERATED_BY",
            )
            .all()
        )

        operated_resources = []
        for edge in incoming_edges:
            resource = db.get(GraphNodeDB, edge.from_node_id)
            if resource and resource.node_type == "Resource":
                operated_resources.append(resource)

        resource_names = [r.label for r in operated_resources]

        title = f"Organization Profile: {org.label}"
        content = (
            f"Organization {org.label}. "
            f"Operates resources: {', '.join(sorted(set(resource_names))) or 'none'}."
        )

        metadata = {
            "node_type": "Organization",
            "organization_id": str(org.id),
        }

        return SearchService._upsert_document(
            db=db,
            doc_type="organization_profile",
            source_node_id=org.id,
            title=title,
            content=content,
            metadata=metadata,
        )
    