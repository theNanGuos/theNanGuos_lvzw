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
  updated_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  active_project_id?: string
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
  return response.json() as Promise<T>
}

export function createProject(payload: {
  title: string
  user_request: string
  preset: Preset
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

export function sendChatMessage(sessionId: string, content: string) {
  return request<ChatResponse>(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}

export function mediaUrl(path: string) {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}
