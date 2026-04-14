import { GRAPH_CORE_URL } from "./config";
import type {
  CaseNote,
  CaseWorker,
  CasesResponse,
  CaseRecord,
  FilterState,
  NearbyResourcesResponse,
  StatsResponse,
} from "./types";

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

  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases?${params}`, {
    headers: authHeaders(),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to fetch cases: ${resp.status}`);
  return resp.json();
}

export async function fetchStats(): Promise<StatsResponse> {
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
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases/${caseId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ status }),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to update status: ${resp.status}`);
  return resp.json();
}

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

export async function fetchCaseWorkers(): Promise<CaseWorker[]> {
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
  const resp = await fetch(`${GRAPH_CORE_URL}/admin/cases/${caseId}/assign`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ assigned_to: caseworkerId }),
  });
  if (resp.status === 401 || resp.status === 403) throw new AuthError(resp.status);
  if (!resp.ok) throw new Error(`Failed to assign case: ${resp.status}`);
  return resp.json();
}

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

export class AuthError extends Error {
  status: number;
  constructor(status: number) {
    super(status === 401 ? "Authentication required" : "Access denied");
    this.status = status;
  }
}