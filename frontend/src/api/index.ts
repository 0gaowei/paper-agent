import axios from 'axios'
import type {
  AcademicPaper,
  ApiConfig,
  DataSourceConfig,
  GraphData,
  HistoryRecord,
  ResearchSession,
  SearchConfig,
  SessionCreateRequest,
  SSEEvent,
  UsageStats
} from '@/types'

const client = axios.create({ baseURL: '/api', headers: { 'Content-Type': 'application/json' } })

function unwrap<T>(response: { data: T }): T {
  return response.data
}

// Backend (paperqa.server) returns snake_case; the rest of the app
// expects camelCase. We convert at the network boundary so downstream
// stores/views can stay typed.
const SNAKE_TO_CAMEL_KEYS = new Set<string>([
  's2_id', 'openalex_id', 'citation_count', 'relevance_tier',
  'referenced_works', 'citing_works', 'created_at', 'updated_at',
  'stop_reason', 'error_message', 'total_tokens', 'prompt_tokens',
  'completion_tokens', 'total_cost', 'llm_calls', 'search_calls',
  'researcher_llm', 'researcher_llm_config', 'summary_llm',
  'max_rounds', 'candidates_per_round', 'citation_expansion_limit',
  'high_relevance_threshold', 'partial_relevance_threshold',
  'llm_configured', 's2_configured', 'openalex_configured',
  'papers_count', 'answer_length', 'answer_summary', 'subqueries',
  'relevance_score', 'round_started', 'paper_found', 'events_emitted',
])

function toCamelKey(key: string): string {
  if (!SNAKE_TO_CAMEL_KEYS.has(key)) return key
  return key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase())
}

function normalize<T = unknown>(value: T): T {
  if (Array.isArray(value)) {
    return (value as unknown[]).map(v => normalize(v)) as unknown as T
  }
  if (value && typeof value === 'object' && (value as object).constructor === Object) {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[toCamelKey(k)] = normalize(v)
    }
    return out as T
  }
  return value
}

interface CreateSessionResponse {
  id: string
}

interface SessionEnvelope {
  session: ResearchSession
  papers: AcademicPaper[]
  eventsEmitted: number
}

const EVENT_TYPES = [
  'understanding',
  'subqueries',
  'round_started',
  'paper_found',
  'citation_expanded',
  'partial_documents',
  'answer',
  'usage',
  'done',
  'error',
  'cancelled'
] as const

export async function createSession(query: string, config?: SearchConfig): Promise<ResearchSession> {
  const body: SessionCreateRequest = { query, ...(config ? { config } : {}) }
  const response = unwrap(await client.post<CreateSessionResponse>('/sessions', body))
  // Backend only returns {id}; construct a minimal session so the store
  // can update it as SSE events arrive.
  return normalize({
    id: response.id,
    query,
    status: 'pending',
    subQueries: [],
    papers: [],
    stats: { totalPapers: 0, relevantPapers: 0 },
    createdAt: new Date().toISOString()
  } as ResearchSession)
}

export async function getSession(sessionId: string): Promise<ResearchSession> {
  // Backend returns {session, papers, events_emitted}; collapse to a
  // single ResearchSession shape the stores expect.
  const envelope = unwrap(await client.get<SessionEnvelope>(`/sessions/${encodeURIComponent(sessionId)}`))
  return normalize({ ...envelope.session, papers: envelope.papers } as ResearchSession)
}

export function onSessionEvent(
  sessionId: string,
  callback: (event: SSEEvent) => void,
  onError?: (error: Event | unknown) => void
): EventSource {
  // Native EventSource is required; use an EventSource polyfill for older browsers if needed.
  if (typeof EventSource === 'undefined') {
    throw new Error('当前浏览器不支持 EventSource，请安装 SSE polyfill')
  }
  const source = new EventSource(`/api/sessions/${encodeURIComponent(sessionId)}/events`)
  const dispatch = (type: string, raw: string) => {
    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      const event: SSEEvent = { type, ...normalize(parsed) } as SSEEvent
      callback(event)
    } catch (error) {
      onError?.(error)
    }
  }
  // Backend emits named events (event: understanding\ndata: {...});
  // onmessage would not match them, so register per-type listeners.
  for (const type of EVENT_TYPES) {
    source.addEventListener(type, (message: MessageEvent) => dispatch(type, message.data))
  }
  source.onerror = (error) => onError?.(error)
  return source
}

export function cancelSearchSubscription(subscription?: EventSource | null): void {
  subscription?.close()
}

export async function cancelSession(sessionId: string): Promise<{ id: string; status: string }> {
  return unwrap(await client.post<{ id: string; status: string }>(`/sessions/${encodeURIComponent(sessionId)}/cancel`))
}

export async function getPaperDetail(paperId: string): Promise<AcademicPaper | null> {
  try {
    return normalize(unwrap(await client.get<AcademicPaper>(`/papers/${encodeURIComponent(paperId)}`)))
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null
    return null
  }
}

export async function getPaperGraph(paperId: string): Promise<GraphData> {
  return normalize(unwrap(await client.get<GraphData>(`/papers/${encodeURIComponent(paperId)}/graph`)))
}

export async function getSessionGraph(sessionId: string): Promise<GraphData> {
  return normalize(unwrap(await client.get<GraphData>(`/sessions/${encodeURIComponent(sessionId)}/graph`)))
}

export const getCitationGraph = getSessionGraph

export async function getRelatedPapers(paperId: string): Promise<AcademicPaper[]> {
  // Backend does not currently expose /papers/{id}/related. The PaperDetail
  // view still uses this call, so we surface an empty list rather than 404.
  try {
    const response = await client.get<AcademicPaper[]>(`/papers/${encodeURIComponent(paperId)}/related`)
    return normalize(unwrap(response))
  } catch {
    return []
  }
}

export async function getSearchHistory(): Promise<HistoryRecord[]> {
  return normalize(unwrap(await client.get<HistoryRecord[]>('/history')))
}

export async function deleteHistoryRecord(id: string): Promise<void> {
  await client.delete(`/history/${encodeURIComponent(id)}`)
}

export interface SettingsResponse {
  apiConfig: ApiConfig
  searchConfig: SearchConfig
  dataSources: DataSourceConfig[]
}

export async function getSettings(): Promise<SettingsResponse> {
  // Backend returns the new SettingsPayload shape (researcher_llm,
  // max_rounds, thresholds, key status booleans). Map it to the legacy
  // shape used by the settings store.
  const raw = unwrap(await client.get<Record<string, unknown>>('/settings'))
  return normalize({
    apiConfig: {
      provider: 'openai',
      model: (raw.researcher_llm as string) ?? undefined,
      baseUrl: undefined,
      configured: Boolean(raw.llm_configured)
    } as ApiConfig,
    searchConfig: {
      enableQueryDecomposition: true,
      enableIterativeSearch: true,
      enableQueryRewrite: false,
      maxIterations: (raw.max_rounds as number) ?? 3,
      maxResults: (raw.candidates_per_round as number) ?? 10
    } as SearchConfig,
    dataSources: [] as DataSourceConfig[]
  })
}

export async function saveSettings(settings: SettingsResponse): Promise<SettingsResponse> {
  const raw = unwrap(await client.put<Record<string, unknown>>('/settings', {
    researcher_llm: settings.apiConfig.model,
    max_rounds: settings.searchConfig.maxIterations,
    candidates_per_round: settings.searchConfig.maxResults
  }))
  return normalize(raw as unknown as SettingsResponse)
}

export async function getUsage(): Promise<UsageStats> {
  return normalize(unwrap(await client.get<UsageStats>('/usage')))
}

export { client, normalize }
