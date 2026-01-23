<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

import {
  dbPing,
  generateDiagram,
  generateIntegration,
  getArtifact,
  getTaskStatus,
  getLlmConfig,
  llmPing,
  listArtifacts,
  settlementMetrics,
  setLlmConfig,
  submitDiagramTask,
  submitIntegrationTask,
  type DiagramType,
  type ArtifactOut,
  type DbPingResponse,
  type LlmPingResponse,
} from './lib/api'
import { renderMermaid } from './lib/mermaid'

const activeTab = ref<'diagram' | 'integration' | 'settlement' | 'artifacts'>('diagram')

const STORAGE_KEYS = {
  statusPanelCollapsed: 'pdc:statusPanelCollapsed',
} as const

const statusPanelCollapsed = ref(false)

function loadBoolFromStorage(key: string, fallback: boolean) {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return fallback
    return raw === '1'
  } catch {
    return fallback
  }
}

function saveBoolToStorage(key: string, value: boolean) {
  try {
    localStorage.setItem(key, value ? '1' : '0')
  } catch {
    // ignore
  }
}

// LLM status (visualize where we call API / local model)
const llmLoading = ref(false)
const llmError = ref('')
const llm = ref<LlmPingResponse | null>(null)

const llmConfigLoading = ref(false)
const llmConfigError = ref('')
const llmMode = ref<'ollama' | 'openai_compat'>('ollama')
const ollamaBaseUrl = ref('http://localhost:11434')
const ollamaModel = ref('llama3.2:1b')

const ollamaPresetModels = ['llama3.2:1b', 'qwen3:4b']

let llmModeAutoApplyEnabled = false
let suppressLlmModeAutoApply = 0
let pendingLlmMode: 'ollama' | 'openai_compat' | null = null
let llmConfigApplyTimer: number | null = null

// DB status (PostgreSQL connectivity)
const dbLoading = ref(false)
const dbError = ref('')
const db = ref<DbPingResponse | null>(null)

const isDevProxy = computed(() => {
  const origin = window.location.origin
  return origin.includes('localhost:5173') || origin.includes('127.0.0.1:5173')
})

const backendApiBase = computed(() => {
  const origin = window.location.origin
  const base = `${origin}/api`
  return isDevProxy.value ? `${base}（dev 代理）` : base
})

const backendApiProxy = computed(() => {
  const origin = window.location.origin
  return `${origin}/api`
})

const backendApiBaseReal = computed(() => {
  return 'http://localhost:8000/api'
})

async function refreshLlm() {
  llmLoading.value = true
  llmError.value = ''
  try {
    llm.value = await llmPing()
  } catch (e) {
    llm.value = null
    llmError.value = e instanceof Error ? e.message : String(e)
  } finally {
    llmLoading.value = false
  }
}

async function refreshLlmConfig() {
  llmConfigLoading.value = true
  llmConfigError.value = ''
  suppressLlmModeAutoApply += 1
  try {
    const cfg = await getLlmConfig()
    // We only expose ollama / openai_compat in the UI.
    // If backend returns an unexpected mode, treat it as ollama (local) to avoid a dead-end UI.
    llmMode.value = cfg.mode === 'openai_compat' ? 'openai_compat' : 'ollama'

    // Auto-fill ollama settings when backend is in ollama mode.
    // (When in openai_compat, cfg.base_url refers to gateway URL and should not overwrite ollama inputs.)
    if (cfg.mode === 'ollama') {
      if (cfg.base_url) ollamaBaseUrl.value = String(cfg.base_url)
      if (cfg.model) ollamaModel.value = String(cfg.model)
    }
  } catch (e) {
    llmConfigError.value = e instanceof Error ? e.message : String(e)
  } finally {
    suppressLlmModeAutoApply -= 1
    llmConfigLoading.value = false
  }
}

async function applyLlmMode(mode: 'ollama' | 'openai_compat') {
  llmConfigLoading.value = true
  llmConfigError.value = ''
  try {
    // Note: openai_compat secrets and ollama defaults are configured via env.
    // The UI only switches the active mode.
    await setLlmConfig(
      mode === 'ollama'
        ? {
            mode,
            ollama_base_url: ollamaBaseUrl.value.trim() || undefined,
            ollama_model: ollamaModel.value.trim() || undefined,
          }
        : { mode }
    )
    await refreshLlmConfig()
    await refreshLlm()
  } catch (e) {
    llmConfigError.value = e instanceof Error ? e.message : String(e)
  } finally {
    llmConfigLoading.value = false
  }
}

function scheduleApplyLlmConfig(debounceMs = 0) {
  if (!llmModeAutoApplyEnabled) return
  if (suppressLlmModeAutoApply > 0) return

  if (llmConfigApplyTimer !== null) {
    window.clearTimeout(llmConfigApplyTimer)
    llmConfigApplyTimer = null
  }

  llmConfigApplyTimer = window.setTimeout(() => {
    llmConfigApplyTimer = null
    pendingLlmMode = llmMode.value
    void flushPendingLlmMode()
  }, debounceMs)
}

async function flushPendingLlmMode() {
  if (llmConfigLoading.value) return
  const mode = pendingLlmMode
  if (!mode) return
  pendingLlmMode = null
  await applyLlmMode(mode)
  if (pendingLlmMode) await flushPendingLlmMode()
}

watch(
  llmMode,
  (mode) => {
    if (!llmModeAutoApplyEnabled) return
    if (suppressLlmModeAutoApply > 0) return
    pendingLlmMode = mode
    void flushPendingLlmMode()
  },
  { flush: 'post' }
)

watch(
  [ollamaBaseUrl, ollamaModel],
  () => {
    if (!llmModeAutoApplyEnabled) return
    if (suppressLlmModeAutoApply > 0) return
    if (llmMode.value !== 'ollama') return
    // debounce a bit while typing
    scheduleApplyLlmConfig(300)
  },
  { flush: 'post' }
)

async function refreshDb() {
  dbLoading.value = true
  dbError.value = ''
  try {
    db.value = await dbPing()
  } catch (e) {
    db.value = null
    dbError.value = e instanceof Error ? e.message : String(e)
  } finally {
    dbLoading.value = false
  }
}

const featureMatrix = computed(() => {
  return [
    {
      feature: '自动出图（同步）',
      llm: '会',
      api: 'POST /api/diagram/generate',
      optional: '无',
    },
    {
      feature: '自动出图（异步）',
      llm: '会',
      api: 'POST /api/tasks/diagram + GET /api/tasks/{id}',
      optional: 'Celery/Redis 可选（默认 inproc）',
    },
    {
      feature: '接入方案（同步）',
      llm: '会',
      api: 'POST /api/integration/generate',
      optional: '无',
    },
    {
      feature: '接入方案（异步）',
      llm: '会',
      api: 'POST /api/tasks/integration + GET /api/tasks/{id}',
      optional: 'Celery/Redis 可选（默认 inproc）',
    },
    {
      feature: '结算指标',
      llm: '不会',
      api: 'POST /api/settlement/metrics',
      optional: '无',
    },
    {
      feature: '产物列表/详情',
      llm: '不会（读取元数据）',
      api: 'GET /api/artifacts/*',
      optional: 'Postgres/Alembic（未启用时返回 503）',
    },
  ]
})

type StepItem = { title: string; description?: string }

const llmSteps = computed<StepItem[]>(() => {
  return [
    { title: '前端点击生成' },
    { title: '后端 API' },
    { title: 'LLM' },
    { title: '结构化 Spec JSON' },
    { title: 'Mermaid 渲染' },
    { title: '前端 SVG' },
  ]
})

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitTask(taskId: string, timeoutMs = 15000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const status = await getTaskStatus(taskId)
    if (status.state === 'SUCCESS' || status.state === 'FAILURE') return status
    await sleep(300)
  }
  throw new Error('Task timeout')
}

// Diagram
const diagramType = ref<DiagramType>('flow')
const diagramText = ref(
  '用户提交退款申请 -> 系统校验 -> 进入人工审核 -> 审核通过则发起打款 -> 更新退款状态 -> 通知用户'
)
const diagramMermaid = ref('')
const diagramSvg = ref('')
const diagramLoading = ref(false)
const diagramError = ref('')
const diagramAsync = ref(true)
const diagramLocalTimeSec = ref<number | null>(null)

// Integration
const integrationText = ref(
  'A系统需要接入B系统查询订单与发起退款；涉及鉴权、幂等、回调通知与对账。请输出接入方案。'
)
const swaggerText = ref('')
const integrationMarkdown = ref('')
const integrationLoading = ref(false)
const integrationError = ref('')
const integrationAsync = ref(true)

// Settlement
const month = ref('2026-01')
const settlementLoading = ref(false)
const settlementError = ref('')
const metrics = ref<Record<string, number>>({})
const chartEl = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const metricsRows = computed(() =>
  Object.entries(metrics.value).map(([k, v]) => ({ name: k, value: v }))
)

function downloadTextFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  try {
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    URL.revokeObjectURL(url)
  }
}

function onDownloadDiagramSvg() {
  if (!diagramSvg.value) return
  const safeType = diagramType.value || 'diagram'
  const filename = `diagram-${safeType}-${new Date().toISOString().slice(0, 10)}.svg`
  downloadTextFile(filename, diagramSvg.value, 'image/svg+xml;charset=utf-8')
}

async function onGenerateDiagram() {
  const startedAt = performance.now()
  diagramError.value = ''
  diagramSvg.value = ''
  diagramMermaid.value = ''
  diagramLocalTimeSec.value = null
  diagramLoading.value = true
  try {
    const payload = {
      diagram_type: diagramType.value,
      text: diagramText.value,
      scene: 'product',
    } as const

    if (diagramAsync.value) {
      const submit = await submitDiagramTask(payload)
      const status = await waitTask(submit.task_id)
      const result = (status.result ?? {}) as Record<string, unknown>
      if (status.state === 'FAILURE') {
        throw new Error(String(result.error ?? 'Task failed'))
      }
      const mermaid = String(result.mermaid ?? '')
      diagramMermaid.value = mermaid
      diagramSvg.value = mermaid ? await renderMermaid(`m-${Date.now()}`, mermaid) : ''
    } else {
      const res = await generateDiagram(payload)
      diagramMermaid.value = res.mermaid
      diagramSvg.value = await renderMermaid(`m-${Date.now()}`, res.mermaid)
    }

    diagramLocalTimeSec.value = (performance.now() - startedAt) / 1000
  } catch (e) {
    diagramError.value = e instanceof Error ? e.message : String(e)
  } finally {
    diagramLoading.value = false
  }
}

async function onGenerateIntegration() {
  integrationError.value = ''
  integrationLoading.value = true
  try {
    const payload = {
      text: integrationText.value,
      swagger_text: swaggerText.value || undefined,
    } as const

    if (integrationAsync.value) {
      const submit = await submitIntegrationTask(payload)
      const status = await waitTask(submit.task_id)
      const result = (status.result ?? {}) as Record<string, unknown>
      if (status.state === 'FAILURE') {
        throw new Error(String(result.error ?? 'Task failed'))
      }
      integrationMarkdown.value = String(result.markdown ?? '')
    } else {
      const res = await generateIntegration(payload)
      integrationMarkdown.value = res.markdown
    }
  } catch (e) {
    integrationError.value = e instanceof Error ? e.message : String(e)
  } finally {
    integrationLoading.value = false
  }
}

function ensureChart() {
  if (!chartEl.value) return
  if (chart) return
  chart = echarts.init(chartEl.value)
}

function updateChart() {
  ensureChart()
  if (!chart) return
  const rows = metricsRows.value
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: rows.map((r) => r.name) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: rows.map((r) => r.value) }],
  })
}

async function onComputeSettlement() {
  settlementError.value = ''
  settlementLoading.value = true
  try {
    const rows = [
      { amount: 1000, status: 'success', channel: 'bank' },
      { amount: 800, status: 'success', channel: 'bank' },
      { amount: 120, status: 'failed', channel: 'wallet' },
      { amount: 560, status: 'success', channel: 'wallet' },
      { amount: 300, status: 'pending', channel: 'bank' },
    ]
    const res = await settlementMetrics({ month: month.value, rows })
    metrics.value = res.metrics
    updateChart()
  } catch (e) {
    settlementError.value = e instanceof Error ? e.message : String(e)
  } finally {
    settlementLoading.value = false
  }
}

watch(metricsRows, () => updateChart())

onMounted(async () => {
  updateChart()
  statusPanelCollapsed.value = loadBoolFromStorage(STORAGE_KEYS.statusPanelCollapsed, false)
  await refreshLlmConfig()
  await refreshLlm()
  await refreshDb()
  llmModeAutoApplyEnabled = true
})

watch(statusPanelCollapsed, (v) => saveBoolToStorage(STORAGE_KEYS.statusPanelCollapsed, v))

// Artifacts
const artifactsLoading = ref(false)
const artifactsError = ref('')
const artifacts = ref<ArtifactOut[]>([])
const selectedArtifactId = ref('')
const selectedArtifact = ref<ArtifactOut | null>(null)

async function refreshArtifacts() {
  artifactsError.value = ''
  artifactsLoading.value = true
  try {
    artifacts.value = await listArtifacts(50)
  } catch (e) {
    artifactsError.value = e instanceof Error ? e.message : String(e)
  } finally {
    artifactsLoading.value = false
  }
}

async function loadArtifact(id: string) {
  selectedArtifactId.value = id
  selectedArtifact.value = null
  artifactsError.value = ''
  try {
    selectedArtifact.value = await getArtifact(id)
  } catch (e) {
    artifactsError.value = e instanceof Error ? e.message : String(e)
  }
}
</script>

<template>
  <div class="app">
    <el-container style="height: 100vh">
      <el-header class="header">
        <div class="brand">
          <div class="title">产品智绘官（Product Diagram Copilot）</div>
          <div class="subtitle">文本 → Diagram Spec → Mermaid / 结算指标可视化</div>
        </div>

        <div class="headerRight">
          <el-tag size="small" :type="db?.ok ? 'success' : 'warning'">
            DB: {{ db?.ok ? 'ok' : 'down' }}
          </el-tag>
          <el-tag size="small" type="info">DB Latency: {{ db?.latency_ms ?? '-' }}ms</el-tag>
          <el-tag size="small" :type="llm?.ok ? 'success' : 'warning'">
            LLM: {{ llm?.mode || 'unknown' }}
          </el-tag>
          <el-tag size="small" type="info">Model: {{ llm?.model || '-' }}</el-tag>
          <el-tag size="small" type="info">Latency: {{ llm?.latency_ms ?? '-' }}ms</el-tag>
          <el-button size="small" :loading="llmLoading || dbLoading" @click="() => { refreshDb(); refreshLlm(); }">
            刷新
          </el-button>
        </div>
      </el-header>

      <el-main class="main">
        <el-card class="mb panel" shadow="never">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span>LLM / DB 状态 & 可选组件</span>
              <div style="display: flex; align-items: center; gap: 8px">
                <el-button
                  size="small"
                  @click="() => { statusPanelCollapsed = !statusPanelCollapsed }"
                >
                  {{ statusPanelCollapsed ? '展开' : '折叠' }}
                </el-button>
                <el-button
                  size="small"
                  :loading="llmLoading || dbLoading"
                  :disabled="statusPanelCollapsed"
                  @click="() => { refreshDb(); refreshLlm(); }"
                >
                  刷新
                </el-button>
              </div>
            </div>
          </template>

          <div v-show="!statusPanelCollapsed">
            <el-alert
              v-if="llmError"
              type="error"
              :title="llmError"
              show-icon
              class="mb"
            />

            <el-alert v-if="dbError" type="error" :title="dbError" show-icon class="mb" />

            <el-row :gutter="16">
              <el-col :span="10">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="后端（FastAPI）">
                    <template v-if="isDevProxy">
                      <div>后端代理：{{ backendApiProxy }}</div>
                      <div style="margin-top: 6px; opacity: 0.85">
                        后端地址：{{ backendApiBaseReal }}
                      </div>
                    </template>
                    <template v-else>
                      <div>后端地址：{{ backendApiBase }}</div>
                    </template>
                  </el-descriptions-item>
                  <el-descriptions-item label="数据库">
                    <el-tag v-if="db" :type="db.ok ? 'success' : 'danger'">{{ db.ok ? 'OK' : 'DOWN' }}</el-tag>
                    <span v-else>-</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="DB 连接">
                    <span v-if="db">{{ db.dialect }}://{{ db.host || '-' }}:{{ db.port ?? '-' }}/{{ db.database || '-' }}</span>
                    <span v-else>-</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="DB 延迟">
                    <span v-if="db">{{ db.latency_ms ?? '-' }} ms</span>
                    <span v-else>-</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="当前模式">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap">
                      <el-tag v-if="llm" :type="llm.ok ? 'success' : 'danger'">{{ llm.mode }}</el-tag>
                      <span v-else>-</span>

                      <el-select
                        v-model="llmMode"
                        size="small"
                        :disabled="llmConfigLoading"
                        :loading="llmConfigLoading"
                        loading-text="模型切换中…"
                        style="min-width: 210px"
                      >
                        <el-option label="ollama（本地模型）" value="ollama" />
                        <el-option label="openai_compat（兼容网关）" value="openai_compat" />
                      </el-select>
                    </div>

                    <div v-if="llmMode === 'ollama'" style="margin-top: 10px">
                      <el-form label-position="top" size="small" style="max-width: 520px">
                        <el-form-item label="Ollama Base URL">
                          <el-input v-model="ollamaBaseUrl" placeholder="http://localhost:11434" :disabled="llmConfigLoading" />
                        </el-form-item>
                        <el-form-item label="Ollama Model">
                          <el-select
                            v-model="ollamaModel"
                            filterable
                            allow-create
                            default-first-option
                            placeholder="选择或输入模型名（例如 llama3.2:1b）"
                            style="width: 100%"
                            :disabled="llmConfigLoading"
                          >
                            <el-option v-for="m in ollamaPresetModels" :key="m" :label="m" :value="m" />
                          </el-select>
                        </el-form-item>
                      </el-form>
                    </div>

                    <el-alert
                      v-if="llmConfigError"
                      type="error"
                      :title="llmConfigError"
                      show-icon
                      :closable="false"
                      class="mt"
                    />
                  </el-descriptions-item>
                  <el-descriptions-item label="Provider">
                    <span v-if="llm">{{ llm.provider }}</span>
                    <span v-else>-</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="延迟">
                    <span v-if="llm">{{ llm.latency_ms ?? '-' }} ms</span>
                    <span v-else>-</span>
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>

              <el-col :span="14">
                <el-steps
                  :active="llmSteps.length + 1"
                  align-center
                  process-status="success"
                  finish-status="success"
                  class="steps"
                >
                  <el-step
                    v-for="s in llmSteps"
                    :key="`${s.title}::${s.description || ''}`"
                    :title="s.title"
                    :description="s.description"
                  />
                </el-steps>

                <el-table :data="featureMatrix" size="small" border style="width: 100%">
                  <el-table-column prop="feature" label="功能" width="170" />
                  <el-table-column prop="llm" label="调用大模型" width="90" />
                  <el-table-column prop="api" label="后端 API" />
                  <el-table-column prop="optional" label="可选依赖/组件" width="240" />
                </el-table>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <el-tabs v-model="activeTab" class="tabs">
          <el-tab-pane label="自动出图" name="diagram">
            <el-row :gutter="16">
              <el-col :span="10">
                <el-form label-position="top">
                  <el-form-item label="图类型">
                    <el-select v-model="diagramType" style="width: 100%">
                      <el-option label="流程图" value="flow" />
                      <el-option label="时序图" value="sequence" />
                      <el-option label="状态图" value="state" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="描述文本">
                    <el-input v-model="diagramText" type="textarea" :rows="10" />
                  </el-form-item>
                  <el-form-item label="执行模式">
                    <el-switch v-model="diagramAsync" active-text="异步" inactive-text="同步" />
                  </el-form-item>
                  <el-button type="primary" :loading="diagramLoading" @click="onGenerateDiagram">
                    生成
                  </el-button>
                  <div v-if="diagramLocalTimeSec !== null" class="mt" style="opacity: 0.85">
                    本次生成时间：{{ diagramLocalTimeSec.toFixed(2) }} 秒
                  </div>
                  <el-alert v-if="diagramError" type="error" :title="diagramError" show-icon class="mt" />
                </el-form>
              </el-col>
              <el-col :span="14">
                <el-card>
                  <template #header>
                    <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px">
                      <span>渲染结果</span>
                      <el-button size="small" :disabled="!diagramSvg" @click="onDownloadDiagramSvg">
                        下载 SVG
                      </el-button>
                    </div>
                  </template>
                  <div v-if="diagramSvg" v-html="diagramSvg" class="mermaid" />
                  <el-empty v-else description="点击生成后展示" />
                </el-card>
                <el-card class="mt">
                  <template #header>Mermaid 源码</template>
                  <el-input v-model="diagramMermaid" type="textarea" :rows="8" readonly />
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <el-tab-pane label="接入方案" name="integration">
            <el-row :gutter="16">
              <el-col :span="10">
                <el-form label-position="top">
                  <el-form-item label="业务描述">
                    <el-input v-model="integrationText" type="textarea" :rows="8" />
                  </el-form-item>
                  <el-form-item label="Swagger / 接口文档文本（可选）">
                    <el-input v-model="swaggerText" type="textarea" :rows="8" />
                  </el-form-item>
                  <el-form-item label="执行模式">
                    <el-switch v-model="integrationAsync" active-text="异步" inactive-text="同步" />
                  </el-form-item>
                  <el-button type="primary" :loading="integrationLoading" @click="onGenerateIntegration">
                    生成
                  </el-button>
                  <el-alert
                    v-if="integrationError"
                    type="error"
                    :title="integrationError"
                    show-icon
                    class="mt"
                  />
                </el-form>
              </el-col>
              <el-col :span="14">
                <el-card>
                  <template #header>方案输出（Markdown 文本）</template>
                  <el-input v-model="integrationMarkdown" type="textarea" :rows="18" readonly />
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <el-tab-pane label="结算指标" name="settlement">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form label-position="top">
                  <el-form-item label="月份（YYYY-MM）">
                    <el-input v-model="month" placeholder="2026-01" />
                  </el-form-item>
                  <el-button type="primary" :loading="settlementLoading" @click="onComputeSettlement">
                    计算示例指标
                  </el-button>
                  <el-alert
                    v-if="settlementError"
                    type="error"
                    :title="settlementError"
                    show-icon
                    class="mt"
                  />
                </el-form>

                <el-table :data="metricsRows" class="mt" size="small" border>
                  <el-table-column prop="name" label="指标" />
                  <el-table-column prop="value" label="数值" />
                </el-table>
              </el-col>
              <el-col :span="16">
                <el-card>
                  <template #header>图表</template>
                  <div ref="chartEl" style="height: 420px; width: 100%" />
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <el-tab-pane label="产物" name="artifacts">
            <el-row :gutter="16">
              <el-col :span="10">
                <el-button :loading="artifactsLoading" @click="refreshArtifacts">刷新列表</el-button>
                <el-alert v-if="artifactsError" type="error" :title="artifactsError" show-icon class="mt" />

                <el-table
                  :data="artifacts"
                  class="mt"
                  size="small"
                  border
                  height="480"
                  @row-click="(row: any) => loadArtifact(row.id)"
                >
                  <el-table-column prop="id" label="ID" width="220" />
                  <el-table-column prop="kind" label="类型" width="110" />
                  <el-table-column prop="status" label="状态" width="110" />
                  <el-table-column prop="created_at" label="创建时间" />
                </el-table>
              </el-col>

              <el-col :span="14">
                <el-card>
                  <template #header>产物详情</template>
                  <div v-if="selectedArtifact">
                    <el-descriptions :column="1" size="small" border>
                      <el-descriptions-item label="ID">{{ selectedArtifact.id }}</el-descriptions-item>
                      <el-descriptions-item label="类型">{{ selectedArtifact.kind }}</el-descriptions-item>
                      <el-descriptions-item label="状态">{{ selectedArtifact.status }}</el-descriptions-item>
                      <el-descriptions-item label="Object Key">{{ selectedArtifact.object_key }}</el-descriptions-item>
                    </el-descriptions>

                    <el-divider />
                    <el-form label-position="top">
                      <el-form-item v-if="selectedArtifact.mermaid" label="Mermaid">
                        <el-input v-model="selectedArtifact.mermaid" type="textarea" :rows="8" readonly />
                      </el-form-item>
                      <el-form-item v-if="selectedArtifact.markdown" label="Markdown">
                        <el-input v-model="selectedArtifact.markdown" type="textarea" :rows="10" readonly />
                      </el-form-item>
                      <el-form-item v-if="selectedArtifact.error" label="错误">
                        <el-input v-model="selectedArtifact.error" type="textarea" :rows="4" readonly />
                      </el-form-item>
                    </el-form>
                  </div>
                  <el-empty v-else description="点击左侧列表查看" />
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
:global(html) {
  scrollbar-gutter: stable;
}

:global(body) {
  overflow-y: scroll;
}

.app {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--el-bg-color) 0%, var(--el-fill-color-lighter) 100%);
  position: relative;
  isolation: isolate;
}

.app::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: -1;
  background:
    repeating-linear-gradient(
      0deg,
      transparent 0,
      transparent 22px,
      color-mix(in srgb, var(--el-border-color-lighter) 55%, transparent) 23px
    ),
    repeating-linear-gradient(
      90deg,
      transparent 0,
      transparent 22px,
      color-mix(in srgb, var(--el-border-color-lighter) 35%, transparent) 23px
    );
  opacity: 0.55;
}

.header {
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  box-shadow: var(--el-box-shadow-lighter);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    repeating-linear-gradient(
      135deg,
      transparent 0,
      transparent 14px,
      color-mix(in srgb, var(--el-color-primary) 18%, transparent) 15px,
      transparent 22px
    ),
    linear-gradient(
      90deg,
      transparent 0,
      color-mix(in srgb, var(--el-border-color-lighter) 55%, transparent) 45%,
      transparent 70%
    );
  opacity: 0.55;
  transform: translateZ(0);
  animation: headerTechLines 14s linear infinite;
  mask-image: linear-gradient(90deg, transparent 0, #000 18%, #000 82%, transparent 100%);
}

.header::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(
      circle at 12% 40%,
      color-mix(in srgb, var(--el-color-primary) 28%, transparent) 0 1px,
      transparent 2px
    ),
    radial-gradient(
      circle at 72% 30%,
      color-mix(in srgb, var(--el-color-success) 20%, transparent) 0 1px,
      transparent 2px
    ),
    radial-gradient(
      circle at 42% 78%,
      color-mix(in srgb, var(--el-border-color-lighter) 70%, transparent) 0 1px,
      transparent 2px
    );
  background-size: 280px 140px;
  opacity: 0.35;
  transform: translateZ(0);
  animation: headerParticles 22s linear infinite;
  mask-image: linear-gradient(90deg, transparent 0, #000 10%, #000 90%, transparent 100%);
}

@keyframes headerTechLines {
  from {
    background-position: 0 0, 0 0;
  }
  to {
    background-position: 240px 0, -120px 0;
  }
}

@keyframes headerParticles {
  from {
    background-position: 0 0;
  }
  to {
    background-position: -280px 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .header::before,
  .header::after {
    animation: none;
  }
}

.brand {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.headerRight {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.title {
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.3px;
}

.subtitle {
  font-size: 12px;
  opacity: 0.75;
}

.main {
  padding: 16px;
  width: 100%;
  max-width: none;
  margin: 0;
}

.panel {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-bg-color) 88%, transparent);
  backdrop-filter: blur(10px);
}

.mt {
  margin-top: 12px;
}

.mb {
  margin-bottom: 12px;
}

.steps {
  margin-bottom: 12px;
  padding: 8px 10px 6px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color);
  overflow: hidden;
  flex-wrap: nowrap;
  min-height: 64px;
}

.steps :deep(.el-step__title) {
  font-size: 12px;
  line-height: 1.25;
  max-width: 180px;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  text-align: center;
}

.steps :deep(.el-step__description) {
  font-size: 11px;
  line-height: 1.25;
  max-width: 180px;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  text-align: center;
}

.steps :deep(.el-step__head.is-success) {
  color: var(--el-color-success);
  border-color: var(--el-color-success);
}

.steps :deep(.el-step__head.is-process),
.steps :deep(.el-step__head.is-wait) {
  color: var(--el-color-success);
  border-color: var(--el-color-success);
}

.steps :deep(.el-step__title.is-process),
.steps :deep(.el-step__title.is-wait) {
  color: var(--el-color-success);
}

.steps :deep(.el-step__icon) {
  border-color: var(--el-color-success);
}

.steps :deep(.el-step__line) {
  background-color: var(--el-color-success);
}

.steps :deep(.el-step__line-inner) {
  border-color: var(--el-color-success);
}

.mermaid :deep(svg) {
  max-width: 100%;
  height: auto;
}
</style>
