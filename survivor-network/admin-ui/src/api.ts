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
    if (resp.ok) return resp.json();
  } catch {
    // fall through to graph-core
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
        total_cases: data.active_cases + (data.urgent_cases || 0),
        by_status: {},
        by_urgency: {},
        with_location: 0,
        ...data,
      };
    }
  } catch {
    // fall through
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
// Resources — still via graph-core (admin-service doesn't have this yet)
// ---------------------------------------------------------------------------

export async function fetchNearbyResources(
  lat: number,
  lon: number,
  radiusKm = 15,
): Promise<NearbyResourcesResponse> {
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
// Caseworkers / Participants — via graph-core (legacy) or admin-service
// ---------------------------------------------------------------------------

export async function fetchCaseWorkers(): Promise<CaseWorker[]> {
  // Try graph-core first (has seed caseworkers)
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
  // Try admin-service assignment (with safety checks)
  try {
    const resp = await fetch(`${ADMIN_SERVICE_URL}/admin/cases/${caseId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        participant_id: caseworkerId,
        assignment_type: "helper",
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
  } catch {
    // fall through to graph-core
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
// Case Notes — via graph-core (admin-service doesn't proxy notes yet)
// ---------------------------------------------------------------------------

export async function fetchCaseNotes(caseId: string): Promise<CaseNote[]> {
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
// SSE — via graph-core (admin-service doesn't have SSE yet)
// ---------------------------------------------------------------------------

export function subscribeToCaseStream(
  onUpdate: (cases: CaseRecord[], total: number) => void,
  onError?: (err: Event) => void,
): () => void {
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
