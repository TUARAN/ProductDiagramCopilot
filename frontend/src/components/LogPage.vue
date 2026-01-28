<script setup lang="ts">
import { computed, ref } from 'vue'

type CodeBlock = {
  language: 'json' | 'text'
  content: string
}

type LogSection = {
  id: string
  title: string
  paragraphs?: string[]
  bullets?: string[]
  codeBlocks?: CodeBlock[]
}

type LogEntry = {
  id: string
  title: string
  date: string
  summary: string
  sections: LogSection[]
}

const entries: LogEntry[] = [
  {
    id: 'pdc-2026-01-28',
    title: '产品智绘官（Product Diagram Copilot）产品形态与主链路（v1）',
    date: '2026-01-28',
    summary:
      '把“描述给大模型 → 生成结构化图形代码（Mermaid / draw.io XML / Spec）→ 交给渲染工具 → 可编辑产物”的链路固化为可复用能力。',
    sections: [
      {
        id: '1',
        title: '（1）定位与入口',
        paragraphs: [
          '产品定位：一个“文本驱动出图”的工作台——用户只需描述需求，系统用大模型生成结构化图形代码，再交给对应渲染/编辑工具产出可交付的图。',
          '统一入口：围绕同一份“结构化中间产物（Diagram Spec / Mermaid code / draw.io XML）”组织生成、预览、编辑与导出。',
        ],
        bullets: [
          '输入：自然语言描述 / 结构化参数 /（可选）业务数据。',
          '输出：Mermaid（前端可直接渲染）/ draw.io XML（可编辑）/（可选）更通用的 Diagram Spec JSON。',
          '目标：默认提供经典模板，保证开箱即用与可编辑交付。',
        ],
      },
      {
        id: '2',
        title: '（2）端到端链路',
        paragraphs: [
          '核心思路：描述给大模型，大模型生成结构化代码（Mermaid 或 draw.io XML），再交给对应工具（Mermaid 渲染器 / draw.io 编辑器 / 指标可视化组件）完成展示与导出。',
          '平台价值：把“模板 + 结构化输出约束 + 校验 + 导出规格 + 可编辑性”做成默认能力，避免每个业务重复造轮子。',
        ],
        bullets: [
          'Step 1：用户输入文本（描述“画什么图、要哪些模块/关系、输出到哪里”）。',
          'Step 2：LLM 生成结构化产物（Mermaid code 或 draw.io XML；可选生成 Diagram Spec 作为中间层）。',
          'Step 3：渲染/编辑：Mermaid 直接渲染为 SVG；draw.io XML 载入嵌入式编辑器支持二次编辑。',
          'Step 4：导出：SVG/PNG/PDF/PPT（取决于渲染器与导出规格）。',
        ],
      },
      {
        id: '3',
        title: '（3）结构化输出形态（建议同时支持 3 种）',
        paragraphs: [
          '为了兼容不同渲染与编辑体验，建议将“结构化输出”拆成：Diagram Spec（平台中间层）+ Mermaid（轻量预览）+ draw.io XML（强编辑）。',
        ],
        codeBlocks: [
          {
            language: 'json',
            content: `{
  "version": "1.0.0",
  "kind": "diagram_spec",
  "graphType": "flow|sequence|state|architecture|metrics",
  "templateId": "classic.flow.v1",
  "rendererHint": "mermaid|drawio",
  "nodes": [
    { "id": "n1", "label": "开始", "type": "start" },
    { "id": "n2", "label": "结算计算", "type": "step" }
  ],
  "edges": [
    { "from": "n1", "to": "n2", "type": "sequence" }
  ],
  "groups": [
    { "id": "g1", "type": "swimlane", "label": "服务层", "members": ["n2"] }
  ],
  "meta": { "generatedBy": "llm", "editable": true }
}`,
          },
          {
            language: 'text',
            content: `flowchart LR
  A[开始] --> B[结算计算]
  B --> C[出账]
`,
          },
          {
            language: 'text',
            content: `<!-- draw.io XML 通常较长；这里仅示意结构（实际产物应为完整 mxfile） -->
<mxfile host="app.diagrams.net">
  <diagram name="Page-1">
    ...
  </diagram>
</mxfile>
`,
          },
        ],
      },
      {
        id: '4',
        title: '（4）默认模板与可编辑性（draw.io）',
        paragraphs: [
          '默认提供经典模板（流程/架构/数据流），LLM 在模板约束下生成结构化代码，减少“自由发挥”导致的不可控。',
          'draw.io 产物以 XML 形式加载到嵌入式编辑器，天然支持二次编辑与导出（PNG/PDF/.drawio）。',
        ],
        bullets: [
          '模板参数：graphType/templateId/输出目标（a4/ppt/svg_web）。',
          '可编辑保证：生成的 draw.io XML 必须是完整 mxfile，可在 diagrams.net 中直接打开。',
          '降级策略：draw.io 生成失败时回退到 Mermaid（保证至少能出 SVG）。',
        ],
      },
      {
        id: '5',
        title: '（5）结算指标可视化（属于“同入口的另一类产物”）',
        bullets: [
          '指标类产物不一定走 Mermaid/draw.io：可以用 ECharts 直接渲染（本项目已有）。',
          '关键是统一输入与可追溯：同一份“结算链路描述/数据”既能出流程图，也能出指标图表。',
          '导出：图表支持导出图片/截图或（后续）进入 PPT 导出链路。',
        ],
      },
      {
        id: '6',
        title: '（6）LLM 输出约束（保证可控与可编辑）',
        bullets: [
          '允许：生成 Mermaid / draw.io XML / Diagram Spec（必须是结构化输出）。',
          '要求：输出必须通过校验（例如 Mermaid 可解析、draw.io XML 可被编辑器 load）。',
          '可追溯：记录输入文本、模板、模型配置、输出代码、渲染结果与导出文件。',
        ],
      },
      {
        id: '7',
        title: '（7）验收点（可测试）',
        bullets: [
          'Mermaid：同一输入生成的 Mermaid 可渲染为 SVG；可下载 SVG。',
          'draw.io：生成的 XML 可加载到嵌入式编辑器并可保存/导出（PNG/PDF/.drawio）。',
          '模板：选择不同图类型/模板能稳定产出结构化代码，且用户可在生成后手工调整。',
          '指标图：结算指标图表能稳定渲染且与后端数据一致。',
        ],
      },
      {
        id: '8',
        title: '（8）风险与对策（贴近“LLM→结构化代码→工具”）',
        bullets: [
          'LLM 幻觉：通过模板约束 + 结构化校验 + 失败回退到更保守模板。',
          'draw.io XML 生成失败：回退 Mermaid（确保至少能交付 SVG）。',
          '编辑器外网依赖：无法访问 embed.diagrams.net 时仅保留 XML 导出与离线编辑提示。',
          '模板碎片化：沉淀“经典模板”，业务仅做少量参数覆盖。',
          '导出一致性：导出链路对同一份代码产物可重复（不引入随机布局）。',
        ],
      },
    ],
  },
]

const activeEntryId = ref(entries[0]?.id ?? '')
const activeEntry = computed(() => entries.find((e) => e.id === activeEntryId.value) ?? null)
</script>

<template>
  <div class="logPage">
    <el-card shadow="never" class="mb">
      <template #header>
        <div class="header">
          <div>
            <div class="title">方案日志</div>
            <div class="subtitle">用于评审与排期的结构化方案记录</div>
          </div>
          <el-select v-model="activeEntryId" style="min-width: 320px" placeholder="选择一条日志">
            <el-option v-for="e in entries" :key="e.id" :label="`${e.title}（${e.date}）`" :value="e.id" />
          </el-select>
        </div>
      </template>

      <el-alert
        v-if="activeEntry"
        type="info"
        :title="activeEntry.title"
        :description="`${activeEntry.date} · ${activeEntry.summary}`"
        show-icon
      />
    </el-card>

    <div v-if="activeEntry" class="sections">
      <el-card v-for="s in activeEntry.sections" :key="s.id" shadow="never" class="section">
        <template #header>
          <div class="sectionTitle">{{ s.title }}</div>
        </template>

        <div v-if="s.paragraphs" class="paragraphs">
          <p v-for="(p, idx) in s.paragraphs" :key="idx" class="p">{{ p }}</p>
        </div>

        <ul v-if="s.bullets" class="bullets">
          <li v-for="(b, idx) in s.bullets" :key="idx">{{ b }}</li>
        </ul>

        <div v-if="s.codeBlocks" class="codeBlocks">
          <div v-for="(cb, idx) in s.codeBlocks" :key="idx" class="codeBlock">
            <div class="codeMeta">{{ cb.language.toUpperCase() }}</div>
            <pre class="code"><code>{{ cb.content }}</code></pre>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-else description="暂无日志" />
  </div>
</template>

<style scoped>
.logPage {
  text-align: left;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.subtitle {
  font-size: 12px;
  opacity: 0.8;
}

.section {
  margin-top: 12px;
}

.sectionTitle {
  font-weight: 600;
}

.p {
  margin: 0 0 8px 0;
}

.bullets {
  margin: 0;
  padding-left: 18px;
}

.codeBlocks {
  margin-top: 10px;
}

.codeBlock {
  margin-top: 10px;
}

.codeMeta {
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 6px;
}

.code {
  margin: 0;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color);
  overflow: auto;
  font-size: 12px;
  line-height: 1.4;
}
</style>
