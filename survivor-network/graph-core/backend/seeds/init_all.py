"""One-shot init script: create tables + seed all data.

Used as an init container or manual bootstrap:
  python seeds/init_all.py

Idempotent — safe to run on every deploy.
"""
import sys
import os

sys.path.insert(0, "/app")
os.chdir("/app")

print("=== graph-core init ===")

# 1. Create tables (idempotent — create_all skips existing)
print("[1/5] Creating tables...")
from app.db import Base, engine
from models.graph import GraphNodeDB, GraphEdgeDB  # noqa: F401
from models.search import SearchDocumentDB  # noqa: F401
Base.metadata.create_all(bind=engine)
print("      Tables ready.")

# 2. Seed reference data (taxonomy, locations, organizations)
print("[2/5] Seeding reference data...")
try:
    from app.db import SessionLocal
    from models.graph import GraphNodeDB
    _db = SessionLocal()
    _location_count = _db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Location").count()
    _db.close()

    if _location_count > 5:
        print(f"      Already seeded ({_location_count} locations found), skipping.")
    else:
        # Fix known issue: hillbrow_clinic -> hillbrow_chc
        org_path = "/app/seeds/reference/organizations.yaml"
        if os.path.exists(org_path):
            with open(org_path, "r") as f:
                content = f.read()
            if "hillbrow_clinic" in content:
                with open(org_path, "w") as f:
                    f.write(content.replace("hillbrow_clinic", "hillbrow_chc"))
                print("      Fixed hillbrow_clinic -> hillbrow_chc")

        from scripts.seed_reference_data import main as seed_ref
        seed_ref()
except Exception as e:
    print(f"      Reference seed error (may already exist): {e}")

# 3. Seed scenarios
print("[3/5] Seeding scenarios...")
try:
    from app.db import SessionLocal as SL2
    from models.graph import GraphNodeDB as GN2
    _db2 = SL2()
    _scenario_cases = _db2.query(GN2).filter(GN2.node_type == "Incident").count()
    _db2.close()

    if _scenario_cases > 0:
        print(f"      Already seeded ({_scenario_cases} incidents found), skipping.")
    else:
        from scripts.seed_scenarios import main as seed_scenarios
        seed_scenarios()
except Exception as e:
    print(f"      Scenario seed error (may already exist): {e}")

# 4. Seed OSM resources
print("[4/5] Seeding OSM resources...")
try:
    from seeds.seed_osm_via_pod import seed as seed_osm
    seed_osm()
except Exception as e:
    print(f"      OSM seed error: {e}")

# 5. Seed dashboard test cases
print("[5/5] Seeding dashboard test cases...")
try:
    from seeds.seed_dashboard_cases import seed as seed_cases
    seed_cases()
except Exception as e:
    print(f"      Dashboard cases seed error: {e}")

print("=== init complete ===")
