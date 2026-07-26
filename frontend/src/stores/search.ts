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
        setStep('3', 'running', data)
        break
      }
      case 'usage':
        session.value!.usage = data as UsageStats
        session.value!.stats = { ...session.value!.stats, ...(data as UsageStats) }
        break
      case 'partial_documents':
        setStep('3', 'running', data)
        break
      case 'citation_expanded':
        setStep('3', 'running', data)
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
      case 'done':
        session.value!.status = 'completed'
        session.value!.completedAt = new Date().toISOString()
        setStep('3', 'completed')
        setStep('4', 'completed', data)
        isSearching.value = false
        cancelSearchSubscription(eventSource)
        eventSource = null
        break
      case 'error':
        session.value!.status = 'error'
        session.value!.error = String((data as { error?: string }).error ?? event.error ?? '搜索失败')
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
