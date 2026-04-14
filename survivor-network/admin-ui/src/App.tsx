import { useState, useEffect, useCallback, useRef } from "react";
import FilterBar from "./components/FilterBar";
import CaseList from "./components/CaseList";
import CaseDetail from "./components/CaseDetail";
import CaseMap from "./components/CaseMap";
import StatsBar from "./components/StatsBar";
import AlertToast from "./components/AlertToast";
import type { Alert } from "./components/AlertToast";
import { useAlertSound } from "./hooks/useAlertSound";
import {
  fetchCases,
  fetchCaseWorkers,
  assignCase,
  fetchNearbyResources,
  subscribeToCaseStream,
  updateCaseStatus,
  AuthError,
  setAuthToken,
  getAuthToken,
} from "./api";
import { POLL_INTERVAL_MS } from "./config";
import type {
  CaseRecord,
  CaseWorker,
  FilterState,
  ResourceMarker,
  ResourceTypeFilter,
} from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";

export default function App() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [filters, setFilters] = useState<FilterState>({
    status: "all",
    hasLocation: false,
  });

  const [caseworkers, setCaseworkers] = useState<CaseWorker[]>([]);
  const [resources, setResources] = useState<ResourceMarker[]>([]);
  const [showResources, setShowResources] = useState(true);
  const [resourceTypeFilters, setResourceTypeFilters] = useState<
    Set<ResourceTypeFilter>
  >(new Set());


  const [sseConnected, setSseConnected] = useState(false);
  const sseCleanupRef = useRef<(() => void) | null>(null);

  const [needsAuth, setNeedsAuth] = useState(false);
  const [authInput, setAuthInput] = useState("");

  const [statusUpdating, setStatusUpdating] = useState(false);

  const [statsRefreshKey, setStatsRefreshKey] = useState(0);

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const knownCaseIdsRef = useRef<Set<string>>(new Set());
  const playAlert = useAlertSound();

  const loadCases = useCallback(async () => {
    try {
      if (loadState === "idle") setLoadState("loading");
      const data = await fetchCases(filters);
      setCases(data.cases);
      setTotalCases(data.total);
      setLoadState("ready");
      setErrorMsg("");
      setStatsRefreshKey((k) => k + 1);

      for (const c of data.cases) {
        knownCaseIdsRef.current.add(c.case_id);
      }

      if (selectedCase) {
        const updated = data.cases.find(
          (c) => c.case_id === selectedCase.case_id,
        );
        if (updated) setSelectedCase(updated);
      }
    } catch (err) {
      if (err instanceof AuthError) {
        setNeedsAuth(true);
        return;
      }
      setLoadState("error");
      setErrorMsg(err instanceof Error ? err.message : "Failed to load cases");
    }
  }, [filters, loadState, selectedCase]);

  useEffect(() => {
    loadCases();
  }, [filters]);

  useEffect(() => {
    fetchCaseWorkers()
      .then(setCaseworkers)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const cleanup = subscribeToCaseStream(
      (streamCases, total) => {
        setSseConnected(true);

        const newAlerts: Alert[] = [];
        for (const c of streamCases) {
          if (
            !knownCaseIdsRef.current.has(c.case_id) &&
            knownCaseIdsRef.current.size > 0 &&
            (c.urgency === "critical" || c.urgency === "urgent")
          ) {
            newAlerts.push({
              id: `alert-${c.case_id}-${Date.now()}`,
              caseRecord: c,
              timestamp: Date.now(),
            });
          }
          knownCaseIdsRef.current.add(c.case_id);
        }

        if (newAlerts.length > 0) {
          setAlerts((prev) => [...newAlerts.slice(0, 3), ...prev].slice(0, 5));
          const hasCritical = newAlerts.some((a) => a.caseRecord.urgency === "critical");
          playAlert(hasCritical ? "critical" : "high");
        }

        let filtered = streamCases;
        if (filters.status !== "all") {
          filtered = filtered.filter((c) => c.status === filters.status);
        }
        if (filters.hasLocation) {
          filtered = filtered.filter((c) => c.location !== null);
        }
        if (filters.assignedTo) {
          if (filters.assignedTo === "unassigned") {
            filtered = filtered.filter((c) => c.assigned_to === null);
          } else {
            filtered = filtered.filter(
              (c) => c.assigned_to === filters.assignedTo,
            );
          }
        }

        setCases(filtered);
        setTotalCases(
          filters.status === "all" && !filters.hasLocation && !filters.assignedTo
            ? total
            : filtered.length,
        );
        setLoadState("ready");

        if (selectedCase) {
          const updated = filtered.find(
            (c) => c.case_id === selectedCase.case_id,
          );
          if (updated) setSelectedCase(updated);
        }
      },
      () => {
        setSseConnected(false);
      },
    );

    sseCleanupRef.current = cleanup;
    return () => {
      cleanup();
      sseCleanupRef.current = null;
    };
  }, [filters]);


  useEffect(() => {
    if (sseConnected || POLL_INTERVAL_MS <= 0) return;
    const timer = setInterval(() => {
      fetchCases(filters)
        .then((data) => {
          setCases(data.cases);
          setTotalCases(data.total);
        })
        .catch(() => {});
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [filters, sseConnected]);

  useEffect(() => {
    if (!selectedCase?.location || !selectedCase.location.consent_to_share)
      return;

    const { latitude, longitude } = selectedCase.location;
    fetchNearbyResources(latitude, longitude)
      .then((data) => setResources(data.resources))
      .catch(() => setResources([]));
  }, [selectedCase?.case_id]);

  const handleStatusUpdate = useCallback(
    async (caseId: string, newStatus: string) => {
      setStatusUpdating(true);
      try {
        await updateCaseStatus(caseId, newStatus);
        const data = await fetchCases(filters);
        setCases(data.cases);
        setTotalCases(data.total);

        const updated = data.cases.find((c) => c.case_id === caseId);
        if (updated) setSelectedCase(updated);
      } catch (err) {
        if (err instanceof AuthError) {
          setNeedsAuth(true);
          return;
        }
        setErrorMsg(
          err instanceof Error ? err.message : "Failed to update status",
        );
      } finally {
        setStatusUpdating(false);
      }
    },
    [filters],
  );

  const handleAssign = useCallback(
    async (caseId: string, caseworkerId: string) => {
      try {
        await assignCase(caseId, caseworkerId);
        const data = await fetchCases(filters);
        setCases(data.cases);
        setTotalCases(data.total);

        const updated = data.cases.find((c) => c.case_id === caseId);
        if (updated) setSelectedCase(updated);
      } catch (err) {
        if (err instanceof AuthError) {
          setNeedsAuth(true);
          return;
        }
        setErrorMsg(
          err instanceof Error ? err.message : "Failed to assign case",
        );
      }
    },
    [filters],
  );

  const handleLogin = () => {
    if (authInput.trim()) {
      setAuthToken(authInput.trim());
      setNeedsAuth(false);
      setAuthInput("");
      loadCases();
    }
  };

  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const _toggleResourceType = useCallback((type: ResourceTypeFilter) => {
    setResourceTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);
  void _toggleResourceType;


  if (needsAuth) {
    return (
      <div className="dashboard">
        <header className="dashboard-header">
          <h1>Survivor Network</h1>
          <span className="header-subtitle">Admin Dashboard</span>
        </header>
        <div className="auth-overlay">
          <div className="auth-card">
            <h2>Authentication Required</h2>
            <p>Enter your admin token to access the dashboard.</p>
            <input
              type="password"
              className="auth-input"
              placeholder="Admin token"
              value={authInput}
              onChange={(e) => setAuthInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              autoFocus
            />
            <button className="auth-submit" onClick={handleLogin}>
              Sign In
            </button>
            {!getAuthToken() && (
              <p className="auth-hint">
                In dev mode (no ADMIN_JWT_SECRET set), auth is not required.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Survivor Network</h1>
        <span className="header-subtitle">Admin Dashboard</span>
        <div className="header-actions">
          {sseConnected && (
            <span className="sse-indicator" title="Real-time updates active">
              <span className="sse-dot" /> Live
            </span>
          )}
          <button
            className="refresh-btn"
            onClick={loadCases}
            disabled={loadState === "loading"}
          >
            {loadState === "loading" ? "Loading..." : "Refresh"}
          </button>
        </div>
      </header>

      <StatsBar refreshKey={statsRefreshKey} />

      {loadState === "error" && (
        <div className="error-banner">
          <span>{errorMsg}</span>
          <button onClick={loadCases}>Retry</button>
        </div>
      )}

      <div className="dashboard-body">
        <aside className="left-panel">
          <FilterBar
            filters={filters}
            onChange={setFilters}
            totalCases={totalCases}
            showResources={showResources}
            onToggleResources={() => setShowResources((v) => !v)}
            caseworkers={caseworkers}
          />

          {loadState === "loading" && cases.length === 0 ? (
            <div className="loading-state">
              <p>Loading cases...</p>
            </div>
          ) : (
            <CaseList
              cases={cases}
              selectedId={selectedCase?.case_id ?? null}
              onSelect={setSelectedCase}
            />
          )}

          <CaseDetail
            caseRecord={selectedCase}
            onStatusChange={handleStatusUpdate}
            statusUpdating={statusUpdating}
            caseworkers={caseworkers}
            onAssign={handleAssign}
          />
        </aside>

        <main className="right-panel">
          <CaseMap
            cases={cases}
            selectedCase={selectedCase}
            onSelectCase={setSelectedCase}
            resources={resources}
            showResources={showResources}
            resourceTypeFilters={resourceTypeFilters}
          />
        </main>
      </div>

      <AlertToast
        alerts={alerts}
        onDismiss={dismissAlert}
        onSelect={(c) => setSelectedCase(c)}
      />
    </div>
  );
}