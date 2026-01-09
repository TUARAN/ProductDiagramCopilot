export type DiagramType = 'flow' | 'sequence' | 'state'

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

async function http<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(init.headers ?? {}),
    },
  })

  if (!res.ok) {
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

export function dbPing() {
  return http<DbPingResponse>('/api/db/ping', {
    method: 'GET',
  })
}
