/**
 * API service for the Meeting Intelligence backend.
 *
 * All backend communication goes through this single file.
 * The Vite dev server proxies /api to localhost:8000.
 */

import axios from 'axios'
import type { MeetingInsights, MeetingTranscriptInput } from '@/types/meeting'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  // The pipeline can take a while on a local model — give it room
  timeout: 180000, // 3 minutes
})

/**
 * Send a meeting transcript for analysis.
 * Returns structured meeting insights.
 */
export async function analyzeMeeting(
  input: MeetingTranscriptInput
): Promise<MeetingInsights> {
  const response = await client.post<MeetingInsights>('/analyze', input)
  return response.data
}

/**
 * Load the bundled sample transcript from the backend.
 */
export async function fetchSampleTranscript(): Promise<string> {
  const response = await client.get<{ transcript: string }>(
    '/sample-transcript'
  )
  return response.data.transcript
}

/**
 * Check whether the LLM provider is connected and responding.
 */
export interface LlmStatus {
  status: string
  provider: string
  sample_response: string
}

export async function checkLlmStatus(): Promise<LlmStatus> {
  const response = await client.get<LlmStatus>('/health/llm')
  return response.data
}

/**
 * Transcription result — mirrors the backend TranscriptionResult schema.
 */
export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface TranscriptionResult {
  meeting_id: string
  transcript: string
  language: string
  duration: number
  segments: TranscriptSegment[]
}

/**
 * Send recorded/uploaded audio to the backend for transcription.
 * Uses multipart/form-data (not JSON), so we build a FormData body.
 */
export async function transcribeAudio(
  audioBlob: Blob,
  meetingId: string,
  filename = 'recording.webm'
): Promise<TranscriptionResult> {
  const form = new FormData()
  form.append('file', audioBlob, filename)
  form.append('meeting_id', meetingId)

  const response = await client.post<TranscriptionResult>(
    '/transcribe',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return response.data
}
