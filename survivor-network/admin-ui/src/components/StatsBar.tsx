import { useEffect, useState } from "react";
import { fetchStats } from "../api";
import type { StatsResponse } from "../types";

const URGENCY_ORDER = ["critical", "high", "urgent", "standard", "low"];
const URGENCY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  urgent: "#f59e0b",
  standard: "#2563eb",
  low: "#6b7280",
};

type Props = {
  refreshKey: number;
};

export default function StatsBar({ refreshKey }: Props) {
  const [stats, setStats] = useState<StatsResponse | null>(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => {});
  }, [refreshKey]);

  if (!stats) return null;

  const statusEntries = Object.entries(stats.by_status).sort(
    ([, a], [, b]) => b - a,
  );
  const urgencyEntries = Object.entries(stats.by_urgency).sort(
    (a, b) => URGENCY_ORDER.indexOf(a[0]) - URGENCY_ORDER.indexOf(b[0]),
  );

  const criticalCount = stats.by_urgency["critical"] ?? 0;
  const highCount = stats.by_urgency["high"] ?? 0;
  const activeAlerts = criticalCount + highCount;

  return (
    <div className="stats-bar">
      <div className="stat-card">
        <span className="stat-value">{stats.total_cases}</span>
        <span className="stat-label">Total Cases</span>
      </div>

      <div className={`stat-card ${activeAlerts > 0 ? "stat-alert" : ""}`}>
        <span className="stat-value">{activeAlerts}</span>
        <span className="stat-label">Critical + High</span>
      </div>

      <div className="stat-card">
        <span className="stat-value">{stats.with_location}</span>
        <span className="stat-label">With GPS</span>
      </div>

      <div className="stat-card stat-breakdown">
        <span className="stat-label">By Urgency</span>
        <div className="stat-pills">
          {urgencyEntries.map(([level, count]) => (
            <span
              key={level}
              className="stat-pill"
              style={{ backgroundColor: URGENCY_COLORS[level] ?? "#6b7280" }}
            >
              {count} {level}
            </span>
          ))}
        </div>
      </div>

      <div className="stat-card stat-breakdown">
        <span className="stat-label">By Status</span>
        <div className="stat-pills">
          {statusEntries.map(([status, count]) => (
            <span key={status} className="stat-pill stat-pill-status">
              {count} {status.replace("_", " ")}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}