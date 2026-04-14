export type CaseLocation = {
  latitude: number;
  longitude: number;
  location_source: string;
  accuracy_meters: number | null;
  is_approximate: boolean;
  consent_to_share: boolean;
  captured_at: string | null;
};

export type Urgency = "low" | "normal" | "urgent" | "critical";
export type CaseStatus = "new" | "in_progress" | "escalated" | "resolved";

export type CaseNote = {
  id: string;
  text: string;
  author: string;
  created_at: string;
};

export type CaseRecord = {
  case_id: string;
  label: string;
  note_count: number;
  incident_summary: string;
  incident_summary_short: string;
  urgency: Urgency;
  raw_urgency: string;
  status: CaseStatus;
  raw_status: string;
  safety_risk: string;
  queue: string | null;
  created_at: string;
  updated_at: string;
  location: CaseLocation | null;
  normalized_location: string | null;
  primary_needs: string[];
  incident_types: string[];
  requires_human_review: boolean;
  escalation_recommended: boolean;
  assigned_to: string | null;
  assigned_to_name: string | null;
  survivor: {
    id: string;
    node_type: string;
    label: string;
    metadata: Record<string, unknown>;
    created_at: string | null;
  } | null;
};

export type CasesResponse = {
  cases: CaseRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type StatsResponse = {
  total_cases: number;
  by_status: Record<string, number>;
  by_urgency: Record<string, number>;
  with_location: number;
};

export type CaseWorker = {
  id: string;
  name: string;
};

export type FilterState = {
  status: CaseStatus | "all";
  hasLocation: boolean;
  assignedTo?: string;
};

export type ResourceMarker = {
  id: string;
  name: string;
  type: "hospital" | "clinic" | "police" | "shelter" | "ngo" | "hotline" | "counseling" | "legal" | "other";
  raw_type: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  phone: string;
  address: string;
  hours: string;
  services: string[];
};

export type NearbyResourcesResponse = {
  resources: ResourceMarker[];
  center: { lat: number; lon: number };
  radius_km: number;
};

export type ResourceTypeFilter = ResourceMarker["type"];