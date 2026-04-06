export type SessionState = {
  session_id: string
  status: string
  stage: string
  escalated: boolean
  provisional_case_id?: string | null
  latest_urgency?: string | null
  latest_queue?: string | null
  state: Record<string, unknown>
  message_count: number
  attachment_count: number
}

export type SessionTurnResponse = {
  session_id: string
  status: string
  stage: string
  bot_message: string
  needs_more_info: boolean
  missing_fields: string[]
  escalation?: Record<string, unknown> | null
  provisional_case?: Record<string, unknown> | null
  latest_assessment?: Record<string, unknown> | null
}

export type StartSessionResponse = {
  session_id: string
  status: string
  stage: string
  bot_message: string
  next_expected_fields: string[]
}

export type SubmitSessionResponse = {
  session_id: string
  status: string
  stage: string
  provisional_case_id?: string | null
  submitted: boolean
  missing_fields: string[]
  state: Record<string, unknown>
  message?: string | null
}

export type AttachmentResponse = {
  attachment_id: string
  attachment_type: string
  filename?: string | null
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}
