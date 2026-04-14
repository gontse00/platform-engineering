import type { CaseRecord } from "../types";

type Props = {
  cases: CaseRecord[];
  selectedId: string | null;
  onSelect: (c: CaseRecord) => void;
};

const URGENCY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  urgent: "#ea580c",
  normal: "#2563eb",
  low: "#6b7280",
};

const STATUS_LABELS: Record<string, string> = {
  new: "New",
  in_progress: "In Progress",
  escalated: "Escalated",
  resolved: "Resolved",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function CaseList({ cases, selectedId, onSelect }: Props) {
  if (cases.length === 0) {
    return (
      <div className="case-list-empty">
        <p>No cases match the current filters.</p>
      </div>
    );
  }

  return (
    <ul className="case-list">
      {cases.map((c) => (
        <li
          key={c.case_id}
          className={`case-item ${selectedId === c.case_id ? "selected" : ""}`}
          onClick={() => onSelect(c)}
        >
          <div className="case-item-header">
            <span
              className="urgency-badge"
              style={{ backgroundColor: URGENCY_COLORS[c.urgency] ?? "#6b7280" }}
            >
              {c.urgency.toUpperCase()}
            </span>
            <span className="case-status">{STATUS_LABELS[c.status] ?? c.status}</span>
            {c.assigned_to_name ? (
              <span className="caseworker-badge" title={c.assigned_to_name}>
                {c.assigned_to_name
                  .split(" ")
                  .map((p) => p[0])
                  .join("")}
              </span>
            ) : (
              <span className="caseworker-badge unassigned">--</span>
            )}
            <span className="case-time">{timeAgo(c.created_at)}</span>
          </div>

          <p className="case-summary">{c.incident_summary_short || "No summary"}</p>

          <div className="case-item-footer">
            {c.normalized_location && (
              <span className="case-location-tag">{c.normalized_location}</span>
            )}
            {c.location ? (
              <span className="location-indicator has-location" title="GPS location available">
                GPS
              </span>
            ) : (
              <span className="location-indicator no-location" title="No GPS location">
                No GPS
              </span>
            )}
            {c.requires_human_review && (
              <span className="review-badge" title="Requires human review">
                Review
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
