import { useEffect, useState } from "react";
import { fetchCaseNotes, addCaseNote } from "../api";
import type { CaseNote, CaseRecord, CaseStatus, CaseWorker } from "../types";

type Props = {
  caseRecord: CaseRecord | null;
  onStatusChange: (caseId: string, newStatus: string) => void;
  statusUpdating: boolean;
  caseworkers: CaseWorker[];
  onAssign: (caseId: string, caseworkerId: string) => void;
};

const STATUS_TRANSITIONS: Record<CaseStatus, CaseStatus[]> = {
  new: ["in_progress", "escalated"],
  in_progress: ["escalated", "resolved"],
  escalated: ["in_progress", "resolved"],
  resolved: ["in_progress"],
};

const STATUS_LABELS: Record<CaseStatus, string> = {
  new: "New",
  in_progress: "In Progress",
  escalated: "Escalated",
  resolved: "Resolved",
};

const STATUS_BUTTON_CLASS: Record<CaseStatus, string> = {
  new: "status-btn-new",
  in_progress: "status-btn-progress",
  escalated: "status-btn-escalated",
  resolved: "status-btn-resolved",
};

function formatDate(iso: string | null): string {
  if (!iso) return "N/A";
  return new Date(iso).toLocaleString("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function timeAgo(iso: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(iso).getTime()) / 1000,
  );
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function CaseDetail({
  caseRecord,
  onStatusChange,
  statusUpdating,
  caseworkers,
  onAssign,
}: Props) {
  const [notes, setNotes] = useState<CaseNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [noteAuthor, setNoteAuthor] = useState("Admin");
  const [noteSubmitting, setNoteSubmitting] = useState(false);

  useEffect(() => {
    if (!caseRecord) {
      setNotes([]);
      return;
    }
    let cancelled = false;
    setNotesLoading(true);
    fetchCaseNotes(caseRecord.case_id)
      .then((data) => {
        if (!cancelled) setNotes(data);
      })
      .catch(() => {
        if (!cancelled) setNotes([]);
      })
      .finally(() => {
        if (!cancelled) setNotesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseRecord?.case_id]);

  const handleAddNote = async () => {
    if (!caseRecord || !noteText.trim()) return;
    setNoteSubmitting(true);
    try {
      await addCaseNote(caseRecord.case_id, noteText.trim(), noteAuthor.trim() || "Admin");
      setNoteText("");
      const refreshed = await fetchCaseNotes(caseRecord.case_id);
      setNotes(refreshed);
    } catch {
      // silently fail
    } finally {
      setNoteSubmitting(false);
    }
  };

  if (!caseRecord) {
    return (
      <div className="case-detail empty">
        <p>Select a case to view details</p>
      </div>
    );
  }

  const c = caseRecord;
  const loc = c.location;
  const nextStatuses = STATUS_TRANSITIONS[c.status] ?? [];

  return (
    <div className="case-detail">
      <h3>Case Detail</h3>

      <div className="detail-row">
        <span className={`detail-urgency urgency-${c.urgency}`}>
          {c.urgency.toUpperCase()}
        </span>
        <span className="detail-status">{c.status.replace("_", " ")}</span>
        {c.safety_risk !== "unknown" && (
          <span className={`detail-safety safety-${c.safety_risk}`}>
            Safety: {c.safety_risk}
          </span>
        )}
      </div>

      {nextStatuses.length > 0 && (
        <div className="detail-section status-actions">
          <label>Change Status</label>
          <div className="status-btn-group">
            {nextStatuses.map((s) => (
              <button
                key={s}
                className={`status-btn ${STATUS_BUTTON_CLASS[s]}`}
                onClick={() => onStatusChange(c.case_id, s)}
                disabled={statusUpdating}
              >
                {statusUpdating ? "..." : STATUS_LABELS[s]}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="detail-section assignment-section">
        <label>Assigned To</label>
        <select
          className="assign-dropdown"
          value={c.assigned_to ?? ""}
          onChange={(e) => onAssign(c.case_id, e.target.value)}
        >
          <option value="">Unassigned</option>
          {caseworkers.map((cw) => (
            <option key={cw.id} value={cw.id}>
              {cw.name}
            </option>
          ))}
        </select>
      </div>

      <div className="detail-section">
        <label>Incident Summary</label>
        <p className="detail-summary">
          {c.incident_summary || "No summary available"}
        </p>
      </div>

      {c.primary_needs.length > 0 && (
        <div className="detail-section">
          <label>Primary Needs</label>
          <div className="tag-list">
            {c.primary_needs.map((n) => (
              <span key={n} className="tag need-tag">{n}</span>
            ))}
          </div>
        </div>
      )}

      {c.incident_types.length > 0 && (
        <div className="detail-section">
          <label>Incident Types</label>
          <div className="tag-list">
            {c.incident_types.map((t) => (
              <span key={t} className="tag incident-tag">{t}</span>
            ))}
          </div>
        </div>
      )}

      <div className="detail-section">
        <label>Location</label>
        {c.normalized_location && (
          <p className="detail-location-name">{c.normalized_location}</p>
        )}
        {loc && loc.consent_to_share ? (
          <div className="detail-location-data">
            <p>
              {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
              {loc.is_approximate && (
                <span className="approx-badge">Approx</span>
              )}
            </p>
            <p className="detail-meta">
              Source: {loc.location_source}
              {loc.accuracy_meters != null &&
                ` | Accuracy: ${Math.round(loc.accuracy_meters)}m`}
            </p>
          </div>
        ) : loc ? (
          <p className="detail-meta">Location withheld (no consent)</p>
        ) : (
          <p className="detail-meta">No location data</p>
        )}
      </div>

      {(c.queue || c.escalation_recommended) && (
        <div className="detail-section">
          <label>Routing</label>
          {c.queue && (
            <p>
              Queue: <strong>{c.queue}</strong>
            </p>
          )}
          {c.escalation_recommended && (
            <p className="escalation-flag">Escalation recommended</p>
          )}
          {c.requires_human_review && (
            <p className="review-flag">Requires human review</p>
          )}
        </div>
      )}

      <div className="detail-section">
        <label>Timeline</label>
        <p className="detail-meta">Created: {formatDate(c.created_at)}</p>
      </div>

      <div className="detail-section">
        <label>Case ID</label>
        <p className="detail-meta case-id-text">{c.case_id}</p>
      </div>

      <div className="detail-section notes-section">
        <label>
          Notes{" "}
          <span className="note-count-badge">
            {notesLoading ? "..." : notes.length}
          </span>
        </label>

        <div className="notes-list">
          {notesLoading && <p className="detail-meta">Loading notes...</p>}
          {!notesLoading && notes.length === 0 && (
            <p className="detail-meta">No notes yet</p>
          )}
          {notes.map((note) => (
            <div key={note.id} className="note-item">
              <div className="note-item-header">
                <span className="note-author">{note.author}</span>
                <span className="note-time">{timeAgo(note.created_at)}</span>
              </div>
              <p className="note-text">{note.text}</p>
            </div>
          ))}
        </div>

        <div className="note-form">
          <input
            type="text"
            className="note-author-input"
            placeholder="Author"
            value={noteAuthor}
            onChange={(e) => setNoteAuthor(e.target.value)}
          />
          <textarea
            className="note-textarea"
            placeholder="Add a note..."
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            rows={3}
          />
          <button
            className="note-submit-btn"
            onClick={handleAddNote}
            disabled={noteSubmitting || !noteText.trim()}
          >
            {noteSubmitting ? "Adding..." : "Add Note"}
          </button>
        </div>
      </div>
    </div>
  );
}