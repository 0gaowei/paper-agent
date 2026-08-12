<template>
  <div class="results-view">
    <div class="results-header">
      <div class="header-left">
        <h1 class="page-title">搜索结果</h1>
        <div class="query-info" v-if="searchStore.session">
          <span class="query-label">查询：</span>
          <span class="query-text">"{{ searchStore.query }}"</span>
          <span class="result-count">找到 {{ searchStore.session.stats.totalPapers }} 篇论文</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回搜索
        </el-button>
        <el-button type="primary" @click="viewGraph">
          <el-icon><Connection /></el-icon>
          查看图谱
        </el-button>
      </div>
    </div>
    
    <div class="results-content">
      <aside class="filter-sidebar">
        <div class="filter-section">
          <h3 class="filter-title">排序方式</h3>
          <el-radio-group v-model="sortBy" @change="handleSortChange">
            <el-radio-button label="relevance">相关性</el-radio-button>
            <el-radio-button label="date">发表时间</el-radio-button>
            <el-radio-button label="citations">引用数</el-radio-button>
            <el-radio-button label="combined">综合排序</el-radio-button>
          </el-radio-group>
        </div>
        
        <div class="filter-section">
          <h3 class="filter-title">发表年份</h3>
          <el-slider
            v-model="yearRange"
            range
            :min="2000"
            :max="2026"
            @change="handleYearChange"
          />
          <div class="year-display">
            {{ yearRange[0] }} - {{ yearRange[1] }}
          </div>
        </div>
        
        <div class="filter-section">
          <h3 class="filter-title">最低相关性</h3>
          <el-slider
            v-model="minRelevance"
            :min="0"
            :max="100"
            :format-tooltip="(val: number) => `${val}%`"
            @change="handleRelevanceChange"
          />
          <div class="relevance-display">
            {{ minRelevance }}%
          </div>
        </div>
        
        <div class="filter-section">
          <h3 class="filter-title">视图切换</h3>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="card">
              <el-icon><Grid /></el-icon>
              卡片
            </el-radio-button>
            <el-radio-button label="list">
              <el-icon><List /></el-icon>
              列表
            </el-radio-button>
          </el-radio-group>
        </div>
        
        <el-button class="reset-btn" text @click="resetFilters">
          <el-icon><RefreshLeft /></el-icon>
          重置筛选
        </el-button>
      </aside>
      
      <main class="results-main">
        <div class="stats-bar" v-if="searchStore.session">
          <StatCard
            :icon="Document"
            label="论文总数"
            :value="searchStore.session.stats.totalPapers ?? 0"
          />
          <StatCard
            :icon="Select"
            label="相关论文"
            :value="searchStore.session.stats.relevantPapers ?? 0"
          />
          <StatCard
            :icon="Connection"
            label="API 调用"
            :value="searchStore.session.stats.apiCalls ?? 0"
          />
          <StatCard
            :icon="Coin"
            label="成本"
            :value="searchStore.session.stats.cost ?? 0"
            format="currency"
          />
        </div>
        
        <el-alert v-if="searchStore.session?.answerSummary" :title="searchStore.session.answerSummary" type="info" :closable="false" />
        <div v-if="searchStore.session?.evidenceSnippets?.length" class="evidence-list"><h3>证据片段</h3><p v-for="(snippet, index) in searchStore.session.evidenceSnippets" :key="index">{{ snippet.text }}</p></div>
        <PaperList :papers="papersStore.filteredPapers" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Connection, Grid, List, RefreshLeft, Document, Select, Coin } from '@element-plus/icons-vue'
import { useSearchStore } from '@/stores/search'
import { getSession } from '@/api'
import { usePapersStore } from '@/stores/papers'
import StatCard from '@/components/common/StatCard.vue'
import PaperList from '@/components/paper/PaperList.vue'

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()
const papersStore = usePapersStore()

const sortBy = ref('relevance')
const yearRange = ref<[number, number]>([2000, 2026])
const minRelevance = ref(0)
const viewMode = ref<'card' | 'list'>('card')

const handleSortChange = (value: string) => {
  papersStore.updateSort(value as any)
}

const handleYearChange = (value: [number, number]) => {
  papersStore.updateYearRange(value)
}

const handleRelevanceChange = (value: number) => {
  papersStore.updateMinRelevance(value / 100)
}

const resetFilters = () => {
  sortBy.value = 'relevance'
  yearRange.value = [2000, 2026]
  minRelevance.value = 0
  papersStore.resetFilters()
}

const goBack = () => {
  router.push({ name: 'Search' })
}

const viewGraph = () => {
  if (searchStore.session) {
    router.push({ name: 'Graph', params: { sessionId: searchStore.session.id } })
  }
}

onMounted(async () => {
  // Reset paper filter state so all papers from a new session are visible
  papersStore.resetFilters()
  if (!searchStore.session) {
      const sessionId = route.params.sessionId as string
      if (sessionId) {
        const restored = await getSession(sessionId)
        searchStore.session = restored
        searchStore.query = restored.query
      }
  }
  if (searchStore.session) {
    papersStore.setPapers(searchStore.session.papers)
  }
})
</script>

<style lang="scss" scoped>
.results-view {
  min-height: calc(100vh - 100px);
}

.results-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.header-left {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }
  
  .query-info {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    
    .query-label {
      color: #909399;
    }
    
    .query-text {
      color: #409EFF;
      font-weight: 500;
    }
    
    .result-count {
      color: #606266;
      padding-left: 16px;
      border-left: 1px solid #E4E7ED;
    }
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.results-content {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 24px;
}

.filter-sidebar {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 80px;
  height: fit-content;
}

.filter-section {
  margin-bottom: 24px;
  
  &:last-of-type {
    margin-bottom: 16px;
  }
}

.filter-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.year-display,
.relevance-display {
  text-align: center;
  font-size: 13px;
  color: #606266;
  margin-top: 8px;
}

.reset-btn {
  width: 100%;
  color: #909399;
  
  &:hover {
    color: #409EFF;
  }
}

.results-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 992px) {
  .results-content {
    grid-template-columns: 1fr;
  }
  
  .filter-sidebar {
    position: static;
  }
  
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
