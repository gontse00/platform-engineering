from app.db import SessionLocal
from models.graph import GraphNodeDB
from services.search_service import SearchService


def main():
    db = SessionLocal()
    try:
        survivors = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Survivor").all()
        cases = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Case").all()
        locations = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Location").all()
        resources = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Resource").all()
        organizations = db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Organization").all()

        for survivor in survivors:
            SearchService.build_survivor_support_document(db, survivor.id)

        for case in cases:
            SearchService.build_case_support_document(db, case.id)

        for location in locations:
            SearchService.build_location_support_document(db, location.id)

        for resource in resources:
            SearchService.build_resource_profile_document(db, resource.id)

        for org in organizations:
            SearchService.build_organization_profile_document(db, org.id)

        db.commit()
        print("Search documents built successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()