from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "seeds" / "scenarios" / "generated"


FIRST_NAMES = [
    "Amina",
    "Carol",
    "Lerato",
    "Naledi",
    "Thandi",
    "Zanele",
    "Ayanda",
    "Busi",
    "Kgomotso",
    "Nomsa",
]

HELPERS = [
    {"label": "David", "helper_type": "volunteer", "supports": ["Transport"]},
    {"label": "Social Worker Team", "helper_type": "social_worker", "supports": ["Mental Health Support"]},
    {"label": "Shelter Coordinator", "helper_type": "case_worker", "supports": ["Emergency Shelter"]},
    {"label": "Legal Intake Worker", "helper_type": "legal_worker", "supports": ["Protection Order Support"]},
]

SCENARIO_TEMPLATES = [
    {
        "template": "urgent_medical",
        "need_labels": ["Emergency Medical"],
        "incident_label": "Assault",
        "barrier_labels": ["No Transport"],
        "helper_label": "David",
        "helper_supports": ["Transport"],
        "case_prefix": "Medical",
    },
    {
        "template": "shelter_request",
        "need_labels": ["Emergency Shelter"],
        "incident_label": "Displacement",
        "barrier_labels": [],
        "helper_label": "Shelter Coordinator",
        "helper_supports": ["Emergency Shelter"],
        "case_prefix": "Shelter",
    },
    {
        "template": "legal_support",
        "need_labels": ["Protection Order Support"],
        "incident_label": "Domestic Violence",
        "barrier_labels": ["No Phone"],
        "helper_label": "Legal Intake Worker",
        "helper_supports": ["Protection Order Support"],
        "case_prefix": "Legal",
    },
    {
        "template": "psychosocial_support",
        "need_labels": ["Mental Health Support"],
        "incident_label": "Assault",
        "barrier_labels": [],
        "helper_label": "Social Worker Team",
        "helper_supports": ["Mental Health Support"],
        "case_prefix": "Psychosocial",
    },
    {
        "template": "multi_need",
        "need_labels": ["Emergency Medical", "Emergency Shelter"],
        "incident_label": "Domestic Violence",
        "barrier_labels": ["No Transport"],
        "helper_label": "David",
        "helper_supports": ["Transport"],
        "case_prefix": "MultiNeed",
    },
]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def node(key: str, node_type: str, label: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "node_type": node_type,
        "label": label,
        "metadata": metadata or {},
    }


def edge(from_ref: str, to_ref: str, edge_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "from": from_ref,
        "to": to_ref,
        "edge_type": edge_type,
        "metadata": metadata or {},
    }


def build_scenario(index: int, template: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    survivor_name = random.choice(FIRST_NAMES)
    case_label = f"Case-{1000 + index}"
    incident_label = f"{template['incident_label']} Incident - {case_label}"

    survivor_key = f"survivor_{slugify(survivor_name)}_{index}"
    case_key = f"case_{1000 + index}"
    incident_key = f"incident_{1000 + index}"
    helper_key = f"helper_{slugify(template['helper_label'])}_{index}"

    nodes: list[dict[str, Any]] = [
        node(
            key=survivor_key,
            node_type="Survivor",
            label=f"{survivor_name} {index}",
            metadata={
                "age_group": random.choice(["adult", "young_adult"]),
                "source": "generated",
                "template": template["template"],
            },
        ),
        node(
            key=case_key,
            node_type="Case",
            label=case_label,
            metadata={
                "source": "generated",
                "template": template["template"],
                "case_family": template["case_prefix"],
            },
        ),
        node(
            key=incident_key,
            node_type="Incident",
            label=incident_label,
            metadata={
                "source": "generated",
                "template": template["template"],
            },
        ),
        node(
            key=helper_key,
            node_type="Helper",
            label=f"{template['helper_label']} {index}",
            metadata={
                "helper_type": slugify(template["helper_label"]),
                "source": "generated",
            },
        ),
    ]

    edges: list[dict[str, Any]] = [
        edge(survivor_key, case_key, "INVOLVED_IN"),
        edge(survivor_key, "Johannesburg", "LOCATED_IN"),
        edge(case_key, incident_key, "TRIGGERED_BY"),
        edge(incident_key, template["incident_label"], "INSTANCE_OF"),
        edge(helper_key, "Johannesburg", "LOCATED_IN"),
        edge(helper_key, case_key, "ASSIGNED_TO"),
    ]

    for need_label in template["need_labels"]:
        edges.append(edge(survivor_key, need_label, "HAS_NEED"))

    for barrier_label in template["barrier_labels"]:
        barrier_key = f"barrier_{slugify(barrier_label)}_{index}"
        nodes.append(
            node(
                key=barrier_key,
                node_type="Barrier",
                label=barrier_label,
                metadata={"source": "generated"},
            )
        )
        edges.append(edge(survivor_key, barrier_key, "BLOCKED_BY"))

    for support_label in template["helper_supports"]:
        edges.append(edge(helper_key, support_label, "CAN_SUPPORT"))

    return {"nodes": nodes, "edges": edges}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def main() -> None:
    random.seed(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated_files: list[Path] = []
    total = 20

    for i in range(total):
        template = SCENARIO_TEMPLATES[i % len(SCENARIO_TEMPLATES)]
        payload = build_scenario(i + 1, template)
        filename = f"{i + 1:02d}_{template['template']}.yaml"
        path = OUTPUT_DIR / filename
        write_yaml(path, payload)
        generated_files.append(path)

    print(f"Generated {len(generated_files)} scenario files in {OUTPUT_DIR}")
    for path in generated_files:
        print(f" - {path.name}")


if __name__ == "__main__":
    main()