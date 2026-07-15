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
}

export interface RunResult {
  id: string
  project_id: string
  state: Record<string, unknown>
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

export function mediaUrl(path: string) {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}
