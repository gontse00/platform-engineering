import type { SessionState } from '../types'
import { toTitle } from '../utils'

type StatusPanelProps = {
  sessionState: SessionState | null
  pendingMissingFields: string[]
}

function renderValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Not yet provided'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function StatusPanel({ sessionState, pendingMissingFields }: StatusPanelProps) {
  const state = sessionState?.state || {}
  const importantKeys = ['location', 'primary_need', 'safe_contact_method', 'immediate_danger', 'injury_status', 'incident_summary']

  return (
    <aside className="status-panel">
      <div className="panel-card">
        <h2>Support status</h2>
        <dl className="detail-list">
          <div>
            <dt>Stage</dt>
            <dd>{sessionState ? toTitle(sessionState.stage) : 'No active session'}</dd>
          </div>
          <div>
            <dt>Urgency</dt>
            <dd>{sessionState?.latest_urgency ? toTitle(sessionState.latest_urgency) : 'Assessing'}</dd>
          </div>
          <div>
            <dt>Queue</dt>
            <dd>{sessionState?.latest_queue ? toTitle(sessionState.latest_queue) : 'Not assigned yet'}</dd>
          </div>
          <div>
            <dt>Case</dt>
            <dd>{sessionState?.provisional_case_id || 'Not created yet'}</dd>
          </div>
        </dl>
      </div>

      <div className="panel-card">
        <h2>Collected details</h2>
        <dl className="detail-list compact">
          {importantKeys.map((key) => (
            <div key={key}>
              <dt>{toTitle(key)}</dt>
              <dd>{renderValue(state[key])}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="panel-card">
        <h2>Still needed</h2>
        {pendingMissingFields.length === 0 ? (
          <p className="muted">You have enough information to submit, or the case was submitted already.</p>
        ) : (
          <ul className="missing-list">
            {pendingMissingFields.map((field) => (
              <li key={field}>{toTitle(field)}</li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}
