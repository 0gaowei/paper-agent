import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ResearchSession, PipelineStep, QueryUnderstanding, SearchConfig, SubQuery, AcademicPaper, UsageStats, SSEEvent } from '@/types'
import { cancelSearchSubscription, cancelSession, createSession, getSession, onSessionEvent } from '@/api'
import { usePapersStore } from './papers'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const session = ref<ResearchSession | null>(null)
  const isSearching = ref(false)
  const pipeline = ref<PipelineStep[]>([
    { id: '1', name: '查询理解', status: 'pending', description: '分析用户查询意图和实体' },
    { id: '2', name: '子查询分解', status: 'pending', description: '将复杂查询拆分为多个子查询' },
    { id: '3', name: '多策略检索', status: 'pending', description: '并行执行多个检索策略' },
    { id: '4', name: '综合排序', status: 'pending', description: '融合多源结果并进行排序' }
  ])
  let eventSource: EventSource | null = null
  let activeSessionId: string | null = null

  const hasResults = computed(() => Boolean(session.value?.papers.length))
  const resultCount = computed(() => session.value?.papers.length || 0)

  function resetPipeline() {
    pipeline.value = pipeline.value.map(step => ({ ...step, status: 'pending', result: undefined }))
  }

  function setStep(id: string, status: PipelineStep['status'], result?: unknown) {
    const step = pipeline.value.find(item => item.id === id)
    if (step) {
      step.status = status
      if (result !== undefined) step.result = result
    }
  }

  function payload(event: SSEEvent): unknown {
    return event.data ?? event
  }

  function applyEvent(event: SSEEvent) {
    const data = payload(event) as Record<string, unknown>
    switch (event.type) {
      case 'understanding':
        session.value!.understanding = data as unknown as QueryUnderstanding
        setStep('1', 'completed', data)
        setStep('2', 'running')
        break
      case 'subqueries': {
        const items = (Array.isArray(data) ? data : data.subqueries) as SubQuery[] | undefined
        if (items) session.value!.subQueries = items
        setStep('2', 'completed', items || data)
        setStep('3', 'running')
        break
      }
      case 'round_started':
        setStep('3', 'running', data)
        break
      case 'paper_found': {
        const papers = (Array.isArray(data) ? data : data.papers) as AcademicPaper[] | undefined
        if (papers?.length) {
          session.value!.papers.push(...papers.filter(p => !session.value!.papers.some(existing => existing.id === p.id)))
          usePapersStore().addPapers(papers)
        } else if (data.id) {
          const paper = data as unknown as AcademicPaper
          session.value!.papers.push(paper)
          usePapersStore().addPapers([paper])
        }
        setStep('3', 'running', { count: session.value!.papers.length })
        break
      }
      case 'usage': {
        const u = data as UsageStats & { totalTokens?: number; totalCost?: number; llmCalls?: number; searchCalls?: number; total_tokens?: number; total_cost?: number; llm_calls?: number; search_calls?: number }
        session.value!.usage = u as UsageStats
        const totalTokens = u.totalTokens ?? (u as { total_tokens?: number }).total_tokens ?? 0
        const totalCost = u.totalCost ?? (u as { total_cost?: number }).total_cost ?? 0
        const llmCalls = u.llmCalls ?? (u as { llm_calls?: number }).llm_calls ?? 0
        const searchCalls = u.searchCalls ?? (u as { search_calls?: number }).search_calls ?? 0
        session.value!.stats = {
          ...session.value!.stats,
          apiCalls: llmCalls + searchCalls,
          cost: totalCost,
          tokenUsage: totalTokens,
          totalTokens,
        }
        break
      }
      case 'partial_documents':
        setStep('3', 'running', { count: session.value!.papers.length })
        break
      case 'citation_expanded':
        setStep('3', 'running', { count: session.value!.papers.length })
        break
      case 'cancelled':
        session.value!.status = 'cancelled'
        session.value!.completedAt = new Date().toISOString()
        isSearching.value = false
        cancelSearchSubscription(eventSource)
        eventSource = null
        break
      case 'answer':
        session.value!.answerSummary = String((data as { answer?: string; answerSummary?: string }).answerSummary
          ?? (data as { answer?: string }).answer
          ?? '')
        setStep('4', 'completed', data)
        break
      case 'done': {
        if (session.value!.status !== 'error') {
          session.value!.status = 'completed'
        }
        session.value!.completedAt = new Date().toISOString()
        const doneData = data as {
          papersCount?: number; papers_count?: number; rounds?: number;
          relevant_papers?: number; relevantPapers?: number;
          total_tokens?: number; totalTokens?: number;
          prompt_tokens?: number; promptTokens?: number;
          completion_tokens?: number; completionTokens?: number;
          total_cost?: number; totalCost?: number;
          llm_calls?: number; llmCalls?: number;
          search_calls?: number; searchCalls?: number;
        }
        const totalPapers = doneData.papersCount ?? doneData.papers_count ?? session.value!.papers.length
        const relevantPapers = doneData.relevant_papers ?? doneData.relevantPapers
          ?? session.value!.papers.filter(p => p.relevanceTier === 'high' || p.relevanceTier === 'partial').length
        const totalTokens = doneData.total_tokens ?? doneData.totalTokens ?? 0
        const totalCost = doneData.total_cost ?? doneData.totalCost ?? 0
        const llmCalls = doneData.llm_calls ?? doneData.llmCalls ?? 0
        const searchCalls = doneData.search_calls ?? doneData.searchCalls ?? 0
        session.value!.stats = {
          ...session.value!.stats,
          totalPapers,
          relevantPapers,
          apiCalls: llmCalls + searchCalls,
          cost: totalCost,
          tokenUsage: totalTokens,
        }
        setStep('3', 'completed', { count: totalPapers })
        setStep('4', 'completed', data)
        isSearching.value = false
        cancelSearchSubscription(eventSource)
        eventSource = null
        // SSE done event may arrive before buffered flush completes.
        // Refetch the session via HTTP to guarantee the latest stats.
        getSession(session.value!.id).then(restored => {
          session.value!.stats = {
            totalPapers: session.value!.papers.length,
            relevantPapers: session.value!.papers.filter(p => p.relevanceTier === 'high' || p.relevanceTier === 'partial').length,
            apiCalls: (restored.usage?.llmCalls ?? 0) + (restored.usage?.searchCalls ?? 0),
            cost: restored.usage?.totalCost ?? 0,
            tokenUsage: restored.usage?.totalTokens ?? 0,
          }
        }).catch(() => undefined)
        break
      }
      case 'error':
        const errorMsg = String((data as { error?: string }).error ?? (data as { message?: string }).message ?? event.error ?? '搜索失败')
        session.value!.status = 'error'
        session.value!.error = errorMsg
        pipeline.value.forEach(step => { if (step.status === 'running') step.status = 'error' })
        isSearching.value = false
        cancelSearchSubscription(eventSource)
        eventSource = null
        break
    }
  }

  function startSearch(searchQuery: string, config?: SearchConfig): { promise: Promise<ResearchSession>; cancel: () => void } {
    query.value = searchQuery
    resetPipeline()
    isSearching.value = true
    const promise = createSession(searchQuery, config).then(created => {
      session.value = { ...created, subQueries: created.subQueries || [], papers: created.papers || [], stats: created.stats || { totalPapers: 0, relevantPapers: 0 } }
      activeSessionId = created.id
      setStep('1', 'running')
      eventSource = onSessionEvent(created.id, applyEvent, () => {
        if (session.value?.status === 'running' || session.value?.status === 'pending') {
          getSession(created.id).then(value => { session.value = value }).catch(() => undefined)
        }
      })
      return session.value
    }).catch(error => {
      isSearching.value = false
      if (session.value) session.value.status = 'error'
      throw error
    })
    return {
      promise,
      cancel: () => {
        cancelSearchSubscription(eventSource)
        eventSource = null
        if (activeSessionId) {
          cancelSession(activeSessionId).then(value => {
            if (session.value) session.value.status = 'cancelled'
            void value
          }).catch(() => undefined)
        }
        if (session.value) session.value.status = 'cancelled'
        isSearching.value = false
      }
    }
  }

  function updatePipelineStep(stepId: string, updates: Partial<PipelineStep>) {
    const index = pipeline.value.findIndex(s => s.id === stepId)
    if (index !== -1) pipeline.value[index] = { ...pipeline.value[index], ...updates }
  }

  function clearSearch() {
    cancelSearchSubscription(eventSource)
    eventSource = null
    query.value = ''
    session.value = null
    isSearching.value = false
    activeSessionId = null
    resetPipeline()
  }

  function getUnderstanding(): QueryUnderstanding | undefined { return session.value?.understanding }

  return { query, session, isSearching, pipeline, hasResults, resultCount, startSearch, clearSearch, updatePipelineStep, getUnderstanding }
})
