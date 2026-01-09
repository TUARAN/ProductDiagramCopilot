<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

import {
  generateDiagram,
  generateIntegration,
  getArtifact,
  getTaskStatus,
  llmPing,
  listArtifacts,
  settlementMetrics,
  submitDiagramTask,
  submitIntegrationTask,
  type DiagramType,
  type ArtifactOut,
  type LlmPingResponse,
} from './lib/api'
import { renderMermaid } from './lib/mermaid'

const activeTab = ref<'diagram' | 'integration' | 'settlement' | 'artifacts'>('diagram')

// LLM status (visualize where we call API / local model)
const llmLoading = ref(false)
const llmError = ref('')
const llm = ref<LlmPingResponse | null>(null)

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

const llmSteps = computed(() => {
  const mode = llm.value?.mode || 'unknown'
  const provider = llm.value?.provider || 'provider'
  const model = llm.value?.model
  const baseUrl = llm.value?.base_url

  const llmNode = model ? `${provider} (${model})` : provider
  const upstream =
    mode === 'openai_compat'
      ? `外部 API: ${baseUrl || 'OPENAI_COMPAT_BASE_URL'}`
      : mode === 'ollama'
        ? `本地模型: ${baseUrl || 'OLLAMA_BASE_URL'}`
        : mode === 'mock'
          ? 'Mock（不出网）'
          : '未识别'

  return [
    '前端点击生成',
    '后端 API',
    llmNode,
    upstream,
    '结构化 Spec JSON',
    'Mermaid 渲染',
    '前端 SVG',
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
  diagramError.value = ''
  diagramSvg.value = ''
  diagramMermaid.value = ''
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
      const mermaid = String(result.mermaid ?? '')
      diagramMermaid.value = mermaid
      diagramSvg.value = mermaid ? await renderMermaid(`m-${Date.now()}`, mermaid) : ''
    } else {
      const res = await generateDiagram(payload)
      diagramMermaid.value = res.mermaid
      diagramSvg.value = await renderMermaid(`m-${Date.now()}`, res.mermaid)
    }
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

onMounted(() => {
  updateChart()
  refreshLlm()
})

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
          <el-tag size="small" :type="llm?.ok ? 'success' : 'warning'">
            LLM: {{ llm?.mode || 'unknown' }}
          </el-tag>
          <el-tag size="small" type="info">Model: {{ llm?.model || '-' }}</el-tag>
          <el-tag size="small" type="info">Latency: {{ llm?.latency_ms ?? '-' }}ms</el-tag>
          <el-button size="small" :loading="llmLoading" @click="refreshLlm">刷新</el-button>
        </div>
      </el-header>

      <el-main class="main">
        <el-card class="mb panel" shadow="never">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span>LLM 调用状态 & 可选组件</span>
              <el-button size="small" :loading="llmLoading" @click="refreshLlm">刷新</el-button>
            </div>
          </template>

          <el-alert
            v-if="llmError"
            type="error"
            :title="llmError"
            show-icon
            class="mb"
          />

          <el-row :gutter="16">
            <el-col :span="10">
              <el-descriptions :column="1" border>
                <el-descriptions-item label="当前模式">
                  <el-tag v-if="llm" :type="llm.ok ? 'success' : 'danger'">{{ llm.mode }}</el-tag>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="Provider">
                  <span v-if="llm">{{ llm.provider }}</span>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="Model">
                  <span v-if="llm">{{ llm.model || '-' }}</span>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="Base URL">
                  <span v-if="llm">{{ llm.base_url || '-' }}</span>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="延迟">
                  <span v-if="llm">{{ llm.latency_ms ?? '-' }} ms</span>
                  <span v-else>-</span>
                </el-descriptions-item>
              </el-descriptions>

              <el-alert
                class="mt"
                type="info"
                title="如何切换到本地模型（Ollama）"
                :closable="false"
                show-icon
              >
                <div>
                  1) 安装并启动 Ollama（默认地址 http://localhost:11434）<br />
                  2) 在 .env 中设置：LLM_MODE=ollama，OLLAMA_MODEL=qwen2.5:7b（或你的模型）<br />
                  3) 重启后端，再点「刷新」即可看到模式变化
                </div>
              </el-alert>
            </el-col>

            <el-col :span="14">
              <el-steps :active="llmSteps.length" align-center finish-status="success" class="steps">
                <el-step v-for="s in llmSteps" :key="s" :title="s" />
              </el-steps>

              <el-table :data="featureMatrix" size="small" border style="width: 100%">
                <el-table-column prop="feature" label="功能" width="170" />
                <el-table-column prop="llm" label="调用大模型" width="90" />
                <el-table-column prop="api" label="后端 API" />
                <el-table-column prop="optional" label="可选依赖/组件" width="240" />
              </el-table>
            </el-col>
          </el-row>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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
  max-width: 1280px;
  margin: 0 auto;
}

.panel {
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
  padding: 8px 8px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color);
  overflow-x: auto;
}

.mermaid :deep(svg) {
  max-width: 100%;
  height: auto;
}
</style>
