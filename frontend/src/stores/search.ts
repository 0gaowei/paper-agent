import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SearchSession, PipelineStep, QueryUnderstanding } from '@/types'
import { searchPapers as apiSearchPapers } from '@/api'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const session = ref<SearchSession | null>(null)
  const isSearching = ref(false)
  const pipeline = ref<PipelineStep[]>([
    { id: '1', name: '查询理解', status: 'pending', description: '分析用户查询意图和实体' },
    { id: '2', name: '子查询分解', status: 'pending', description: '将复杂查询拆分为多个子查询' },
    { id: '3', name: '多策略检索', status: 'pending', description: '并行执行多个检索策略' },
    { id: '4', name: '综合排序', status: 'pending', description: '融合多源结果并进行排序' }
  ])

  const hasResults = computed(() => session.value && session.value.papers.length > 0)
  const resultCount = computed(() => session.value?.papers.length || 0)

  async function startSearch(searchQuery: string) {
    if (!searchQuery.trim()) return
    
    query.value = searchQuery
    isSearching.value = true
    
    // 重置管道状态
    pipeline.value = pipeline.value.map(step => ({
      ...step,
      status: 'pending' as const,
      result: undefined
    }))

    // 模拟管道执行
    await executePipeline(searchQuery)
  }

  async function executePipeline(searchQuery: string) {
    // 步骤 1: 查询理解
    pipeline.value[0].status = 'running'
    await delay(800)
    pipeline.value[0].status = 'completed'
    
    // 步骤 2: 子查询分解
    pipeline.value[1].status = 'running'
    await delay(600)
    pipeline.value[1].status = 'completed'
    
    // 步骤 3: 多策略检索
    pipeline.value[2].status = 'running'
    await delay(1000)
    pipeline.value[2].status = 'completed'
    
    // 步骤 4: 综合排序
    pipeline.value[3].status = 'running'
    await delay(500)
    pipeline.value[3].status = 'completed'

    // 执行实际搜索
    try {
      const result = await apiSearchPapers(searchQuery)
      session.value = result
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      isSearching.value = false
    }
  }

  function updatePipelineStep(stepId: string, updates: Partial<PipelineStep>) {
    const index = pipeline.value.findIndex(s => s.id === stepId)
    if (index !== -1) {
      pipeline.value[index] = { ...pipeline.value[index], ...updates }
    }
  }

  function clearSearch() {
    query.value = ''
    session.value = null
    isSearching.value = false
    pipeline.value = pipeline.value.map(step => ({
      ...step,
      status: 'pending' as const,
      result: undefined
    }))
  }

  function getUnderstanding(): QueryUnderstanding | undefined {
    return session.value?.understanding
  }

  return {
    query,
    session,
    isSearching,
    pipeline,
    hasResults,
    resultCount,
    startSearch,
    clearSearch,
    updatePipelineStep,
    getUnderstanding
  }
})

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
