export type Preset =
  | 'auto'
  | 'pop_vocal'
  | 'classical_instrumental'
  | 'electronic_instrumental'
  | 'soundtrack_score'

export interface Project {
  id: string
  title: string
  user_request: string
  preset: Preset
  genre: string
  language: string
  instruments: string[]
  status: 'draft' | 'running' | 'completed' | 'failed'
  progress: number
  current_stage: string
  latest_run_id?: string
  error?: string
}

export interface RunResult {
  id: string
  project_id: string
  state: Record<string, unknown>
  status: 'draft' | 'running' | 'completed' | 'failed'
  progress: number
  current_stage: string
  error?: string
}

export interface PortfolioItem {
  project_id: string
  title: string
  user_request: string
  preset: Preset
  status: Project['status']
  progress: number
  current_stage: string
  latest_run_id?: string
  tracks: PortfolioTrack[]
  updated_at: string
}

export interface PortfolioTrack {
  title: string
  audio_url: string
  download_url: string
  cover_url?: string | null
  duration_seconds?: number | null
  style: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  workflow_run?: ChatWorkflowRun | null
  audio_attachments?: ChatAudioAttachment[]
  created_at: string
}

export interface ChatAudioAttachment {
  id: string
  filename: string
  path: string
  content_type: string
  size: number
}

export interface ChatWorkflowRun {
  project_id: string
  run_id: string
  title: string
  preset: Preset
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  active_project_id?: string | null
  created_at: string
  updated_at: string
}

export interface ChatSessionSummary {
  id: string
  title: string
  active_project_id?: string | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface ChatResponse {
  session: ChatSession
  message: ChatMessage
  action: string
  project_id?: string
  run_id?: string
}

export interface GeneratedTrack {
  title: string
  source_url: string
  local_path: string
  audio_url: string
  download_url: string
  cover_url?: string | null
  style?: string
  duration_seconds?: number | null
}

export interface DemoAudio {
  output_path: string
  audio_url: string
  duration_seconds: number
  tempo_bpm: number
  frequencies: number[]
}

export interface GeneratedAudioAnalysis {
  track_title: string
  waveform_url?: string
  inspection: {
    duration_seconds?: number
    codec_name?: string
    sample_rate?: number
    channels?: number
    bit_rate?: number
    size_bytes?: number
  }
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `请求失败 (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function createProject(payload: {
  title: string
  user_request: string
  preset: Preset
  genre?: string
  language?: string
  instruments?: string[]
}) {
  return request<Project>('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function uploadAsset(projectId: string, file: File) {
  const body = new FormData()
  body.append('file', file)
  return request(`/api/projects/${projectId}/assets`, { method: 'POST', body })
}

export function runProject(projectId: string) {
  return request<RunResult>(`/api/projects/${projectId}/runs`, { method: 'POST' })
}

export function runProjectAsync(projectId: string) {
  return request<RunResult>(`/api/projects/${projectId}/runs/async`, { method: 'POST' })
}

export function getRun(projectId: string, runId: string) {
  return request<RunResult>(`/api/projects/${projectId}/runs/${runId}`)
}

export function listPortfolio() {
  return request<PortfolioItem[]>('/api/portfolio')
}

export function createSession(title = '新会话') {
  return request<ChatSession>('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export function listSessions() {
  return request<ChatSessionSummary[]>('/api/sessions')
}

export function getSession(sessionId: string) {
  return request<ChatSession>(`/api/sessions/${sessionId}`)
}

export function renameSession(sessionId: string, title: string) {
  return request<ChatSession>(`/api/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export function deleteSession(sessionId: string) {
  return request<void>(`/api/sessions/${sessionId}`, { method: 'DELETE' })
}

export function getProject(projectId: string) {
  return request<Project>(`/api/projects/${projectId}`)
}

export function uploadSessionAsset(sessionId: string, file: File) {
  const body = new FormData()
  body.append('file', file)
  return request<ChatAudioAttachment>(`/api/sessions/${sessionId}/assets`, { method: 'POST', body })
}

export function sendChatMessage(sessionId: string, content: string, assetIds: string[] = []) {
  return request<ChatResponse>(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, asset_ids: assetIds }),
  })
}

export function mediaUrl(path: string) {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}
