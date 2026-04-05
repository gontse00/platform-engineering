from pathlib import Path
import sys
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.db import SessionLocal
from models.graph import GraphEdgeDB, GraphNodeDB

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIO_DIR = BASE_DIR / "seeds" / "scenarios"

def get_scenario_files() -> list[Path]:
    files = list(SCENARIO_DIR.glob("*.yaml"))
    files += list((SCENARIO_DIR / "generated").glob("*.yaml"))
    return sorted(files)


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


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_node_ref(db, ref: str, scenario_key_to_node: dict):
    # first try scenario-local key
    node = scenario_key_to_node.get(ref)
    if node:
        return node

    # then try label lookup in DB (for reference data or pre-existing scenario nodes)
    return get_node_by_label(db, ref)


def seed_scenario_file(db, file_path: Path):
    payload = load_yaml(file_path)
    scenario_key_to_node = {}

    # pass 1: create all nodes first
    for node_data in payload.get("nodes", []):
        node = get_or_create_node(
            db=db,
            node_type=node_data["node_type"],
            label=node_data["label"],
            metadata=node_data.get("metadata", {}),
        )
        if "key" in node_data:
            scenario_key_to_node[node_data["key"]] = node

    # pass 2: create edges
    for edge_data in payload.get("edges", []):
        from_node = resolve_node_ref(db, edge_data["from"], scenario_key_to_node)
        to_node = resolve_node_ref(db, edge_data["to"], scenario_key_to_node)

        get_or_create_edge(
            db=db,
            from_node_id=from_node.id,
            to_node_id=to_node.id,
            edge_type=edge_data["edge_type"],
            metadata=edge_data.get("metadata", {}),
        )


def main():
    db = SessionLocal()
    try:
        for file_path in get_scenario_files():
            seed_scenario_file(db, file_path)

        db.commit()
        print("Scenario data seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()