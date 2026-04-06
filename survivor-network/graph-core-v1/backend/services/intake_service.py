import re
from dataclasses import dataclass
from sqlalchemy.orm import Session
from models.graph import GraphNodeDB


@dataclass
class IntakeParseResult:
    message: str
    normalized_location: str | None
    primary_needs: list[str]
    derived_support_needs: list[str]
    normalized_barriers: list[str]


class IntakeService:
    """
    Deterministic text normalizer that maps free-text user input
    into ontology labels already present in the graph.
    """

    NEED_PATTERNS: dict[str, list[str]] = {
        "Emergency Medical": [
            r"\bmedical help\b",
            r"\bneed medical\b",
            r"\bclinic\b",
            r"\bhospital\b",
            r"\binjured\b",
            r"\bemergency\b",
            r"\bbleeding\b",
            r"\bdoctor\b",
            r"\bambulance\b",
            r"\bmedical attention\b",
        ],
        "Medication Access": [
            r"\bmedication\b",
            r"\bmedicine\b",
            r"\bpills\b",
            r"\bprescription\b",
            r"\bno medication\b",
            r"\bout of medicine\b",
        ],
        "Mental Health Support": [
            r"\btrauma\b",
            r"\btraumatized\b",
            r"\btraumatised\b",
            r"\banxiety\b",
            r"\bpanic\b",
            r"\bmental health\b",
            r"\bcounselling\b",
            r"\bcounseling\b",
            r"\bneed someone to talk to\b",
            r"\bneed to talk to someone\b",
            r"\bneed support\b",
            r"\bi need support\b",
            r"\bemotional support\b",
            r"\bcrisis support\b",
            r"\bi am overwhelmed\b",
            r"\bi feel unsafe and overwhelmed\b",
            r"\btherapy\b",
            r"\bneed counselling\b",
            r"\bneed counseling\b",
        ],
        "Emergency Shelter": [
            r"\bshelter\b",
            r"\bnowhere to stay\b",
            r"\bno place to sleep\b",
            r"\bsafe house\b",
            r"\bunsafe home\b",
            r"\bsafe place to stay\b",
            r"\bsomewhere safe\b",
            r"\bplace to stay\b",
            r"\bnowhere to sleep\b",
            r"\bscared to go home\b",
            r"\bsomewhere safe to stay\b",
            r"\bsafe to stay\b",
            r"\bstay tonight\b",
            r"\bnot safe at home\b",
            r"\bsomewhere safe to stay\b",
            r"\bsafe to stay\b",
            r"\bstay tonight\b",
            r"\bnot safe at home\b",
        ],
        "Protection Order Support": [
            r"\bprotection order\b",
            r"\blegal help\b",
            r"\bcourt\b",
            r"\bpolice report\b",
            r"\brestraining order\b",
            r"\babuse\b",
            r"\bthreatened me\b",
            r"\bpartner threatened me\b",
            r"\bpartner threatened me\b",
        ],
        "Transport": [
            r"\bneed transport\b",
            r"\bneed a ride\b",
            r"\bneed taxi\b",
            r"\btransport assistance\b",
            r"\bhelp me get there\b",
            r"\bget to the clinic\b",
            r"\bget to hospital\b",
        ],
    }

    BARRIER_PATTERNS: dict[str, list[str]] = {
        "No Transport": [
            r"\bno transport\b",
            r"\bcan.?t travel\b",
            r"\bno taxi\b",
            r"\bno money for transport\b",
            r"\bstranded\b",
            r"\bneed a ride\b",
        ],
        "No Phone": [
            r"\bno phone\b",
            r"\bphone stolen\b",
            r"\bcan.?t call\b",
            r"\bno airtime\b",
        ],
        "Unsafe To Travel": [
            r"\bunsafe to travel\b",
            r"\bnot safe to leave\b",
            r"\bafraid to go out\b",
            r"\bscared to leave\b",
        ],
        "No ID Document": [
            r"\bno id\b",
            r"\bmissing id\b",
            r"\bno document\b",
            r"\bno id document\b",
        ],
    }

    LOCATION_ALIASES: dict[str, list[str]] = {
        "Johannesburg": [r"\bjohannesburg\b", r"\bjoburg\b", r"\bjhb\b", r"\bjozi\b"],
        "Gauteng": [r"\bgauteng\b"],
        "South Africa": [r"\bsouth africa\b", r"\bza\b", r"\brsa\b"],
    }

    BARRIER_TO_SUPPORT_NEED: dict[str, str] = {
        "No Transport": "Transport",
        "No Phone": "Transport",
        "Unsafe To Travel": "Transport",
        "No ID Document": "Protection Order Support",
    }

    @staticmethod
    def _find_matches(text: str, pattern_map: dict[str, list[str]]) -> list[str]:
        matches: list[str] = []
        for label, patterns in pattern_map.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    matches.append(label)
                    break
        return matches

    @staticmethod
    def _resolve_known_label(db: Session, label: str, allowed_types: list[str]) -> str | None:
        node = (
            db.query(GraphNodeDB)
            .filter(
                GraphNodeDB.label == label,
                GraphNodeDB.node_type.in_(allowed_types),
            )
            .first()
        )
        return node.label if node else None

    @staticmethod
    def parse_message(db: Session, message: str, explicit_location: str | None = None) -> IntakeParseResult:
        text = message.strip()

        normalized_barriers = IntakeService._find_matches(text, IntakeService.BARRIER_PATTERNS)
        matched_needs = IntakeService._find_matches(text, IntakeService.NEED_PATTERNS)

        primary_needs: list[str] = []
        derived_support_needs: list[str] = []

        for need in matched_needs:
            if need == "Transport":
                if need not in derived_support_needs:
                    derived_support_needs.append(need)
            else:
                if need not in primary_needs:
                    primary_needs.append(need)

        normalized_location: str | None = None

        if explicit_location:
            normalized_location = IntakeService._resolve_known_label(
                db,
                explicit_location,
                ["Location"],
            ) or explicit_location
        else:
            for label, patterns in IntakeService.LOCATION_ALIASES.items():
                if any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
                    normalized_location = (
                        IntakeService._resolve_known_label(db, label, ["Location"]) or label
                    )
                    break

        if not primary_needs:
            if re.search(
                r"\bmedical\b|\bdoctor\b|\bclinic\b|\bhospital\b|\bbleeding\b",
                text,
                flags=re.IGNORECASE,
            ):
                primary_needs.append("Emergency Medical")
            if re.search(
                r"\bshelter\b|\bsafe\b|\bstay\b|\bhome\b",
                text,
                flags=re.IGNORECASE,
            ):
                primary_needs.append("Emergency Shelter")
            if re.search(
                r"\blegal\b|\bprotection order\b|\bcourt\b|\bpolice\b",
                text,
                flags=re.IGNORECASE,
            ):
                primary_needs.append("Protection Order Support")
            if re.search(
                r"\btrauma\b|\btraumatized\b|\bcounselling\b|\bcounseling\b|\boverwhelmed\b",
                text,
                flags=re.IGNORECASE,
            ):
                primary_needs.append("Mental Health Support")

        for barrier in normalized_barriers:
            support_need = IntakeService.BARRIER_TO_SUPPORT_NEED.get(barrier)
            if support_need and support_need not in derived_support_needs:
                derived_support_needs.append(support_need)

        primary_needs = sorted(set(primary_needs))
        derived_support_needs = sorted(
            set(n for n in derived_support_needs if n not in primary_needs)
        )

        # If a derived support need also landed in primary_needs because of barrier wording,
        # keep it in derived_support_needs instead.
        for barrier in normalized_barriers:
            support_need = IntakeService.BARRIER_TO_SUPPORT_NEED.get(barrier)
            if support_need and support_need in primary_needs:
                primary_needs.remove(support_need)
                if support_need not in derived_support_needs:
                    derived_support_needs.append(support_need)

        primary_needs = sorted(set(primary_needs))
        derived_support_needs = sorted(set(derived_support_needs))
        normalized_barriers = sorted(set(normalized_barriers))

        return IntakeParseResult(
            message=message,
            normalized_location=normalized_location,
            primary_needs=primary_needs,
            derived_support_needs=derived_support_needs,
            normalized_barriers=normalized_barriers,
        )