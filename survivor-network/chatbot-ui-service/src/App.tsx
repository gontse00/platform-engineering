import { useEffect, useMemo, useState } from 'react'
import QuickActions from './components/QuickActions'
import { API_BASE_URL, STORAGE_KEY } from './config'
import {
  getInputPlaceholder,
  getQuickActionHint,
  getQuickActionsForField,
} from './quickActions'
import { generateId, toTitle } from './utils'
import './styles.css'

type Role = 'user' | 'assistant'

type ChatMessage = {
  id: string
  role: Role
  content: string
}

type SessionState = {
  location?: string | null
  primary_need?: string | null
  safe_contact_method?: string | null
  immediate_danger?: boolean | null
  injury_status?: string | null
  incident_summary?: string | null
  latest_graph_assessment?: {
    triage?: {
      urgency?: string
    }
    escalation?: {
      queue?: string
      escalate?: boolean
    }
  }
}

type SessionResponse = {
  session_id: string
  status: string
  stage: string
  bot_message?: string
  message?: string
  needs_more_info?: boolean
  missing_fields?: string[]
  escalation?: {
    queue?: string
    escalate?: boolean
  } | null
  provisional_case?: {
    id?: string
  } | null
  provisional_case_id?: string | null
  state?: SessionState
  latest_assessment?: {
    triage?: {
      urgency?: string
    }
    escalation?: {
      queue?: string
      escalate?: boolean
    }
  } | null
}

type PersistedState = {
  sessionId: string | null
  messages: ChatMessage[]
}

const defaultMessages: ChatMessage[] = [
  {
    id: generateId('msg'),
    role: 'assistant',
    content:
      'You can describe what happened in your own words. This chat helps collect information and route support.',
  },
]

function loadPersisted(): PersistedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { sessionId: null, messages: defaultMessages }

    const parsed = JSON.parse(raw) as PersistedState
    return {
      sessionId: parsed.sessionId ?? null,
      messages: parsed.messages?.length ? parsed.messages : defaultMessages,
    }
  } catch (err) {
    console.error('Failed to load persisted UI state', err)
    return { sessionId: null, messages: defaultMessages }
  }
}

function humanStage(stage?: string | null): string {
  switch (stage) {
    case 'collecting_followup_after_escalation':
      return 'We need a few more details'
    case 'collecting_required_fields':
      return 'We are collecting required details'
    case 'ready_for_submission':
      return 'Ready to submit'
    case 'submitted':
      return 'Case submitted'
    default:
      return 'No active session'
  }
}

function humanUrgency(state?: SessionState | null): string {
  return state?.latest_graph_assessment?.triage?.urgency
    ? toTitle(state.latest_graph_assessment.triage.urgency)
    : 'Assessing'
}

function humanQueue(state?: SessionState | null): string {
  return state?.latest_graph_assessment?.escalation?.queue
    ? toTitle(state.latest_graph_assessment.escalation.queue)
    : 'Not assigned yet'
}

export default function App() {
  const persisted = loadPersisted()

  const [sessionId, setSessionId] = useState<string | null>(persisted.sessionId)
  const [messages, setMessages] = useState<ChatMessage[]>(persisted.messages)
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sessionData, setSessionData] = useState<SessionResponse | null>(null)

  function appendAssistantMessage(content: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: generateId('msg'),
        role: 'assistant',
        content,
      },
    ])
  }

  function appendUserMessage(content: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: generateId('msg'),
        role: 'user',
        content,
      },
    ])
  }

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId, messages }))
    } catch (err) {
      console.error('Failed to persist UI state', err)
    }
  }, [sessionId, messages])

  useEffect(() => {
    if (!sessionId) return
    void fetchSession(sessionId)
  }, [sessionId])

  async function fetchSession(id: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/${id}`)
      if (!response.ok) {
        throw new Error(`Failed to load session: ${response.status}`)
      }

      const data = (await response.json()) as SessionResponse
      setSessionData(data)
    } catch (err) {
      console.error(err)
    }
  }

  async function startSession(initialMessage?: string) {
    const response = await fetch(`${API_BASE_URL}/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        initial_message: initialMessage || null,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to start session')
    }

    return (await response.json()) as SessionResponse
  }

  async function postMessage(id: string, content: string) {
    const response = await fetch(`${API_BASE_URL}/sessions/${id}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: content,
        client_message_id: generateId('client'),
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to send message')
    }

    return (await response.json()) as SessionResponse
  }

  async function submitCase(id: string) {
    const response = await fetch(`${API_BASE_URL}/sessions/${id}/submit`, {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error('Failed to submit case')
    }

    return (await response.json()) as SessionResponse
  }

  async function handleSendMessage(contentOverride?: string) {
    const content = (contentOverride ?? input).trim()
    if (!content || isSending || sessionData?.status === 'submitted') return

    setError(null)
    setIsSending(true)

    try {
      let activeSessionId = sessionId

      if (!activeSessionId) {
        const startData = await startSession()
        activeSessionId = startData.session_id
        setSessionId(activeSessionId)
        setSessionData(startData)

        const welcome = startData.message ?? startData.bot_message
        if (typeof welcome === 'string' && welcome.trim()) {
          appendAssistantMessage(welcome)
        }
      }

      appendUserMessage(content)

      const data = await postMessage(activeSessionId, content)
      setSessionData(data)

      if (typeof data.bot_message === 'string' && data.bot_message.trim()) {
        appendAssistantMessage(data.bot_message)
      }

      setInput('')
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to fetch')
    } finally {
      setIsSending(false)
    }
  }

  async function handleQuickAction(value: string) {
    if (!value || isSending || sessionData?.status === 'submitted') return
    await handleSendMessage(value)
  }

  async function handleSubmitCase() {
    if (!sessionId || isSubmitting || sessionData?.status === 'submitted') return

    setError(null)
    setIsSubmitting(true)

    try {
      const data = await submitCase(sessionId)
      setSessionData(data)

      if (typeof data.message === 'string' && data.message.trim()) {
        appendAssistantMessage(data.message)
      }
    } catch (err) {
      console.error(err)
      setError(err instanceof Error ? err.message : 'Failed to submit case')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleStartNewSession() {
    setSessionId(null)
    setSessionData(null)
    setMessages(defaultMessages)
    setInput('')
    setError(null)

    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (err) {
      console.error('Failed to clear persisted UI state', err)
    }
  }

  const missingFields = sessionData?.missing_fields ?? []
  const activeMissingField = missingFields.length > 0 ? missingFields[0] : null
  const isSubmitted = sessionData?.status === 'submitted'

  const quickActions = useMemo(
    () => getQuickActionsForField(activeMissingField),
    [activeMissingField],
  )

  const quickActionHint = useMemo(
    () => getQuickActionHint(activeMissingField),
    [activeMissingField],
  )

  const inputPlaceholder = useMemo(
    () => getInputPlaceholder(activeMissingField),
    [activeMissingField],
  )

  const state = sessionData?.state ?? null
  const stage = humanStage(sessionData?.stage)
  const urgency = humanUrgency(state)
  const queue = humanQueue(state)
  const caseId =
    sessionData?.provisional_case?.id ||
    sessionData?.provisional_case_id ||
    'Not created yet'

  const showUrgentBanner =
    urgency.toLowerCase() === 'urgent' || urgency.toLowerCase() === 'critical'

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">SURVIVOR NETWORK</div>
          <h1>Support intake guide</h1>
        </div>

        <button type="button" className="secondary-button" onClick={handleStartNewSession}>
          Start new session
        </button>
      </header>

      {showUrgentBanner && (
        <div className="alert-banner urgent">
          <strong>Urgent support:</strong> Support routing is continuing. Answer the next question so the case can move forward.
        </div>
      )}

      {isSubmitted && (
        <div className="current-step-banner">
          <strong>Case submitted:</strong> Your case has been sent. We will continue using the information you provided.
        </div>
      )}

      {!showUrgentBanner && !isSubmitted && (
        <div className="current-step-banner">
          <strong>Current step:</strong>{' '}
          {activeMissingField
            ? quickActionHint
            : 'Start with what happened, where you are, and whether you are safe right now.'}
        </div>
      )}

      <main className="layout">
        <section className="conversation-panel">
          <div className="panel-header">
            <div>
              <h2>Conversation</h2>
              <div className="muted">
                {sessionId ? 'Your support session is active' : 'Session not started yet'}
              </div>
            </div>

            <div className="header-actions">
              <button type="button" className="secondary-button" disabled={isSending || isSubmitting || isSubmitted}>
                Upload attachment
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={handleSubmitCase}
                disabled={!sessionId || isSending || isSubmitting || isSubmitted}
              >
                {isSubmitted ? 'Submitted' : isSubmitting ? 'Submitting...' : 'Submit case'}
              </button>
            </div>
          </div>

          <div className="messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message-row ${message.role === 'user' ? 'user' : 'assistant'}`}
              >
                <div className={`message-bubble ${message.role}`}>
                  <div className="message-role">
                    {message.role === 'user' ? 'You' : 'Support guide'}
                  </div>
                  <div>{message.content}</div>
                </div>
              </div>
            ))}
          </div>

          {!isSubmitted && (
            <>
              <div className="quick-action-hint">{quickActionHint}</div>

              <QuickActions
                actions={quickActions}
                disabled={isSending || isSubmitting}
                onSelect={handleQuickAction}
              />

              <div className="composer">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={inputPlaceholder}
                  disabled={isSending || isSubmitting}
                  rows={5}
                />

                <div className="composer-footer">
                  <div className="muted">
                    Tip: mention your location, whether you are safe, and whether you are injured.
                  </div>

                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => void handleSendMessage()}
                    disabled={isSending || isSubmitting || !input.trim()}
                  >
                    {isSending ? 'Sending...' : 'Send message'}
                  </button>
                </div>
              </div>
            </>
          )}

          {error && <div className="error-banner">{error}</div>}
        </section>

        <aside className="sidebar">
          <section className="sidebar-card">
            <h2>Support status</h2>

            <div className="field-label">Stage</div>
            <div className="field-value">{stage}</div>

            <div className="field-label">Urgency</div>
            <div className="field-value">{urgency}</div>

            <div className="field-label">Queue</div>
            <div className="field-value">{queue}</div>

            <div className="field-label">Case</div>
            <div className="field-value">{caseId}</div>
          </section>

          <section className="sidebar-card">
            <h2>Collected details</h2>

            <div className="field-label">Location</div>
            <div className="field-value">{state?.location || 'Not yet provided'}</div>

            <div className="field-label">Primary Need</div>
            <div className="field-value">{state?.primary_need || 'Not yet provided'}</div>

            <div className="field-label">Safe Contact Method</div>
            <div className="field-value">{state?.safe_contact_method || 'Not yet provided'}</div>

            <div className="field-label">Immediate Danger</div>
            <div className="field-value">
              {state?.immediate_danger === true
                ? 'Yes'
                : state?.immediate_danger === false
                ? 'No'
                : 'Not yet provided'}
            </div>

            <div className="field-label">Injury Status</div>
            <div className="field-value">{state?.injury_status || 'Not yet provided'}</div>

            <div className="field-label">Incident Summary</div>
            <div className="field-value">{state?.incident_summary || 'Not yet provided'}</div>
          </section>

          <section className="sidebar-card">
            <h2>Still needed</h2>
            {missingFields.length ? (
              <ul className="missing-fields">
                {missingFields.map((field) => (
                  <li key={field}>{toTitle(field)}</li>
                ))}
              </ul>
            ) : (
              <div className="field-value">No required details are missing right now.</div>
            )}
          </section>
        </aside>
      </main>
    </div>
  )
}