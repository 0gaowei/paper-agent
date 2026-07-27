export interface AcademicPaper {
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
  relevanceTier?: 'high' | 'partial' | 'low' | string
  rankingFactors?: RankingFactors
  evidenceSnippets?: EvidenceSnippet[]
  tags?: string[]
  provenance?: Provenance
  // Backend (paperqa.server.schemas.AcademicPaper) additional fields — accepted
  // when the API client surfaces raw payloads; normalize() in @/api converts
  // them to camelCase on the wire, but the optional snake_case forms are
  // tolerated for forward-compat with raw responses.
  s2Id?: string
  openalexId?: string
  citation_count?: number
  relevance_tier?: string
  referenced_works?: string[]
  citing_works?: string[]
  source?: string
  relevanceScore?: number
  url?: string
}

export type Paper = AcademicPaper

export interface QueryEntities {
  topics?: string[]
  methods?: string[]
  datasets?: string[]
  domains?: string[]
  [key: string]: string[] | undefined
}

export interface QueryUnderstanding {
  originalQuery?: string
  entities: string[] | QueryEntities
  intent: 'survey' | 'specific' | 'comparative' | 'methodology' | 'general' | 'current_state' | 'background' | 'domain' | string
  queryType?: string
  summary?: string
  // Backend fields (paperqa.server.schemas.QueryUnderstanding)
  domain?: string
  suitableSources?: string[]
  subqueries?: SubQuery[]
}

export interface SubQuery {
  id?: string
  query?: string
  text?: string
  type?: 'topic' | 'method' | 'dataset' | 'author' | 'venue' | string
  intent?: string
  resultCount?: number
  round?: number
}

export interface RankingFactors {
  relevance: number
  recency: number
  authority: number
  diversity: number
  [key: string]: number
}

export interface EvidenceSnippet {
  paperId?: string
  text: string
  score?: number
  query?: string
  intent?: string
  [key: string]: unknown
}

export interface Provenance {
  source?: string
  query?: string
  iteration?: number
  discoveredVia?: string
  [key: string]: unknown
}

export interface UsageStats {
  totalTokens?: number
  tokenUsage?: number
  inputTokens?: number
  outputTokens?: number
  apiCalls?: number
  cost?: number
  duration?: number
  dailyTrend?: Array<{ date: string; tokens?: number; cost?: number; calls?: number }>
  [key: string]: unknown
}

export interface SearchStats extends UsageStats {
  totalPapers: number
  relevantPapers: number
}

export interface ResearchSession {
  id: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'error' | 'cancelled' | 'done'
  understanding?: QueryUnderstanding
  subQueries: SubQuery[]
  papers: AcademicPaper[]
  stats: SearchStats
  usage?: UsageStats
  answerSummary?: string
  evidenceSnippets?: EvidenceSnippet[]
  graph?: GraphData
  provenance?: Provenance[] | Provenance
  createdAt: string
  completedAt?: string
  error?: string
  // Backend-tolerant fields (snake_case from paperqa.server.schemas.ResearchSession).
  // The API client normalizes to camelCase, but stores/views may receive raw
  // payloads when used outside the normal flow.
  created_at?: string
  updated_at?: string
  rounds?: number
  answer?: string
  evidence?: Record<string, EvidenceSnippet[]>
  stop_reason?: string
  error_message?: string
}

export type SearchSession = ResearchSession

export interface PipelineStep {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'error'
  description?: string
  result?: unknown
}

export interface SSEEvent {
  type: 'understanding' | 'subqueries' | 'round_started' | 'paper_found' | 'usage' | 'answer' | 'done' | 'error' | string
  sessionId?: string
  data?: unknown
  [key: string]: unknown
}

export interface FilterState {
  yearRange: [number, number]
  minRelevance: number
  sortBy: 'relevance' | 'date' | 'citations' | 'combined'
}

export interface Citation {
  sourceId: string
  targetId: string
  type: 'query' | 'citation' | 'cites' | 'citedBy'
}

export interface GraphNode {
  id: string
  title?: string
  label?: string
  type: 'center' | 'iteration' | 'ref' | 'reference' | 'citedBy' | 'paper' | 'subquery' | 'query' | string
  relevance?: number
  year?: number | null
  citationCount?: number
  relevanceTier?: string
  isRoot?: boolean
  source?: string | null
  round?: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphEdge {
  source: string | GraphNode
  target: string | GraphNode
  type: 'query' | 'citation' | 'cites' | 'citedBy' | 'spawned' | 'found' | 'references' | 'cited_by' | 'citation_expansion' | string
  round?: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  query?: string
  rounds?: number
}

export interface ApiConfig {
  provider: 'openai' | 'anthropic' | 'deepseek' | 'qwen' | string
  apiKey?: string
  configured?: boolean
  baseUrl?: string
  model?: string
}

export interface SearchConfig {
  enableQueryDecomposition?: boolean
  enableIterativeSearch?: boolean
  enableQueryRewrite?: boolean
  maxIterations?: number
  maxResults?: number
  [key: string]: unknown
}

export interface SessionCreateRequest {
  query: string
  config?: SearchConfig
}

export interface DataSourceConfig {
  name: string
  enabled: boolean
  priority: number
}

export interface HistoryRecord {
  id: string
  query: string
  sessionId?: string
  status?: string
  papersCount?: number
  paperCount?: number
  rounds?: number
  answerLength?: number
  duration: number
  cost: number
  createdAt: string
  updatedAt?: string
}
