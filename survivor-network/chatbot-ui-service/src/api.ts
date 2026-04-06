import { API_BASE_URL } from './config'
import type {
  AttachmentResponse,
  SessionState,
  SessionTurnResponse,
  StartSessionResponse,
  SubmitSessionResponse,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
  })

  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const body = await response.json()
      detail = body.detail || body.message || detail
    } catch {
      // ignore non-json responses
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export async function startSession(initialMessage?: string): Promise<StartSessionResponse | SessionTurnResponse> {
  return request('/sessions/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_message: initialMessage || null }),
  })
}

export async function sendMessage(sessionId: string, message: string, clientMessageId: string): Promise<SessionTurnResponse> {
  return request(`/sessions/${sessionId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, client_message_id: clientMessageId }),
  })
}

export async function getSession(sessionId: string): Promise<SessionState> {
  return request(`/sessions/${sessionId}`)
}

export async function submitSession(sessionId: string): Promise<SubmitSessionResponse> {
  return request(`/sessions/${sessionId}/submit`, {
    method: 'POST',
  })
}

export async function uploadAttachment(sessionId: string, file: File): Promise<AttachmentResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return request(`/sessions/${sessionId}/attachments`, {
    method: 'POST',
    body: formData,
  })
}
