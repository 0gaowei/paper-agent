import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Paper, FilterState } from '@/types'
import { getPaperDetail } from '@/api'

export const usePapersStore = defineStore('papers', () => {
  const papers = ref<Map<string, Paper>>(new Map())
  const currentPaper = ref<Paper | null>(null)
  const isLoading = ref(false)
  
  const filters = ref<FilterState>({
    yearRange: [2000, 2026],
    minRelevance: 0,
    sortBy: 'relevance'
  })

  const filteredPapers = computed(() => {
    let result = Array.from(papers.value.values())
    
    // 按年份筛选
    result = result.filter(p => {
      return p.year >= filters.value.yearRange[0] && p.year <= filters.value.yearRange[1]
    })
    
    // 按相关性筛选
    if (filters.value.minRelevance > 0) {
      result = result.filter(p => (p.relevance || 0) >= filters.value.minRelevance)
    }
    
    // 排序
    switch (filters.value.sortBy) {
      case 'relevance':
        result.sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
        break
      case 'date':
        result.sort((a, b) => b.year - a.year)
        break
      case 'citations':
        result.sort((a, b) => (b.citationCount || 0) - (a.citationCount || 0))
        break
      case 'combined':
        result.sort((a, b) => {
          const scoreA = (a.relevance || 0) * 0.4 + (a.citationCount || 0) / 100000 * 0.3 + (a.year - 2000) / 26 * 0.3
          const scoreB = (b.relevance || 0) * 0.4 + (b.citationCount || 0) / 100000 * 0.3 + (b.year - 2000) / 26 * 0.3
          return scoreB - scoreA
        })
        break
    }
    
    return result
  })

  const paperList = computed(() => Array.from(papers.value.values()))

  function setPapers(paperList: Paper[]) {
    papers.value.clear()
    paperList.forEach(p => papers.value.set(p.id, p))
  }

  function addPapers(newPapers: Paper[]) {
    newPapers.forEach(p => papers.value.set(p.id, p))
  }

  async function fetchPaper(paperId: string): Promise<Paper | null> {
    if (papers.value.has(paperId)) {
      currentPaper.value = papers.value.get(paperId) || null
      return currentPaper.value
    }

    isLoading.value = true
    try {
      const paper = await getPaperDetail(paperId)
      if (paper) {
        papers.value.set(paper.id, paper)
        currentPaper.value = paper
      }
      return paper
    } finally {
      isLoading.value = false
    }
  }

  function setCurrentPaper(paper: Paper | null) {
    currentPaper.value = paper
  }

  function applyFilters(newFilters: Partial<FilterState>) {
    filters.value = { ...filters.value, ...newFilters }
  }

  function resetFilters() {
    filters.value = {
      yearRange: [2000, 2026],
      minRelevance: 0,
      sortBy: 'relevance'
    }
  }

  function updateYearRange(range: [number, number]) {
    filters.value.yearRange = range
  }

  function updateSort(sortBy: FilterState['sortBy']) {
    filters.value.sortBy = sortBy
  }

  function updateMinRelevance(min: number) {
    filters.value.minRelevance = min
  }

  return {
    papers,
    currentPaper,
    isLoading,
    filters,
    filteredPapers,
    paperList,
    setPapers,
    addPapers,
    fetchPaper,
    setCurrentPaper,
    applyFilters,
    resetFilters,
    updateYearRange,
    updateSort,
    updateMinRelevance
  }
})
