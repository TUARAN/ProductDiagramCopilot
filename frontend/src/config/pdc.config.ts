export type StrategyId =
  | 'mermaid.svg.web.v1'
  | 'drawio.editable.v1'
  | 'settlement.echarts.dashboard.v1'

export type OutputProfileId = 'web'

export type BusinessId = 'settlement' | 'yuexin_integration' | 'general_report'

export type TemplateGraphType =
  | 'flow'
  | 'sequence'
  | 'state'
  | 'architecture'
  | 'metrics'

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
      businessId: 'yuexin_integration',
      label: '阅信产品对接',
      defaults: {
        templateId: 'yuexin.integration.flow.v1',
        strategyId: 'mermaid.svg.web.v1',
        outputProfileId: 'web',
      },
      enabledTemplates: [
        'yuexin.integration.flow.v1',
        'yuexin.integration.sequence.v1',
        'yuexin.integration.state.v1',
      ],
      enabledStrategies: ['mermaid.svg.web.v1'],
    },
    {
      businessId: 'settlement',
      label: '阅信结算趋势',
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
      businessId: 'general_report',
      label: '通用业务汇报',
      defaults: {
        templateId: 'general.arch.system.v1',
        strategyId: 'drawio.editable.v1',
        outputProfileId: 'web',
      },
      enabledTemplates: ['general.arch.system.v1'],
      enabledStrategies: ['drawio.editable.v1'],
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
      label: '结算指标 → ECharts',
      pipelineKind: 'settlement_echarts',
      llmOutputFormat: 'none',
      exports: [],
    },
  ],
  templates: [
    {
      templateId: 'general.arch.system.v1',
      businessId: 'general_report',
      label: '系统架构图',
      graphType: 'architecture',
      recommendedStrategyIds: ['drawio.editable.v1'],
      promptTemplateId: 'drawio.arch.v1',
      constraints: {
        layers: ['客户端', '网关/接入层', '服务层', '数据层', '可观测'],
      },
      exampleInputs: [
        '请生成一个“通用业务汇报”的系统架构图：包含客户端/网关/核心服务/依赖服务/数据存储/监控告警，并输出可编辑的 draw.io XML。',
      ],
    },
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
      templateId: 'yuexin.integration.flow.v1',
      businessId: 'yuexin_integration',
      label: '对接流程图（业务流程）',
      graphType: 'flow',
      recommendedStrategyIds: ['mermaid.svg.web.v1'],
      promptTemplateId: 'mermaid.flow.v1',
      constraints: {
        mustHave: ['鉴权', '查询', '回调', '对账'],
      },
      exampleInputs: ['请生成“阅信产品对接”的流程图：申请接入→鉴权→查询接口→回调通知→对账/补单→完成。'],
    },
    {
      templateId: 'yuexin.integration.sequence.v1',
      businessId: 'yuexin_integration',
      label: '对接时序图（系统交互）',
      graphType: 'sequence',
      recommendedStrategyIds: ['mermaid.svg.web.v1'],
      promptTemplateId: 'mermaid.flow.v1',
      constraints: {
        participants: ['调用方', '阅信网关', '阅信服务', '回调接收方'],
      },
      exampleInputs: ['请生成“阅信产品对接”的时序图：调用方→阅信网关鉴权→阅信服务查询→返回结果；异步回调通知；对账与重试。'],
    },
    {
      templateId: 'yuexin.integration.state.v1',
      businessId: 'yuexin_integration',
      label: '对接状态图（单据/任务状态）',
      graphType: 'state',
      recommendedStrategyIds: ['mermaid.svg.web.v1'],
      promptTemplateId: 'mermaid.flow.v1',
      constraints: {
        mustHave: ['待鉴权', '已鉴权', '处理中', '成功', '失败', '重试中'],
      },
      exampleInputs: ['请生成“阅信产品对接”的状态图：待鉴权→已鉴权→处理中→成功；失败→重试中→处理中；终态含失败/成功。'],
    },
  ],
  outputProfiles: [{ outputProfileId: 'web', label: 'Web 默认' }],
} as const
