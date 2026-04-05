from pathlib import Path
import sys
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.db import SessionLocal
from models.graph import GraphEdgeDB, GraphNodeDB

REFERENCE_FILES = [
    "locations.yaml",
    "statuses.yaml",
    "need_taxonomy.yaml",
    "resource_taxonomy.yaml",
    "organizations.yaml",
    "incident_taxonomy.yaml",
]

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "seeds" / "reference"


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_or_create_node(db, node_type: str, label: str, metadata: dict):
    existing = (
        db.query(GraphNodeDB)
        .filter(
            GraphNodeDB.node_type == node_type,
            GraphNodeDB.label == label,
        )
        .first()
    )
    if existing:
        return existing

    node = GraphNodeDB(
        node_type=node_type,
        label=label,
        metadata_json=metadata or {},
    )
    db.add(node)
    db.flush()
    return node


def get_node_by_label(db, label: str):
    node = db.query(GraphNodeDB).filter(GraphNodeDB.label == label).first()
    if not node:
        raise ValueError(f"Referenced node not found for label: {label}")
    return node


def get_or_create_edge(db, from_node_id, to_node_id, edge_type: str, metadata: dict):
    existing = (
        db.query(GraphEdgeDB)
        .filter(
            GraphEdgeDB.from_node_id == from_node_id,
            GraphEdgeDB.to_node_id == to_node_id,
            GraphEdgeDB.edge_type == edge_type,
        )
        .first()
    )
    if existing:
        return existing

    edge = GraphEdgeDB(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_type=edge_type,
        metadata_json=metadata or {},
    )
    db.add(edge)
    db.flush()
    return edge


def resolve_node_ref(db, ref: str, global_key_to_node: dict):
    # first try key lookup
    node = global_key_to_node.get(ref)
    if node:
        return node

    # then try DB label lookup
    return get_node_by_label(db, ref)


def main():
    db = SessionLocal()
    try:
        global_key_to_node = {}
        payloads = []

        # pass 0: load all yamls into memory
        for filename in REFERENCE_FILES:
            file_path = REFERENCE_DIR / filename
            if file_path.exists():
                payloads.append((filename, load_yaml(file_path)))

        # pass 1: create all nodes first
        for filename, payload in payloads:
            for node_data in payload.get("nodes", []):
                node = get_or_create_node(
                    db=db,
                    node_type=node_data["node_type"],
                    label=node_data["label"],
                    metadata=node_data.get("metadata", {}),
                )
                if "key" in node_data:
                    global_key_to_node[node_data["key"]] = node

        # pass 2: create all edges
        for filename, payload in payloads:
            for edge_data in payload.get("edges", []):
                if "from" in edge_data and "to" in edge_data:
                    from_node = resolve_node_ref(db, edge_data["from"], global_key_to_node)
                    to_node = resolve_node_ref(db, edge_data["to"], global_key_to_node)
                else:
                    from_node = get_node_by_label(db, edge_data["from_label"])
                    to_node = get_node_by_label(db, edge_data["to_label"])

                get_or_create_edge(
                    db=db,
                    from_node_id=from_node.id,
                    to_node_id=to_node.id,
                    edge_type=edge_data["edge_type"],
                    metadata=edge_data.get("metadata", {}),
                )

        db.commit()
        print("Reference data seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()