ALLOWED_NODE_TYPES = {
    # core operational
    "Survivor",
    "Case",
    "Helper",
    "Organization",
    "Location",

    # need taxonomy
    "NeedCategory",
    "NeedType",
    "UrgencyLevel",

    # service/resource taxonomy
    "Resource",
    "ResourceType",
    "ServiceType",

    # context layer
    "Incident",
    "IncidentType",
    "RiskFactor",
    "Barrier",
    "Assessment",
    "Referral",

    # state/time layer
    "Status",
    "AvailabilityWindow",
    "Priority",
    "CaseStage",
}


ALLOWED_EDGE_TYPES = {
    # core case relationships
    "INVOLVED_IN",
    "LOCATED_IN",
    "TRIGGERED_BY",
    "EXPERIENCED",

    # need relationships
    "HAS_NEED",
    "IS_A",
    "HAS_URGENCY",
    "REQUIRES",

    # service/resource relationships
    "INSTANCE_OF",
    "PROVIDES",
    "SPECIALIZES_IN",
    "OPERATED_BY",
    "AVAILABLE_AT",

    # context/barrier/risk
    "HAS_RISK",
    "BLOCKED_BY",
    "IMPACTS",
    "ASSESSED_AS",

    # helper/referral
    "CAN_SUPPORT",
    "ASSIGNED_TO",
    "REFERRED_TO",
    "FOR_CASE",
    "TO_RESOURCE",

    # status/time
    "HAS_STATUS",
    "AVAILABLE_DURING",
    "UPDATED_TO",
}