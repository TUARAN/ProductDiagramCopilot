export type DiagramType = 'flow' | 'sequence' | 'state' | 'cmic_report'

export interface DiagramGenerateRequest {
  diagram_type: DiagramType
  text: string
  scene?: string
}

export interface DiagramGenerateResponse {
  spec: unknown
  mermaid: string
}

export interface IntegrationGenerateRequest {
  text: string
  swagger_text?: string
}

export interface IntegrationGenerateResponse {
  markdown: string
  spec?: unknown
}

export interface SettlementMetricsRequest {
  month: string
  rows: Array<Record<string, unknown>>
}

export interface SettlementMetricsResponse {
  month: string
  metrics: Record<string, number>
}

export interface TaskSubmitResponse {
  task_id: string
}

export interface TaskStatusResponse {
  task_id: string
  state: string
  result?: Record<string, unknown> | null
}

export interface ArtifactOut {
  id: string
  kind: string
  status: string
  request: Record<string, unknown>
  spec?: unknown | null
  mermaid?: string | null
  markdown?: string | null
  object_key?: string | null
  error?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface LlmPingResponse {
  ok: boolean
  provider: string
  mode: string
  model?: string
  base_url?: string
  latency_ms?: number
  text?: string
  error?: string
}

export interface LlmConfigResponse {
  mode: string
  provider: string
  model?: string | null
  base_url?: string | null
}

export interface LlmConfigRequest {
  mode: 'openai_compat' | 'ollama'
  ollama_base_url?: string
  ollama_model?: string
}

export interface DbPingResponse {
  ok: boolean
  dialect: string
  driver?: string
  host?: string
  port?: number
  database?: string
  latency_ms?: number
  error?: string
}

function isTauriRuntime(): boolean {
  if (typeof window === 'undefined') return false
  const w = window as any
  // Tauri v1 exposed __TAURI__. Tauri v2 commonly exposes __TAURI_INTERNALS__.
  return Boolean(w.__TAURI__ || w.__TAURI_INTERNALS__)
}

function apiBase(): string {
  // In normal web/dev, we rely on same-origin `/api` (Vite proxy in dev).
  // In Tauri production, the origin is not the dev server, so use the local backend.
  return isTauriRuntime() ? 'http://localhost:8000' : ''
}

async function http<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init.headers ?? {}),
    },
  })

  if (!res.ok) {
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const data = (await res.json().catch(() => null)) as any
      const detail = data?.detail ?? data?.error ?? null
      const msg =
        typeof detail === 'string'
          ? detail
          : detail
            ? JSON.stringify(detail)
            : data
              ? JSON.stringify(data)
              : ''
      throw new Error(msg || `HTTP ${res.status}`)
    }

    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }

  return (await res.json()) as T
}

export function generateDiagram(req: DiagramGenerateRequest) {
  return http<DiagramGenerateResponse>('/api/diagram/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function generateIntegration(req: IntegrationGenerateRequest) {
  return http<IntegrationGenerateResponse>('/api/integration/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function settlementMetrics(req: SettlementMetricsRequest) {
  return http<SettlementMetricsResponse>('/api/settlement/metrics', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function submitDiagramTask(req: DiagramGenerateRequest) {
  return http<TaskSubmitResponse>('/api/tasks/diagram', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function submitIntegrationTask(req: IntegrationGenerateRequest) {
  return http<TaskSubmitResponse>('/api/tasks/integration', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function getTaskStatus(taskId: string) {
  return http<TaskStatusResponse>(`/api/tasks/${encodeURIComponent(taskId)}`, {
    method: 'GET',
  })
}

export function listArtifacts(limit = 50) {
  return http<ArtifactOut[]>(`/api/artifacts/?limit=${limit}`, {
    method: 'GET',
  })
}

export function getArtifact(artifactId: string) {
  return http<ArtifactOut>(`/api/artifacts/${encodeURIComponent(artifactId)}`, {
    method: 'GET',
  })
}

export function llmPing() {
  return http<LlmPingResponse>('/api/llm/ping', {
    method: 'GET',
  })
}

export function getLlmConfig() {
  return http<LlmConfigResponse>('/api/llm/config', {
    method: 'GET',
  })
}

export function setLlmConfig(req: LlmConfigRequest) {
  return http<LlmConfigResponse>('/api/llm/config', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function dbPing() {
  return http<DbPingResponse>('/api/db/ping', {
    method: 'GET',
  })
}
