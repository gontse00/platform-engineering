"""Seed real OSM resource data directly into the database.

Run inside the graph-core pod:
  python seeds/seed_osm_via_pod.py
"""
import sys, os
sys.path.insert(0, "/app")
os.chdir("/app")

from app.db import SessionLocal
from models.graph import GraphNodeDB

OSM_RESOURCES = [
    # --- Hospitals (from Overpass API, Gauteng) ---
    {"name": "Bougainville Hospital", "lat": -25.7175, "lon": 28.1537, "type": "public_hospital", "phone": "+27 12 377 5700", "address": "647 Redelinghuys Street, Pretoria"},
    {"name": "Tshwane District Hospital", "lat": -25.7327, "lon": 28.2007, "type": "public_hospital", "phone": "+27 12 354 7000", "address": "349-Jr Doctor Savage Road, Pretoria"},
    {"name": "Lilian Ngoyi Community Clinic", "lat": -26.2601, "lon": 27.9326, "type": "public_clinic", "phone": "+27 11 933 0202", "address": "Chris Hani Road, Johannesburg"},
    {"name": "Orlando Clinic", "lat": -26.2370, "lon": 27.9192, "type": "public_clinic", "phone": "+27 11 935 5186", "address": "6516 Rathebe Street, Soweto"},
    {"name": "Randfontein Hospital", "lat": -26.1805, "lon": 27.7119, "type": "public_hospital", "phone": "", "address": "Randfontein"},
    {"name": "Life Flora Clinic", "lat": -26.1518, "lon": 27.9197, "type": "private_hospital", "phone": "+27 11 470 7777", "address": "William Nicol St North, Roodepoort"},
    {"name": "Akeso Arcadia", "lat": -25.7472, "lon": 28.2238, "type": "private_hospital", "phone": "+27 87 098 0459", "address": "871 Francis Baard St, Arcadia, Pretoria"},
    {"name": "Carecross Health", "lat": -25.7601, "lon": 28.2416, "type": "private_hospital", "phone": "+27 860 103 491", "address": "230 Brooks Street, Pretoria"},
    {"name": "RH Bell Hospital", "lat": -26.0972, "lon": 27.8045, "type": "private_hospital", "phone": "+27 119541023", "address": "Bell Drive, Krugersdorp"},
    {"name": "Life Groenkloof Hospital", "lat": -25.7708, "lon": 28.2164, "type": "private_hospital", "phone": "+27 124243600", "address": "50 George Storrar Drive, Pretoria"},
    {"name": "Sunward Park Hospital Netcare", "lat": -26.2599, "lon": 28.2568, "type": "private_hospital", "phone": "+27 118971600", "address": "Kingfisher Avenue, Boksburg"},
    {"name": "Bertha Gxowa Hospital", "lat": -26.2201, "lon": 28.1636, "type": "public_hospital", "phone": "+27 112787600", "address": "Angus St, Germiston South"},
    {"name": "Thelle Mogoerane Regional Hospital", "lat": -26.3571, "lon": 28.2244, "type": "public_hospital", "phone": "+27 118917000", "address": "12390 Nguza Street, Vosloorus"},
    {"name": "Clinix Botshelong-Empilweni", "lat": -26.3445, "lon": 28.2183, "type": "private_hospital", "phone": "+27 118616200", "address": "9 Sam Sekoati Ave, Vosloorus"},
    {"name": "Sediba Hope Medical Centre", "lat": -25.7524, "lon": 28.2117, "type": "private_hospital", "phone": "+27 83 307 4063", "address": "50 Vos Street, Pretoria"},
    {"name": "Weskoppies Hospital", "lat": -25.7462, "lon": 28.1646, "type": "public_hospital", "phone": "+27 12 319 9500", "address": "Ketjen Street, Pretoria"},
    {"name": "Bronkhorstspruit Hospital", "lat": -25.8036, "lon": 28.7164, "type": "public_hospital", "phone": "+27 13 935 1275", "address": "102 Old Bronkhorstspruit Rd, Tshwane"},
    {"name": "Cullinan Hospital", "lat": -25.6653, "lon": 28.5157, "type": "public_hospital", "phone": "", "address": "100 Hospital Road, Tshwane"},
    {"name": "Mamelodi Hospital", "lat": -25.7197, "lon": 28.3690, "type": "public_hospital", "phone": "", "address": "23 Serapeng Avenue, Tshwane"},
    {"name": "Netcare Unitas Hospital", "lat": -25.8321, "lon": 28.1950, "type": "private_hospital", "phone": "+27 126778000", "address": "866 Clifton Ave, Centurion"},
    {"name": "Lenmed Zamokuhle Private Hospital", "lat": -25.9837, "lon": 28.2400, "type": "private_hospital", "phone": "+27 87 087 0643", "address": "128 Flint Mazibuko Drive, Tembisa"},
    {"name": "Tambo Memorial Hospital", "lat": -26.2183, "lon": 28.2448, "type": "public_hospital", "phone": "+27 118988000", "address": "Railway Street, Boksburg"},
    {"name": "Chris Hani Baragwanath Academic Hospital", "lat": -26.2614, "lon": 27.9449, "type": "public_hospital", "phone": "+27 11 933 8000", "address": "Chris Hani Road, Soweto"},
    {"name": "Pholosong Hospital", "lat": -26.3398, "lon": 28.3759, "type": "public_hospital", "phone": "", "address": "Indaba Street"},
    {"name": "Helen Joseph Hospital", "lat": -26.1739, "lon": 27.9991, "type": "public_hospital", "phone": "+27 11 489 0111", "address": "Auckland Park, Johannesburg"},
    {"name": "Rahima Moosa Mother and Child Hospital", "lat": -26.1750, "lon": 27.9810, "type": "public_hospital", "phone": "+27 11 470 9000", "address": "Fuel Road, Coronationville, Johannesburg"},
    # --- Police Stations (from Overpass API, Gauteng) ---
    {"name": "SAPS Soweto (Jabulani)", "lat": -26.2482, "lon": 27.8586, "type": "police_station", "phone": "+27 11 527 7000", "address": "Bolani Road, Jabulani, Johannesburg"},
    {"name": "Johannesburg Central Police Station", "lat": -26.2062, "lon": 28.0319, "type": "police_station", "phone": "+27 114977000", "address": "1 Commissioner Street, Johannesburg"},
    {"name": "Meadowlands Police Station", "lat": -26.2215, "lon": 27.8999, "type": "police_station", "phone": "", "address": "Meadowlands, Soweto"},
    {"name": "Orlando East SAPS", "lat": -26.2386, "lon": 27.9195, "type": "police_station", "phone": "", "address": "Orlando East, Soweto"},
    {"name": "Diepsloot Police Station", "lat": -25.9223, "lon": 28.0221, "type": "police_station", "phone": "+27 113676300", "address": "1 Buffalo Street, Diepsloot"},
    {"name": "SAPS Ga-Rankuwa", "lat": -25.5994, "lon": 27.9989, "type": "police_station", "phone": "+27 127978800", "address": "6543 Kgotleng Street, Ga-Rankuwa"},
    {"name": "Pretoria Central Police Station", "lat": -25.7483, "lon": 28.1855, "type": "police_station", "phone": "", "address": "Pretoria"},
    {"name": "SAPS Edenvale", "lat": -26.1484, "lon": 28.1492, "type": "police_station", "phone": "", "address": "Edenvale"},
    {"name": "SAPS Silverton", "lat": -25.7332, "lon": 28.2963, "type": "police_station", "phone": "", "address": "Silverton, Pretoria"},
    {"name": "SAPS Randburg Police Station", "lat": -26.0760, "lon": 27.9966, "type": "police_station", "phone": "", "address": "Randburg"},
    {"name": "Parkview Police Station", "lat": -26.1592, "lon": 28.0266, "type": "police_station", "phone": "", "address": "Parkview, Johannesburg"},
    {"name": "Honeydew Police Station", "lat": -26.0729, "lon": 27.9202, "type": "police_station", "phone": "", "address": "Honeydew"},
    {"name": "Eldorado Park Police Station", "lat": -26.2915, "lon": 27.9007, "type": "police_station", "phone": "", "address": "Eldorado Park"},
    {"name": "Vereeniging Police Station", "lat": -26.6792, "lon": 27.9302, "type": "police_station", "phone": "+27 16 450 2043", "address": "Voortrekker Street, Vereeniging"},
    {"name": "Vosloorus Police Station", "lat": -26.3426, "lon": 28.2113, "type": "police_station", "phone": "", "address": "Vosloorus"},
    {"name": "Katlehong Police Station", "lat": -26.3151, "lon": 28.1571, "type": "police_station", "phone": "", "address": "Katlehong"},
    {"name": "Tokoza Police Station", "lat": -26.3284, "lon": 28.1428, "type": "police_station", "phone": "", "address": "Tokoza"},
    {"name": "Booysens Police Station", "lat": -26.2336, "lon": 28.0217, "type": "police_station", "phone": "", "address": "Booysens, Johannesburg"},
    {"name": "Brixton SAPS", "lat": -26.1938, "lon": 28.0075, "type": "police_station", "phone": "", "address": "Brixton, Johannesburg"},
    {"name": "Fairlands SAPS", "lat": -26.1442, "lon": 27.9376, "type": "police_station", "phone": "+27 114789413", "address": "Fairlands"},
    {"name": "Douglasdale Police Station", "lat": -26.0264, "lon": 27.9907, "type": "police_station", "phone": "", "address": "Douglasdale"},
    {"name": "Muldersdrift Police Station", "lat": -26.0381, "lon": 27.8508, "type": "police_station", "phone": "", "address": "Muldersdrift"},
    {"name": "Pretoria North Police Station", "lat": -25.6711, "lon": 28.1737, "type": "police_station", "phone": "", "address": "Pretoria North"},
]

def seed():
    db = SessionLocal()
    try:
        existing_labels = {
            n.label for n in db.query(GraphNodeDB).filter(GraphNodeDB.node_type == "Resource").all()
        }
        added = 0
        for r in OSM_RESOURCES:
            if r["name"] in existing_labels:
                continue
            node = GraphNodeDB(
                node_type="Resource",
                label=r["name"],
                metadata_json={
                    "type": r["type"],
                    "lat": r["lat"],
                    "lon": r["lon"],
                    "phone": r.get("phone", ""),
                    "address": r.get("address", ""),
                    "hours": "",
                    "services": [],
                    "source": "openstreetmap",
                },
            )
            db.add(node)
            added += 1
        db.commit()
        print(f"Seeded {added} OSM resources (skipped {len(OSM_RESOURCES) - added} duplicates)")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
