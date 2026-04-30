import { ADMIN_SERVICE_URL, GRAPH_CORE_URL } from "./config";
import type {
  CaseNote,
  CaseWorker,
  CasesResponse,
  CaseRecord,
  FilterState,
  NearbyResourcesResponse,
  StatsResponse,
} from "./types";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
let _authToken: string | null = null;

export function setAuthToken(token: string | null) {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

function authHeaders(): Record<string, string> {
  if (!_authToken) return {};
  return { Authorization: `Bearer ${_authToken}` };
}

// ---------------------------------------------------------------------------
// Mapper: admin-service/incident-service case → UI CaseRecord shape
// ---------------------------------------------------------------------------

function mapAdminCaseToCaseRecord(c: Record<string, unknown>): CaseRecord {
  const summary = (c.summary as string) || "";
  const urgencyMap: Record<string, string> = {
    critical: "critical",
    urgent: "urgent",
    medium: "normal",
    standard: "normal",
    low: "low",
  };
  const rawUrgency = (c.urgency as string) || "standard";
  const mappedUrgency = urgencyMap[rawUrgency] || "normal";

  const lat = c.latitude as number | null;
  const lon = c.longitude as number | null;
  const location = lat != null && lon != null
    ? {
        latitude: lat,
        longitude: lon,
        location_source: "incident-service",
        accuracy_meters: null,
        is_approximate: true,
        consent_to_share: true,
        captured_at: (c.created_at as string) || null,
      }
    : null;

  return {
    case_id: (c.id as string) || (c.case_id as string) || "",
    label: `Case - ${((c.id as string) || "").slice(0, 8)}`,
    note_count: 0,
    incident_summary: summary,
    incident_summary_short: summary.length > 120 ? summary.slice(0, 120) + "..." : summary,
    urgency: mappedUrgency as CaseRecord["urgency"],
    raw_urgency: rawUrgency,
    status: ((c.status as string) || "new") as CaseRecord["status"],
    raw_status: (c.status as string) || "new",
    safety_risk: (c.safety_risk as string) || "low",
    queue: null,
    created_at: (c.created_at as string) || "",
    updated_at: (c.updated_at as string) || (c.created_at as string) || "",
    location,
    normalized_location: (c.location_text as string) || null,
    primary_needs: (c.needs as string[]) || [],
    incident_types: c.incident_type ? [c.incident_type as string] : [],
    requires_human_review: rawUrgency === "critical",
    escalation_recommended: rawUrgency === "critical" || rawUrgency === "urgent",
    assigned_to: (c.assigned_participant_id as string) || null,
    assigned_to_name: null,
    survivor: null,
  };
}

// ---------------------------------------------------------------------------
// Cases — via admin-service (primary) with graph-core fallback
// ---------------------------------------------------------------------------

export async function fetchCases(
  filters: FilterState,
  limit = 50,
  offset = 0,
): Promise<CasesResponse> {
  const params = new URLSearchParams();
  if (filters.status !== "all") params.set("status", filters.status);
  if (filters.hasLocation) params.set("has_location", "true");
  if (filters.assignedTo) params.set("assigned_to", filters.assignedTo);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  // Try admin-service first (incident-service backed)
  try {
    const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases?${params}`, {
      headers: authHeaders(),
    });
    if (resp.ok) {
      const data = await resp.json();
      const cases = (data.cases || []).map(mapAdminCaseToCaseRecord);
      return { cases, total: data.total || cases.length, limit, offset };
    }
    console.warn("[admin-ui] admin-service /admin/cases failed, falling back to graph-core");
  } catch (err) {
    console.warn("[admin-ui] admin-service unreachable, falling back to graph-core:", err);
  }

  // Fallback to graph-core (legacy)
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases?${params}`, {
    headers: authHeaders(),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to fetch cases: ${resp.status}`);
  return resp.json();
}

export async function fetchStats(): Promise<StatsResponse> {
  // Try admin-service dashboard summary
  try {
    const resp = await fetch(`${ADMIN_SERVICE_URL}/dashboard/summary`, {
      headers: authHeaders(),
    });
    if (resp.ok) {
      const data = await resp.json();
      return {
        total_cases: data.active_cases || 0,
        by_status: data.by_status || {},
        by_urgency: data.by_urgency || {},
        with_location: data.with_location || 0,
      };
    }
    console.warn("[admin-ui] admin-service /dashboard/summary failed, falling back to graph-core");
  } catch (err) {
    console.warn("[admin-ui] admin-service unreachable for stats:", err);
  }

  // Fallback to graph-core
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/stats`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error(`Failed to fetch stats: ${resp.status}`);
  return resp.json();
}

export async function updateCaseStatus(
  caseId: string,
  status: string,
): Promise<{ case_id: string; old_status: string; new_status: string; updated: boolean }> {
  // Use admin-service
  const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases/${caseId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ status, note: `Status changed to ${status}` }),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to update status: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Case Detail & Timeline — via admin-service
// ---------------------------------------------------------------------------

export async function fetchCaseDetail(caseId: string): Promise<Record<string, unknown>> {
  const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases/${caseId}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error(`Failed to fetch case detail: ${resp.status}`);
  return resp.json();
}

export type TimelineEntry = {
  id: string;
  case_id: string;
  event_type: string;
  description: string;
  actor: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export async function fetchCaseTimeline(caseId: string): Promise<TimelineEntry[]> {
  const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases/${caseId}/timeline`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error(`Failed to fetch timeline: ${resp.status}`);
  const data = await resp.json();
  return data.timeline || [];
}

// ---------------------------------------------------------------------------
// Resources — via graph-core (TODO: migrate to admin-service when available)
// ---------------------------------------------------------------------------

export async function fetchNearbyResources(
  lat: number,
  lon: number,
  radiusKm = 15,
): Promise<NearbyResourcesResponse> {
  // TODO: Move to admin-service when resource proxy is implemented
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
  });
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/resources/nearby?${params}`, {
    headers: authHeaders(),
  });
  if (!resp.ok) throw new Error(`Failed to fetch resources: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Caseworkers — via graph-core (TODO: migrate to participant-service via admin-service)
// ---------------------------------------------------------------------------

export async function fetchCaseWorkers(): Promise<CaseWorker[]> {
  // TODO: Replace with admin-service /dashboard/participants when participant-service
  // participants are used as caseworkers. Currently graph-core has seed caseworkers
  // that may not exist in participant-service. Assignments may fail if the caseworker
  // ID from graph-core is not a valid participant-service participant.
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/caseworkers`, {
    headers: authHeaders(),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to fetch caseworkers: ${resp.status}`);
  const data = await resp.json();
  return data.caseworkers;
}

export async function assignCase(
  caseId: string,
  caseworkerId: string,
): Promise<{ case_id: string; assigned_to: string | null; assigned_to_name: string | null; assigned_at: string | null }> {
  // Use admin-service assignment (with safety checks)
  try {
    const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases/${caseId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        participant_id: caseworkerId,
        assignment_type: "driver",
        notify_participant: false,
      }),
    });
    if (resp.ok) {
      const data = await resp.json();
      return {
        case_id: data.case_id,
        assigned_to: data.participant_id,
        assigned_to_name: null,
        assigned_at: null,
      };
    }
    console.warn("[admin-ui] admin-service assign failed, falling back to graph-core");
  } catch (err) {
    console.warn("[admin-ui] admin-service unreachable for assign:", err);
  }

  // Fallback to graph-core
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases/${caseId}/assign`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ assigned_to: caseworkerId }),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to assign case: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Notes — via graph-core (TODO: add notes proxy to admin-service)
// ---------------------------------------------------------------------------

export async function fetchCaseNotes(caseId: string): Promise<CaseNote[]> {
  // TODO: Migrate to admin-service when notes proxy is implemented
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases/${caseId}/notes`, {
    headers: authHeaders(),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to fetch notes: ${resp.status}`);
  const data = await resp.json();
  return data.notes;
}

export async function addCaseNote(
  caseId: string,
  text: string,
  author: string,
): Promise<CaseNote> {
  // TODO: Migrate to admin-service when notes proxy is implemented
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases/${caseId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text, author }),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to add note: ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// SSE — via graph-core (TODO: add SSE to admin-service)
// ---------------------------------------------------------------------------

export function subscribeToCaseStream(
  onUpdate: (cases: CaseRecord[], total: number) => void,
  onError?: (err: Event) => void,
): () => void {
  // TODO: Migrate to admin-service SSE when implemented
  const url = `${GRAPH_CORE_URL}/admin/cases/stream`;
  const source = new EventSource(url);

  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onUpdate(data.cases ?? [], data.total ?? 0);
    } catch {
      // ignore malformed events
    }
  };

  source.onerror = (err) => {
    onError?.(err);
  };

  return () => source.close();
}

// ---------------------------------------------------------------------------
// Auth error
// ---------------------------------------------------------------------------

export class AuthError extends Error {
  status: number;
  constructor(status: number) {
    super(status === 401 ? "Authentication required" : "Access denied");
    this.status = status;
  }
}
