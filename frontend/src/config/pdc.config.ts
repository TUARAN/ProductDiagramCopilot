export type StrategyId =
  | 'mermaid.svg.web.v1'
  | 'drawio.editable.v1'
  | 'settlement.echarts.dashboard.v1'

export type OutputProfileId = 'web'

export type BusinessId = 'settlement' | 'cpc_streaming'

export type TemplateGraphType = 'flow' | 'architecture' | 'metrics' | 'dataflow' | 'attribution'

export type PdcBusiness = {
  businessId: BusinessId
  label: string
  defaults: {
    templateId: string
    strategyId: StrategyId
    outputProfileId: OutputProfileId
  }
  enabledTemplates: string[]
  enabledStrategies: StrategyId[]
}

export type PdcStrategy = {
  strategyId: StrategyId
  label: string
  pipelineKind: 'mermaid_svg_web' | 'drawio_editable' | 'settlement_echarts'
  llmOutputFormat: 'mermaid' | 'drawio_xml' | 'none'
  exports: Array<'svg' | 'png' | 'pdf' | 'drawio'>
}

export type PdcTemplate = {
  templateId: string
  businessId: BusinessId
  label: string
  graphType: TemplateGraphType
  recommendedStrategyIds: StrategyId[]
  promptTemplateId: string | null
  constraints?: Record<string, unknown>
  exampleInputs: string[]
}

export type PdcOutputProfile = {
  outputProfileId: OutputProfileId
  label: string
}

export type PdcConfig = {
  version: string
  businesses: PdcBusiness[]
  strategies: PdcStrategy[]
  templates: PdcTemplate[]
  outputProfiles: PdcOutputProfile[]
}

export const PDC_CONFIG: PdcConfig = {
  version: '1.0.0',
  businesses: [
    {
      businessId: 'settlement',
      label: '阅信结算链路复盘',
      defaults: {
        templateId: 'settlement.flow.replay.v1',
        strategyId: 'mermaid.svg.web.v1',
        outputProfileId: 'web',
      },
      enabledTemplates: [
        'settlement.flow.replay.v1',
        'settlement.arch.system.v1',
        'settlement.metrics.dashboard.v1',
      ],
      enabledStrategies: [
        'mermaid.svg.web.v1',
        'drawio.editable.v1',
        'settlement.echarts.dashboard.v1',
      ],
    },
    {
      businessId: 'cpc_streaming',
      label: 'CPC 推流链路',
      defaults: {
        templateId: 'cpc.dataflow.streaming.v1',
        strategyId: 'drawio.editable.v1',
        outputProfileId: 'web',
      },
      enabledTemplates: ['cpc.dataflow.streaming.v1', 'cpc.attribution.chain.v1'],
      enabledStrategies: ['mermaid.svg.web.v1', 'drawio.editable.v1'],
    },
  ],
  strategies: [
    {
      strategyId: 'mermaid.svg.web.v1',
      label: 'Mermaid → SVG（网页嵌入）',
      pipelineKind: 'mermaid_svg_web',
      llmOutputFormat: 'mermaid',
      exports: ['svg'],
    },
    {
      strategyId: 'drawio.editable.v1',
      label: 'draw.io XML → 编辑器（可编辑交付）',
      pipelineKind: 'drawio_editable',
      llmOutputFormat: 'drawio_xml',
      exports: ['drawio', 'png', 'pdf'],
    },
    {
      strategyId: 'settlement.echarts.dashboard.v1',
      label: '结算指标 → ECharts（不走 LLM）',
      pipelineKind: 'settlement_echarts',
      llmOutputFormat: 'none',
      exports: [],
    },
  ],
  templates: [
    {
      templateId: 'settlement.flow.replay.v1',
      businessId: 'settlement',
      label: '结算流程图（复盘）',
      graphType: 'flow',
      recommendedStrategyIds: ['mermaid.svg.web.v1'],
      promptTemplateId: 'mermaid.flow.v1',
      constraints: {
        mustHave: ['开始', '对账', '结算', '出账'],
        naming: '中文短语，动宾结构优先',
      },
      exampleInputs: ['请生成结算链路复盘流程图：从数据入湖→对账→结算→出账→通知。'],
    },
    {
      templateId: 'settlement.arch.system.v1',
      businessId: 'settlement',
      label: '结算系统架构图（可编辑）',
      graphType: 'architecture',
      recommendedStrategyIds: ['drawio.editable.v1'],
      promptTemplateId: 'drawio.arch.v1',
      constraints: {
        layers: ['应用层', '服务层', '数据层'],
        mustHave: ['结算服务', '对账服务', '账务库'],
      },
      exampleInputs: ['请生成结算系统架构图，按应用/服务/数据三层分组，并输出可编辑的 draw.io XML。'],
    },
    {
      templateId: 'settlement.metrics.dashboard.v1',
      businessId: 'settlement',
      label: '结算指标看板',
      graphType: 'metrics',
      recommendedStrategyIds: ['settlement.echarts.dashboard.v1'],
      promptTemplateId: null,
      constraints: {
        metrics: ['total_amount', 'success_rate', 'latency_p95', 'error_count'],
      },
      exampleInputs: [],
    },

    {
      templateId: 'cpc.dataflow.streaming.v1',
      businessId: 'cpc_streaming',
      label: '推流数据流图（可编辑）',
      graphType: 'dataflow',
      recommendedStrategyIds: ['drawio.editable.v1'],
      promptTemplateId: 'drawio.dataflow.v1',
      constraints: {
        mustHave: ['采集', '聚合', '清洗', '投放', '监控'],
      },
      exampleInputs: ['请生成 CPC 推流链路数据流图：采集→聚合→清洗→投放→监控，输出可编辑的 draw.io XML。'],
    },
    {
      templateId: 'cpc.attribution.chain.v1',
      businessId: 'cpc_streaming',
      label: '归因链路图（网页嵌入）',
      graphType: 'attribution',
      recommendedStrategyIds: ['mermaid.svg.web.v1'],
      promptTemplateId: 'mermaid.flow.v1',
      constraints: {
        mustHave: ['曝光', '点击', '转化', '回传'],
      },
      exampleInputs: ['请生成 CPC 归因链路流程：曝光→点击→转化→回传，输出 Mermaid。'],
    },
  ],
  outputProfiles: [{ outputProfileId: 'web', label: 'Web 默认' }],
} as const
