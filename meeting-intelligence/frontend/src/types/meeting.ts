/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * This is the shared contract between frontend and backend.
 */

export interface Topic {
  title: string
  summary: string
}

export interface Decision {
  decision: string
  reason: string
  source_reference: string
}

export interface ActionItem {
  task: string
  owner: string
  deadline: string
  source_reference: string
}

export interface OpenQuestion {
  question: string
  context: string
}

export interface MeetingInsights {
  meeting_id: string
  summary: string
  topics: Topic[]
  decisions: Decision[]
  action_items: ActionItem[]
  open_questions: OpenQuestion[]
}

export interface MeetingTranscriptInput {
  meeting_id: string
  transcript: string
}
