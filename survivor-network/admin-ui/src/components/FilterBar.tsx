import type { FilterState, CaseStatus, CaseWorker } from "../types";

type Props = {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  totalCases: number;
  showResources: boolean;
  onToggleResources: () => void;
  caseworkers: CaseWorker[];
};

const STATUS_OPTIONS: { value: CaseStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "new", label: "New" },
  { value: "triaging", label: "Triaging" },
  { value: "assigned", label: "Assigned" },
  { value: "in_progress", label: "In Progress" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

export default function FilterBar({
  filters,
  onChange,
  totalCases,
  showResources,
  onToggleResources,
  caseworkers,
}: Props) {
  return (
    <div className="filter-bar">
      <div className="filter-tabs">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={`filter-tab ${filters.status === opt.value ? "active" : ""}`}
            onClick={() => onChange({ ...filters, status: opt.value })}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="filter-toggles">
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filters.hasLocation}
            onChange={(e) =>
              onChange({ ...filters, hasLocation: e.target.checked })
            }
          />
          With location only
        </label>

        <label className="filter-checkbox resource-toggle">
          <input
            type="checkbox"
            checked={showResources}
            onChange={onToggleResources}
          />
          Show resources
        </label>

        <select
          className="filter-caseworker-dropdown"
          value={filters.assignedTo ?? ""}
          onChange={(e) =>
            onChange({ ...filters, assignedTo: e.target.value || undefined })
          }
        >
          <option value="">All Caseworkers</option>
          <option value="unassigned">Unassigned</option>
          {caseworkers.map((cw) => (
            <option key={cw.id} value={cw.id}>
              {cw.name}
            </option>
          ))}
        </select>
      </div>

      <span className="filter-count">
        {totalCases} case{totalCases !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
