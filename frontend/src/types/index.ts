// 论文类型
export interface Paper {
  id: string
  title: string
  authors: string[]
  year: number
  journal?: string
  venue?: string
  abstract?: string
  doi?: string
  citationCount?: number
  isOpenAccess?: boolean
  pdfUrl?: string
  semanticScholarUrl?: string
  relevance?: number
  tags?: string[]
}

// 查询理解结果
export interface QueryUnderstanding {
  originalQuery: string
  entities: {
    topics: string[]
    methods: string[]
    datasets: string[]
    domains: string[]
  }
  intent: 'survey' | 'specific' | 'comparative' | 'methodology'
  queryType: string
}

// 子查询
export interface SubQuery {
  id: string
  query: string
  type: 'topic' | 'method' | 'dataset' | 'author' | 'venue'
}

// 搜索管道步骤
export interface PipelineStep {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'error'
  description?: string
  result?: any
}

// 搜索统计
export interface SearchStats {
  totalPapers: number
  relevantPapers: number
  apiCalls: number
  tokenUsage: number
  cost: number
  duration: number
}

// 搜索会话
export interface SearchSession {
  id: string
  query: string
  status: 'running' | 'completed' | 'error'
  understanding?: QueryUnderstanding
  subQueries: SubQuery[]
  papers: Paper[]
  stats: SearchStats
  createdAt: string
  completedAt?: string
}

// 筛选状态
export interface FilterState {
  yearRange: [number, number]
  minRelevance: number
  sortBy: 'relevance' | 'date' | 'citations' | 'combined'
}

// 排序因素
export interface RankingFactors {
  relevance: number
  recency: number
  authority: number
  diversity: number
}

// 引用关系
export interface Citation {
  sourceId: string
  targetId: string
  type: 'reference' | 'citedBy'
}

// 图谱节点
export interface GraphNode {
  id: string
  title: string
  type: 'center' | 'reference' | 'citedBy'
  relevance?: number
  year?: number
  citationCount?: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

// 图谱边
export interface GraphEdge {
  source: string | GraphNode
  target: string | GraphNode
  type: 'cites' | 'citedBy'
}

// 图谱数据
export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// 设置配置
export interface ApiConfig {
  provider: 'openai' | 'anthropic' | 'deepseek' | 'qwen'
  apiKey: string
  baseUrl?: string
  model: string
}

export interface SearchConfig {
  enableQueryDecomposition: boolean
  enableIterativeSearch: boolean
  enableQueryRewrite: boolean
  maxIterations: number
  maxResults: number
}

export interface DataSourceConfig {
  name: string
  enabled: boolean
  priority: number
}

// 历史记录
export interface HistoryRecord {
  id: string
  query: string
  sessionId: string
  paperCount: number
  duration: number
  cost: number
  createdAt: string
}
