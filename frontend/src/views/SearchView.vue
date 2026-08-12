<template>
  <div class="search-view">
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">学术论文智能搜索</h1>
        <p class="hero-subtitle">基于大语言模型的智能学术搜索系统，深入理解查询意图，精准检索相关论文</p>
        
        <div class="search-area">
          <SearchInput
            ref="searchInputRef"
            :is-searching="searchStore.isSearching"
            @search="handleSearch"
            @clear="handleClear"
          />
          <el-button v-if="searchStore.isSearching" type="danger" plain @click="cancelSearch">取消搜索</el-button>
        </div>
      </div>
    </div>
    
    <div class="features-section">
      <div class="feature-card">
        <div class="feature-icon">
          <el-icon :size="32"><Cpu /></el-icon>
        </div>
        <h3>智能查询理解</h3>
        <p>自动识别查询中的主题、方法、数据集和领域</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">
          <el-icon :size="32"><Share /></el-icon>
        </div>
        <h3>多策略检索</h3>
        <p>并行执行多种检索策略，全面覆盖相关论文</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">
          <el-icon :size="32"><DataLine /></el-icon>
        </div>
        <h3>智能排序</h3>
        <p>综合相关性、时效性、权威性进行排序</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">
          <el-icon :size="32"><Connection /></el-icon>
        </div>
        <h3>引用图谱</h3>
        <p>可视化展示论文引用关系，发现研究脉络</p>
      </div>
    </div>
    
    <transition name="slide">
      <div v-if="searchStore.isSearching || searchStore.session" class="results-section">
        <div class="section-header">
          <h2>搜索流程</h2>
        </div>
        <SearchPipeline :steps="searchStore.pipeline" />
        
        <div v-if="searchStore.session?.understanding" class="understanding-section">
          <QueryUnderstanding :understanding="searchStore.session.understanding" />
        </div>
        
        <div v-if="searchStore.session?.error" class="error-section">
          <el-alert type="error" :title="searchStore.session.error" :closable="false" show-icon>
            <template #default>
              <p>搜索过程中遇到错误，请检查 API 配置或稍后重试。</p>
            </template>
          </el-alert>
        </div>

        <div v-if="searchStore.session?.stats" class="stats-section">
          <div class="section-header">
            <h2>搜索统计</h2>
          </div>
          <div class="stats-grid">
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
              label="Token 使用"
              :value="searchStore.session.stats.tokenUsage ?? 0"
            />
            <StatCard
              :icon="Money"
              label="成本"
              :value="searchStore.session.stats.cost ?? 0"
              format="currency"
            />
            <StatCard
              :icon="Timer"
              label="耗时"
              :value="searchStore.session.stats.duration ?? 0"
              format="duration"
            />
          </div>
        </div>
        
        <div v-if="searchStore.hasResults" class="results-preview">
          <div class="section-header flex-between">
            <h2>搜索结果</h2>
            <el-button type="primary" @click="viewAllResults">
              查看全部结果
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
          <PaperList :papers="searchStore.session?.papers || []" />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Cpu, Share, DataLine, Connection, Document, Select, Coin, Money, Timer, ArrowRight } from '@element-plus/icons-vue'
import { useSearchStore } from '@/stores/search'
import { SearchConfig } from '@/types'
import SearchInput from '@/components/search/SearchInput.vue'
import SearchPipeline from '@/components/search/SearchPipeline.vue'
import QueryUnderstanding from '@/components/search/QueryUnderstanding.vue'
import StatCard from '@/components/common/StatCard.vue'
import PaperList from '@/components/paper/PaperList.vue'

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()

const searchInputRef = ref<InstanceType<typeof SearchInput> | null>(null)

const handleSearch = (searchQuery: string, options: SearchConfig) => {
  const operation = searchStore.startSearch(searchQuery, options)
  operation.promise.catch(() => undefined)
}

const cancelSearch = () => searchStore.clearSearch()

const handleClear = () => {
  searchStore.clearSearch()
}

const viewAllResults = () => {
  if (searchStore.session) {
    router.push({ name: 'Results', params: { sessionId: searchStore.session.id } })
  }
}

onMounted(() => {
  searchInputRef.value?.focus()
  const initialQuery = route.query.q
  if (typeof initialQuery === 'string' && initialQuery) searchInputRef.value?.setQuery?.(initialQuery)
})
</script>

<style lang="scss" scoped>
.search-view {
  min-height: calc(100vh - 100px);
}

.hero-section {
  background: linear-gradient(135deg, #409EFF 0%, #53A8FF 50%, #66BFFF 100%);
  padding: 80px 20px;
  text-align: center;
  border-radius: 0 0 40px 40px;
  margin-bottom: 40px;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  color: white;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.hero-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 40px 0;
  line-height: 1.6;
}

.search-area {
  max-width: 800px;
  margin: 0 auto;
}

.features-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto 40px;
  padding: 0 20px;
}

.feature-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
  
  .feature-icon {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(64, 158, 255, 0.2) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 16px;
    color: #409EFF;
  }
  
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px 0;
  }
  
  p {
    font-size: 14px;
    color: #909399;
    margin: 0;
    line-height: 1.5;
  }
}

.results-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section-header {
  margin-bottom: 20px;
  
  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.flex-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.understanding-section {
  margin: 20px 0;
}

.error-section {
  margin: 20px 0;
  padding: 0 16px;

  :deep(.el-alert) {
    border-radius: 12px;
    border: 1px solid var(--el-color-danger-light-8);
  }
}

.stats-section {
  margin: 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.results-preview {
  margin-top: 30px;
  
  .section-header {
    margin-bottom: 20px;
  }
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.5s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

@media (max-width: 992px) {
  .features-section {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 576px) {
  .hero-title {
    font-size: 28px;
  }
  
  .hero-subtitle {
    font-size: 16px;
  }
  
  .features-section {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
