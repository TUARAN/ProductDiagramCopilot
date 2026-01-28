<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { Loading } from '@element-plus/icons-vue'
import { jsPDF } from 'jspdf'

import LogPage from './components/LogPage.vue'

import { PDC_CONFIG, type BusinessId, type StrategyId, type PdcStrategy } from './config/pdc.config'

import {
  dbPing,
  generateDiagram,
  generateDrawioXml,
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

import drawioBlankXml from './assets/drawio-blank.drawio?raw'

const activeTab = ref<'diagram' | 'drawio' | 'integration' | 'settlement' | 'artifacts'>('diagram')

const logsOpen = ref(false)
const statusPanelOpen = ref(false)

// NOTE: These refs are used by applyTemplateSeed(). Keep them declared before
// any watchers that might call applyTemplateSeed during setup.
const diagramType = ref<DiagramType>('flow')
const diagramText = ref('')
const drawioGenText = ref('')

// Business optional configuration (front-end)
const selectedBusinessId = ref<BusinessId | ''>('')
const selectedTemplateId = ref<string>('')
const selectedStrategyId = ref<StrategyId | ''>('')

const selectedBusiness = computed(() =>
  selectedBusinessId.value
    ? (PDC_CONFIG.businesses.find((b) => b.businessId === selectedBusinessId.value) ?? null)
    : null
)

const templatesForBusiness = computed(() => {
  const biz = selectedBusiness.value
  if (!biz) return []
  const enabled = new Set(biz.enabledTemplates)
  return PDC_CONFIG.templates.filter((t) => t.businessId === biz.businessId && enabled.has(t.templateId))
})

const selectedTemplate = computed(() =>
  templatesForBusiness.value.find((t) => t.templateId === selectedTemplateId.value) ?? null
)

const strategiesForSelection = computed(() => {
  const biz = selectedBusiness.value
  if (!biz) return []

  const enabled = new Set<StrategyId>(biz.enabledStrategies)
  const recommended = selectedTemplate.value?.recommendedStrategyIds?.length
    ? new Set<StrategyId>(selectedTemplate.value.recommendedStrategyIds)
    : null

  const ids = biz.enabledStrategies.filter((id) => enabled.has(id) && (!recommended || recommended.has(id)))
  const byId = new Map(PDC_CONFIG.strategies.map((s) => [s.strategyId, s]))
  return ids
    .map((id) => byId.get(id))
    .filter((s): s is PdcStrategy => Boolean(s))
})

const selectedStrategy = computed(() =>
  selectedStrategyId.value
    ? (PDC_CONFIG.strategies.find((s) => s.strategyId === selectedStrategyId.value) ?? null)
    : null
)

const lastTemplateSeededId = ref<string>('')
const lastSeededDiagramText = ref<string>('')
const lastSeededDrawioText = ref<string>('')

function shouldReplaceSeed(current: string, lastSeed: string) {
  const cur = (current ?? '').trim()
  const last = (lastSeed ?? '').trim()
  return !cur || (last && cur === last)
}

function applyTemplateSeed() {
  const t = selectedTemplate.value
  if (!t) return

  const bizLabel = (selectedBusiness.value?.label ?? '').trim()
  const rawExample = (t.exampleInputs?.[0] ?? '').trim()
  const example =
    rawExample && bizLabel && !rawExample.includes(bizLabel)
      ? `【${bizLabel}】${rawExample}`
      : rawExample

  if (t.graphType === 'architecture') {
    activeTab.value = 'drawio'
    if (example && shouldReplaceSeed(drawioGenText.value, lastSeededDrawioText.value)) {
      drawioGenText.value = example
      lastSeededDrawioText.value = example
      lastTemplateSeededId.value = t.templateId
    }
    return
  }

  if (t.graphType === 'metrics') {
    activeTab.value = 'settlement'
    return
  }

  // flow default to Mermaid diagram tab
  activeTab.value = 'diagram'
  if (example && shouldReplaceSeed(diagramText.value, lastSeededDiagramText.value)) {
    diagramText.value = example
    lastSeededDiagramText.value = example
    lastTemplateSeededId.value = t.templateId
  }
  // Current UI supports flow/sequence/state only.
  if (t.graphType === 'sequence') diagramType.value = 'sequence'
  else if (t.graphType === 'state') diagramType.value = 'state'
  else diagramType.value = 'flow'
}

function applyStrategyRouting() {
  const s = selectedStrategy.value
  if (!s) return
  if (s.pipelineKind === 'drawio_editable') activeTab.value = 'drawio'
  else if (s.pipelineKind === 'settlement_echarts') activeTab.value = 'settlement'
  else activeTab.value = 'diagram'
}

watch(
  selectedBusinessId,
  () => {
    // Business selection should not default template/strategy.
    selectedTemplateId.value = ''
    selectedStrategyId.value = ''
  }
)

watch(selectedTemplateId, () => {
  if (!selectedTemplateId.value) return
  // If template recommends strategies, align to its first recommendation.
  const rec = selectedTemplate.value?.recommendedStrategyIds?.[0]
  if (rec && !selectedStrategyId.value) selectedStrategyId.value = rec
  applyStrategyRouting()
  applyTemplateSeed()
})

watch(selectedStrategyId, () => {
  if (!selectedStrategyId.value) return
  applyStrategyRouting()
})

const STORAGE_KEYS = {
  statusPanelCollapsed: 'pdc:statusPanelCollapsed',
  drawioXml: 'pdc:drawioXml',
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

// draw.io (diagrams.net) embedded editor
type DrawioExportKind = 'png' | 'pdf'

const drawioFrame = ref<HTMLIFrameElement | null>(null)
const drawioReady = ref(false)
const drawioError = ref('')
const drawioStatus = ref('')
const drawioBusy = ref(false)
const drawioXml = ref('')
let drawioPendingSave: ((xml: string) => void) | null = null
let drawioPendingExport: DrawioExportKind | null = null

const drawioGenLoading = ref(false)

const drawioEmbedUrl = computed(() => {
  const params = new URLSearchParams({
    embed: '1',
    proto: 'json',
    spin: '1',
    libraries: '1',
    noExitBtn: '1',
    ui: 'min',
    lang: 'zh',
  })
  return `https://embed.diagrams.net/?${params.toString()}`
})

function onDrawioMessage(ev: MessageEvent) {
  if (ev.origin !== 'https://embed.diagrams.net') return
  const msg = parseDrawioMessage(ev.data)
  if (!msg) return

  if (msg.error) {
    drawioError.value = String(msg.error)
    drawioBusy.value = false
    drawioPendingExport = null
    return
  }

  if (msg.event === 'init') {
    drawioReady.value = true
    loadDrawio(drawioXml.value || drawioBlankXml)
    return
  }

  if (msg.event === 'load') {
    drawioStatus.value = '已加载'
    return
  }

  if (msg.event === 'autosave' || msg.event === 'save') {
    const xml = typeof msg.xml === 'string' ? msg.xml : ''
    if (xml) {
      drawioXml.value = xml
      saveTextToStorage(STORAGE_KEYS.drawioXml, xml)
      drawioStatus.value = msg.event === 'save' ? '已保存' : '自动保存'
      if (drawioPendingSave) drawioPendingSave(xml)
    }
    return
  }

  if (msg.event === 'export') {
    const dataUri = typeof msg.data === 'string' ? msg.data : ''
    const pending = drawioPendingExport
    drawioPendingExport = null
    drawioBusy.value = false
    if (!dataUri) {
      drawioError.value = '导出失败（未返回 data URI）'
      return
    }

    const date = new Date().toISOString().slice(0, 10)
    if (pending === 'png') {
      downloadDataUri(`drawio-${date}.png`, dataUri)
      drawioStatus.value = '已导出 PNG'
      return
    }

    if (pending === 'pdf') {
      void (async () => {
        try {
          const img = await dataUriToImage(dataUri)
          const orientation = img.width >= img.height ? 'landscape' : 'portrait'
          const pdf = new jsPDF({
            orientation,
            unit: 'px',
            format: [img.width, img.height],
            compress: true,
          })
          pdf.addImage(dataUri, 'PNG', 0, 0, img.width, img.height)
          pdf.save(`drawio-${date}.pdf`)
          drawioStatus.value = '已导出 PDF'
        } catch (e) {
          drawioError.value = e instanceof Error ? e.message : String(e)
        }
      })()
    }
  }
}

function loadTextFromStorage(key: string, fallback: string) {
  try {
    const raw = localStorage.getItem(key)
    return raw === null ? fallback : raw
  } catch {
    return fallback
  }
}

function saveTextToStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // ignore
  }
}

function postToDrawio(message: Record<string, unknown>) {
  const win = drawioFrame.value?.contentWindow
  if (!win) return
  // Embed mode is only supported on embed.diagrams.net
  win.postMessage(JSON.stringify(message), 'https://embed.diagrams.net')
}

function parseDrawioMessage(data: unknown): any | null {
  if (typeof data !== 'string') return null
  try {
    return JSON.parse(data)
  } catch {
    return null
  }
}

function loadDrawio(xml: string) {
  if (!drawioReady.value) return
  drawioError.value = ''
  drawioStatus.value = '正在加载…'
  postToDrawio({
    action: 'load',
    xml,
    autosave: 1,
    title: '架构图（draw.io）',
  })
}

function requestDrawioSave(timeoutMs = 4000): Promise<string> {
  if (!drawioReady.value) return Promise.reject(new Error('draw.io 未就绪'))
  drawioError.value = ''
  drawioStatus.value = '正在保存…'
  drawioBusy.value = true
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      if (drawioPendingSave) drawioPendingSave = null
      drawioBusy.value = false
      reject(new Error('保存超时（draw.io 未返回 save 事件）'))
    }, timeoutMs)

    drawioPendingSave = (xml: string) => {
      window.clearTimeout(timer)
      drawioPendingSave = null
      drawioBusy.value = false
      resolve(xml)
    }

    postToDrawio({ action: 'save' })
  })
}

async function ensureLatestDrawioXml() {
  // If autosave is enabled, we likely already have XML.
  if (drawioXml.value) return drawioXml.value
  const xml = await requestDrawioSave()
  return xml
}

async function onDrawioSaveClick() {
  try {
    await requestDrawioSave()
  } catch (e) {
    drawioError.value = e instanceof Error ? e.message : String(e)
  }
}

function downloadDataUri(filename: string, dataUri: string) {
  const a = document.createElement('a')
  a.href = dataUri
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

function dataUriToImage(dataUri: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('无法加载导出的 PNG'))
    img.src = dataUri
  })
}

async function exportDrawio(kind: DrawioExportKind) {
  if (!drawioReady.value) return
  drawioError.value = ''
  drawioStatus.value = '正在导出…'
  drawioBusy.value = true
  drawioPendingExport = kind
  const xml = await ensureLatestDrawioXml().catch((e) => {
    drawioBusy.value = false
    drawioError.value = e instanceof Error ? e.message : String(e)
    return ''
  })
  if (!xml) return

  postToDrawio({
    action: 'export',
    format: 'png',
    // Higher scale for sharper PNG/PDF
    scale: 2,
    transparent: true,
    xml,
    spin: '1',
    message: '正在生成图片…',
  })
}

async function exportDrawioJson() {
  drawioError.value = ''
  try {
    const xml = await ensureLatestDrawioXml()
    const payload = {
      format: 'drawio',
      version: 1,
      exported_at: new Date().toISOString(),
      xml,
    }
    downloadTextFile(
      `drawio-${new Date().toISOString().slice(0, 10)}.json`,
      JSON.stringify(payload, null, 2),
      'application/json;charset=utf-8'
    )
    drawioStatus.value = '已导出 JSON'
  } catch (e) {
    drawioError.value = e instanceof Error ? e.message : String(e)
  }
}

async function exportDrawioXmlFile() {
  drawioError.value = ''
  try {
    const xml = await ensureLatestDrawioXml()
    downloadTextFile(
      `drawio-${new Date().toISOString().slice(0, 10)}.drawio`,
      xml,
      'application/xml;charset=utf-8'
    )
    drawioStatus.value = '已导出 .drawio'
  } catch (e) {
    drawioError.value = e instanceof Error ? e.message : String(e)
  }
}

function resetDrawioToMock() {
  drawioXml.value = drawioBlankXml
  saveTextToStorage(STORAGE_KEYS.drawioXml, drawioXml.value)
  loadDrawio(drawioXml.value)
  drawioStatus.value = '已重置为默认模板'
}

async function onGenerateDrawioFromText() {
  drawioError.value = ''

  const text = (drawioGenText.value || '').trim()
  if (!text) {
    drawioError.value = '请先输入描述文本'
    return
  }
  if (drawioGenLoading.value || drawioBusy.value) return

  drawioGenLoading.value = true
  try {
    const resp = await generateDrawioXml({ text })
    const xml = (resp?.xml || '').trim()
    if (!xml) throw new Error('生成失败（未返回 XML）')

    drawioXml.value = xml
    saveTextToStorage(STORAGE_KEYS.drawioXml, drawioXml.value)

    // If iframe already initialized, load immediately. Otherwise it will load on init.
    if (drawioReady.value) loadDrawio(drawioXml.value)
    drawioStatus.value = '已根据描述生成并加载'
  } catch (e) {
    drawioError.value = e instanceof Error ? e.message : String(e)
  } finally {
    drawioGenLoading.value = false
  }
}

async function importDrawioFile(file: File) {
  drawioError.value = ''
  try {
    const text = await file.text()
    drawioXml.value = text
    saveTextToStorage(STORAGE_KEYS.drawioXml, drawioXml.value)
    loadDrawio(drawioXml.value)
    drawioStatus.value = `已导入：${file.name}`
  } catch (e) {
    drawioError.value = e instanceof Error ? e.message : String(e)
  }
}

function onDrawioFileInputChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  // allow selecting the same file repeatedly
  input.value = ''
  if (!file) return
  void importDrawioFile(file)
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
  if (activeTab.value === 'drawio') {
    return [
      { title: '前端点击生成' },
      { title: '后端 API' },
      { title: 'LLM' },
      { title: '结构化 draw.io XML' },
      { title: '载入 draw.io 编辑器' },
      { title: '可编辑 & 导出产物' },
    ]
  }

  if (activeTab.value === 'integration') {
    return [
      { title: '前端点击生成' },
      { title: '后端 API' },
      { title: 'LLM' },
      { title: '结构化输出（Markdown/方案）' },
      { title: '前端展示' },
    ]
  }

  if (activeTab.value === 'settlement') {
    return [
      { title: '前端点击生成' },
      { title: '后端 API' },
      { title: '结算计算/聚合' },
      { title: '前端 ECharts 渲染' },
    ]
  }

  if (activeTab.value === 'artifacts') {
    return [
      { title: '前端加载' },
      { title: '后端 API' },
      { title: '展示产物元数据' },
    ]
  }

  // Default: Mermaid auto diagram pipeline
  return [
    { title: '前端点击生成' },
    { title: '后端 API' },
    { title: 'LLM' },
    { title: '结构化 Spec JSON' },
    { title: 'Mermaid 渲染' },
    { title: '前端 SVG' },
  ]
})

// Active step for the pipeline UI (Element Plus Steps)
// We use a 1-based index here and set it to (steps.length + 1) when finished.
const llmStepActive = ref(llmSteps.value.length + 1)

watch(activeTab, () => {
  llmStepActive.value = llmSteps.value.length + 1
})

function setLlmStepActive(step: number) {
  const total = llmSteps.value.length + 1
  const next = Math.max(1, Math.min(step, total))
  llmStepActive.value = next
}

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
const diagramMermaid = ref('')
const diagramSvg = ref('')
const diagramLoading = ref(false)
const diagramError = ref('')
const diagramAsync = ref(true)
const diagramLocalTimeSec = ref<number | null>(null)

// Page-level loading (fullscreen)
const pageLoading = ref(false)
const pageLoadingMessage = ref('正在准备…')
const pageLoadingContext = ref<'switch' | 'generate' | null>(null)
let pageLoadingTimer: number | null = null
let pageLoadingMessageIndex = 0

function startPageLoading(context: 'switch' | 'generate') {
  pageLoadingContext.value = context
  pageLoading.value = true
}

function stopPageLoading() {
  pageLoading.value = false
  pageLoadingContext.value = null
}

watch(
  pageLoading,
  (isLoading) => {
    if (pageLoadingTimer !== null) {
      window.clearInterval(pageLoadingTimer)
      pageLoadingTimer = null
    }
    if (!isLoading) return

    pageLoadingMessageIndex = 0
    const messagesByContext: Record<'switch' | 'generate', string[]> = {
      switch: [
        '正在切换图类型…',
        '正在理解默认描述文本…',
        '正在调用大模型生成模式图示…',
        '正在渲染 Mermaid…',
        '已经很努力在执行了，请稍等…',
      ],
      generate: [
        '正在生成图…',
        '正在调用大模型整理结构…',
        '正在生成 Mermaid 源码…',
        '正在渲染 SVG…',
        '已经很努力在执行了，请稍等…',
      ],
    }

    const getMessages = () => {
      const ctx = pageLoadingContext.value
      return ctx ? messagesByContext[ctx] : messagesByContext.generate
    }

    const msgs = getMessages()
    pageLoadingMessage.value = msgs[0] || '加载中…'

    pageLoadingTimer = window.setInterval(() => {
      const current = getMessages()
      if (!current.length) return
      pageLoadingMessageIndex = (pageLoadingMessageIndex + 1) % current.length
      pageLoadingMessage.value = current[pageLoadingMessageIndex] ?? '加载中…'
    }, 1200)
  },
  { immediate: true }
)

const diagramDefaultTextByType: Record<DiagramType, string> = {
  flow: '用户提交退款申请 -> 系统校验 -> 进入人工审核 -> 审核通过则发起打款 -> 更新退款状态 -> 通知用户',
  sequence: '用户在 App 下单并支付；订单系统调用库存系统锁定库存；支付系统回调订单系统确认支付；订单系统通知用户下单成功。',
  state: '一个订单从创建到完成：创建(待支付) -> 已支付 -> 已发货 -> 已完成；支付失败或超时进入已取消；退款进入已退款。',
}
let diagramTypeWatchInitialized = false

type ApplySampleOptions = {
  /** First render on page load: do not show fullscreen loading */
  initial?: boolean
  /** Previous diagram type, used to decide whether to auto-replace the text */
  prevType?: DiagramType
}

async function applyDiagramSample(type: DiagramType, options: ApplySampleOptions = {}) {
  diagramError.value = ''
  diagramLocalTimeSec.value = null

  // 切换图类型不自动生成：仅在合适时更新默认描述文本，并清空渲染结果。
  const nextDefault = diagramDefaultTextByType[type] || diagramDefaultTextByType.flow
  const prevType = options.prevType
  const prevDefault = prevType ? (diagramDefaultTextByType[prevType] || diagramDefaultTextByType.flow) : undefined

  const currentText = diagramText.value?.trim() || ''
  const shouldReplaceText =
    !currentText ||
    (prevDefault ? currentText === prevDefault.trim() : Boolean(options.initial))

  if (shouldReplaceText) {
    diagramText.value = nextDefault
  }

  diagramMermaid.value = ''
  diagramSvg.value = ''
  setLlmStepActive(7)
}

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
  startPageLoading('generate')
  setLlmStepActive(1)
  try {
    const payload = {
      diagram_type: diagramType.value,
      text: diagramText.value,
      scene: 'product',
    } as const

    if (diagramAsync.value) {
      setLlmStepActive(2)
      const submit = await submitDiagramTask(payload)
      setLlmStepActive(3)
      const status = await waitTask(submit.task_id)
      const result = (status.result ?? {}) as Record<string, unknown>
      if (status.state === 'FAILURE') {
        throw new Error(String(result.error ?? 'Task failed'))
      }
      setLlmStepActive(4)
      const mermaid = String(result.mermaid ?? '')
      diagramMermaid.value = mermaid
      setLlmStepActive(5)
      diagramSvg.value = mermaid ? await renderMermaid(`m-${Date.now()}`, mermaid) : ''
      setLlmStepActive(6)
    } else {
      setLlmStepActive(2)
      setLlmStepActive(3)
      const res = await generateDiagram(payload)
      setLlmStepActive(4)
      diagramMermaid.value = res.mermaid
      setLlmStepActive(5)
      diagramSvg.value = await renderMermaid(`m-${Date.now()}`, res.mermaid)
      setLlmStepActive(6)
    }

    diagramLocalTimeSec.value = (performance.now() - startedAt) / 1000
  } catch (e) {
    diagramError.value = e instanceof Error ? e.message : String(e)
  } finally {
    setLlmStepActive(7)
    diagramLoading.value = false
    stopPageLoading()
  }
}

watch(
  diagramType,
  (t, prev) => {
    const isInitial = !diagramTypeWatchInitialized
    diagramTypeWatchInitialized = true
    void applyDiagramSample(t, { initial: isInitial, prevType: prev })
  },
  { immediate: true }
)

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
  // Important: run after setup finished, otherwise applyTemplateSeed can hit TDZ
  // when diagramText/drawioGenText refs haven't been initialized yet.
  updateChart()
  statusPanelCollapsed.value = loadBoolFromStorage(STORAGE_KEYS.statusPanelCollapsed, false)
  await refreshLlmConfig()
  await refreshLlm()
  await refreshDb()
  llmModeAutoApplyEnabled = true

  // draw.io: load last diagram from storage, fallback to blank
  drawioXml.value = loadTextFromStorage(STORAGE_KEYS.drawioXml, drawioBlankXml)

  window.addEventListener('message', onDrawioMessage)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onDrawioMessage)
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
    <div v-show="pageLoading" class="el-loading-mask is-fullscreen">
      <div class="el-loading-spinner">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p class="el-loading-text">{{ pageLoadingMessage }}</p>
      </div>
    </div>
    <el-container style="height: 100vh">
      <el-header class="header">
        <div class="headerTop">
          <div class="brand">
            <div class="title">产品智绘官（Product Diagram Copilot）</div>
            <div class="subtitle">文本 → Diagram Spec/XML → Mermaid / drawio / 结算指标可视化</div>
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
            <el-button size="small" @click="() => { statusPanelOpen = !statusPanelOpen }">
              {{ statusPanelOpen ? '收起状态面板' : '状态面板' }}
            </el-button>
            <el-button size="small" @click="() => { logsOpen = !logsOpen }">
              {{ logsOpen ? '收起日志' : '日志' }}
            </el-button>
          </div>
        </div>

        <div class="selectorBar selectorBarInHeader">
          <div class="selectorTitle">业务配置</div>
          <el-select v-model="selectedBusinessId" size="small" style="width: 140px" placeholder="请选择业务">
            <el-option v-for="b in PDC_CONFIG.businesses" :key="b.businessId" :label="b.label" :value="b.businessId" />
          </el-select>

          <el-select
            v-model="selectedTemplateId"
            size="small"
            style="width: 180px"
            :disabled="templatesForBusiness.length === 0"
            placeholder="请选择模板"
          >
            <el-option v-for="t in templatesForBusiness" :key="t.templateId" :label="t.label" :value="t.templateId" />
          </el-select>

          <el-select
            v-model="selectedStrategyId"
            size="small"
            style="width: 180px"
            :disabled="strategiesForSelection.length === 0"
            placeholder="请选择策略"
          >
            <el-option v-for="s in strategiesForSelection" :key="s.strategyId" :label="s.label" :value="s.strategyId" />
          </el-select>
        </div>
      </el-header>

      <el-main class="main">
        <el-card v-if="logsOpen" class="mb" shadow="never">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px">
              <span>日志</span>
              <el-button size="small" @click="() => { logsOpen = false }">关闭</el-button>
            </div>
          </template>
          <LogPage />
        </el-card>

        <el-card v-if="statusPanelOpen" class="mb panel" shadow="never">
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
                  @click="() => { refreshDb(); refreshLlm(); }"
                >
                  刷新
                </el-button>
              </div>
            </div>
          </template>

          <div v-show="statusPanelCollapsed" class="statusStepsCollapsed">
            <el-steps
              :active="llmStepActive"
              align-center
              process-status="success"
              finish-status="success"
              class="steps steps--compact"
            >
              <el-step
                v-for="s in llmSteps"
                :key="`${s.title}::collapsed`"
                :title="s.title"
              />
            </el-steps>
          </div>

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
                  :active="llmStepActive"
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
          <el-tab-pane label="自动出图（mermaid）" name="diagram">
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
                    <el-input
                      v-model="diagramText"
                      type="textarea"
                      :rows="10"
                      placeholder="请输入描述文本"
                    />
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

          <el-tab-pane label="架构图（draw.io）" name="drawio">
            <el-card shadow="never" class="mb">
              <template #header>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap">
                  <span>嵌入式 draw.io 编辑器（diagrams.net）</span>
                  <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
                    <el-tag size="small" :type="drawioReady ? 'success' : 'warning'">
                      {{ drawioReady ? 'ready' : 'loading' }}
                    </el-tag>
                    <el-tag v-if="drawioStatus" size="small" type="info">{{ drawioStatus }}</el-tag>
                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="onDrawioSaveClick">
                      保存
                    </el-button>
                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="resetDrawioToMock">
                      重置示例
                    </el-button>

                    <label>
                      <input
                        type="file"
                        accept=".drawio,.xml"
                        style="display: none"
                        @change="onDrawioFileInputChange"
                      />
                      <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy">导入</el-button>
                    </label>

                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="exportDrawioXmlFile">
                      导出 .drawio
                    </el-button>
                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="() => exportDrawio('png')">
                      导出 PNG
                    </el-button>
                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="() => exportDrawio('pdf')">
                      导出 PDF
                    </el-button>
                    <el-button size="small" :disabled="!drawioReady" :loading="drawioBusy" @click="exportDrawioJson">
                      导出 JSON
                    </el-button>
                  </div>
                </div>
              </template>

              <el-alert
                v-if="drawioError"
                type="error"
                :title="drawioError"
                show-icon
                class="mb"
              />

              <el-alert
                type="info"
                title="说明：此编辑器通过 https://embed.diagrams.net 以 iframe 方式嵌入；需可访问外网。导出 PNG/PDF 在本地完成，JSON 为包含 draw.io XML 的封装格式。"
                show-icon
                :closable="false"
              />

              <el-form label-position="top" class="mt">
                <el-form-item label="前置步骤：描述 → 大模型 → draw.io XML">
                  <el-input
                    v-model="drawioGenText"
                    type="textarea"
                    :rows="4"
                    placeholder="例如：我们有 Web/H5、App、小程序；通过 API Gateway 进入用户/订单/消息服务；用 MySQL+Redis+Kafka；需要可观测性…"
                  />
                </el-form-item>
                <el-button
                  type="primary"
                  size="small"
                  :disabled="!drawioReady"
                  :loading="drawioGenLoading"
                  @click="onGenerateDrawioFromText"
                >
                  生成并载入
                </el-button>
              </el-form>
            </el-card>

            <iframe
              ref="drawioFrame"
              class="drawioFrame"
              :src="drawioEmbedUrl"
              title="draw.io editor"
              loading="lazy"
              referrerpolicy="no-referrer"
            />
          </el-tab-pane>


          <el-tab-pane label="大数据图（Echart）" name="settlement">
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

/* Page-level fullscreen loading overlay: force true center alignment */
.app :deep(.el-loading-mask.is-fullscreen) {
  position: fixed !important;
  inset: 0 !important;
  /* IMPORTANT: do NOT use display: ... !important here.
     v-show relies on inline display:none to hide this element. */
  display: flex;
  align-items: center !important;
  justify-content: center !important;
}

.app :deep(.el-loading-mask.is-fullscreen .el-loading-spinner) {
  position: static !important;
  top: auto !important;
  left: auto !important;
  right: auto !important;
  bottom: auto !important;
  transform: none !important;
  margin-top: 0 !important;
  text-align: center;
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
  height: auto;
  min-height: 56px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  box-shadow: var(--el-box-shadow-lighter);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 22px;
}

.headerTop {
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

.selectorBar {
  padding: 10px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: color-mix(in srgb, var(--el-fill-color-lighter) 65%, var(--el-bg-color));
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  box-shadow: var(--el-box-shadow-lighter);
  position: relative;
}

.selectorBarInHeader {
  padding: 0;
  border-bottom: none;
  background: transparent;
  box-shadow: none;
}

.selectorTitle {
  font-size: 14px;
  font-weight: 700;
  opacity: 0.95;
  white-space: nowrap;
  padding-left: 10px;
  position: relative;
}

.selectorTitle::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--el-color-primary);
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

.statusStepsCollapsed {
  margin-bottom: 8px;
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

.steps.steps--compact {
  margin-bottom: 0;
  padding: 6px 10px;
  min-height: 44px;
}

.steps.steps--compact :deep(.el-step__description) {
  display: none;
}

.steps.steps--compact :deep(.el-step__main) {
  padding-bottom: 0;
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

.drawioFrame {
  width: 100%;
  height: 720px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color);
}
</style>
