import { useEffect } from "react";
import type { CaseRecord } from "../types";

type Alert = {
  id: string;
  caseRecord: CaseRecord;
  timestamp: number;
};

type Props = {
  alerts: Alert[];
  onDismiss: (id: string) => void;
  onSelect: (c: CaseRecord) => void;
};

const AUTO_DISMISS_MS = 15_000;

const URGENCY_LABELS: Record<string, string> = {
  critical: "CRITICAL",
  urgent: "URGENT",
};

export type { Alert };

export default function AlertToast({ alerts, onDismiss, onSelect }: Props) {
  useEffect(() => {
    if (alerts.length === 0) return;
    const timers = alerts.map((a) =>
      setTimeout(() => onDismiss(a.id), AUTO_DISMISS_MS),
    );
    return () => timers.forEach(clearTimeout);
  }, [alerts, onDismiss]);

  if (alerts.length === 0) return null;

  return (
    <div className="alert-toast-container">
      {alerts.map((a) => (
        <div
          key={a.id}
          className={`alert-toast alert-toast-${a.caseRecord.urgency}`}
          onClick={() => {
            onSelect(a.caseRecord);
            onDismiss(a.id);
          }}
        >
          <div className="alert-toast-header">
            <span className="alert-toast-badge">
              {URGENCY_LABELS[a.caseRecord.urgency] ?? "ALERT"}
            </span>
            <span className="alert-toast-time">just now</span>
            <button
              className="alert-toast-close"
              onClick={(e) => {
                e.stopPropagation();
                onDismiss(a.id);
              }}
            >
              ×
            </button>
          </div>
          <p className="alert-toast-summary">
            {a.caseRecord.incident_summary_short || "New critical case"}
          </p>
          {a.caseRecord.normalized_location && (
            <span className="alert-toast-location">
              {a.caseRecord.normalized_location}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}