<template>
  <div class="paper-detail-view">
    <div v-if="loading" class="loading-state">
      <LoadingSpinner size="large" text="加载论文详情..." />
    </div>
    
    <template v-else-if="paper">
      <div class="detail-header">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div class="header-actions">
          <el-button @click="viewGraph">
            <el-icon><Connection /></el-icon>
            查看图谱
          </el-button>
          <el-button v-if="paper.pdfUrl" type="primary" @click="openPdf">
            <el-icon><Download /></el-icon>
            下载 PDF
          </el-button>
        </div>
      </div>
      
      <div class="paper-info-card">
        <div class="paper-meta">
          <div class="venue-badge" :class="{ openAccess: paper.isOpenAccess }">
            <el-icon v-if="paper.isOpenAccess"><Unlock /></el-icon>
            <el-icon v-else><Lock /></el-icon>
            <span>{{ paper.venue || paper.journal || 'arXiv' }}</span>
          </div>
          <span class="year-badge">{{ paper.year }}</span>
          <span v-if="paper.citationCount" class="citation-badge">
            <el-icon><ChatLineSquare /></el-icon>
            {{ paper.citationCount }} 引用
          </span>
        </div>
        
        <h1 class="paper-title">{{ paper.title }}</h1>
        
        <div class="authors-section">
          <span class="section-label">作者</span>
          <div class="authors-list">
            <span v-for="(author, index) in paper.authors" :key="index" class="author">
              {{ author }}<span v-if="index < paper.authors.length - 1">, </span>
            </span>
          </div>
        </div>
        
        <div class="doi-section" v-if="paper.doi">
          <span class="section-label">DOI</span>
          <a :href="`https://doi.org/${paper.doi}`" target="_blank" class="doi-link">
            {{ paper.doi }}
            <el-icon><TopRight /></el-icon>
          </a>
        </div>
        
        <div class="tags-section" v-if="paper.tags?.length">
          <span class="section-label">标签</span>
          <div class="tags-list">
            <el-tag v-for="tag in paper.tags" :key="tag" size="small" effect="plain">
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </div>
      
      <div class="content-grid">
        <div class="main-content">
          <div class="section-card">
            <h2 class="section-title">摘要</h2>
            <p class="abstract-text">{{ paper.abstract }}</p>
          </div>
          
          <div class="section-card" v-if="paper.relevance !== undefined">
            <h2 class="section-title">相关性分析</h2>
            <div class="relevance-chart">
              <div class="relevance-item">
                <span class="relevance-label">查询相关性</span>
                <div class="relevance-bar">
                  <div class="bar-fill" :style="{ width: `${paper.relevance * 100}%` }"></div>
                </div>
                <span class="relevance-value">{{ (paper.relevance * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          
          <div class="section-card">
            <h2 class="section-title">相关论文推荐</h2>
            <div class="related-papers">
              <PaperCard v-for="relatedPaper in relatedPapers" :key="relatedPaper.id" :paper="relatedPaper" />
            </div>
          </div>
        </div>
        
        <aside class="side-content">
          <div class="section-card">
            <h2 class="section-title">论文链接</h2>
            <div class="links-list">
              <a v-if="paper.semanticScholarUrl" :href="paper.semanticScholarUrl" target="_blank" class="external-link">
                <el-icon><Link /></el-icon>
                Semantic Scholar
              </a>
              <a v-if="paper.pdfUrl" :href="paper.pdfUrl" target="_blank" class="external-link">
                <el-icon><Document /></el-icon>
                PDF 全文
              </a>
            </div>
          </div>
          
          <div class="section-card">
            <h2 class="section-title">统计信息</h2>
            <div class="stats-list">
              <div class="stat-item">
                <span class="stat-label">发表年份</span>
                <span class="stat-value">{{ paper.year }}</span>
              </div>
              <div class="stat-item" v-if="paper.citationCount">
                <span class="stat-label">引用数</span>
                <span class="stat-value">{{ paper.citationCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">开源获取</span>
                <span class="stat-value">{{ paper.isOpenAccess ? '是' : '否' }}</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </template>
    
    <div v-else class="empty-state">
      <el-empty description="未找到论文详情" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Connection, Download, Unlock, Lock, ChatLineSquare, TopRight, Link, Document } from '@element-plus/icons-vue'
import { usePapersStore } from '@/stores/papers'
import { mockPapers } from '@/api'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import PaperCard from '@/components/paper/PaperCard.vue'
import type { Paper } from '@/types'

const router = useRouter()
const route = useRoute()
const papersStore = usePapersStore()

const loading = ref(true)
const paper = ref<Paper | null>(null)

const relatedPapers = computed(() => {
  if (!paper.value) return []
  return mockPapers
    .filter(p => p.id !== paper.value?.id)
    .slice(0, 4)
})

const goBack = () => {
  router.back()
}

const viewGraph = () => {
  if (paper.value) {
    router.push({ name: 'Graph', params: { sessionId: paper.value.id } })
  }
}

const openPdf = () => {
  if (paper.value?.pdfUrl) {
    window.open(paper.value.pdfUrl, '_blank')
  }
}

onMounted(async () => {
  const paperId = route.params.paperId as string
  if (paperId) {
    paper.value = await papersStore.fetchPaper(paperId)
  }
  loading.value = false
})
</script>

<style lang="scss" scoped>
.paper-detail-view {
  max-width: 1200px;
  margin: 0 auto;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.paper-info-card {
  background: white;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.paper-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.venue-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  background: #F0F0F0;
  color: #606266;
  
  &.openAccess {
    background: rgba(103, 194, 58, 0.1);
    color: #67C23A;
  }
}

.year-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  background: #F5F7FA;
  color: #909399;
}

.citation-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #909399;
}

.paper-title {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 20px 0;
  line-height: 1.4;
}

.authors-section,
.doi-section,
.tags-section {
  margin-bottom: 16px;
}

.section-label {
  display: block;
  font-size: 12px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.authors-list {
  font-size: 15px;
  color: #606266;
  line-height: 1.6;
  
  .author {
    color: #409EFF;
  }
}

.doi-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #409EFF;
  font-size: 14px;
  
  &:hover {
    text-decoration: underline;
  }
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  
  :deep(.el-tag) {
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.2);
    color: #409EFF;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.section-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #F0F0F0;
}

.abstract-text {
  font-size: 15px;
  color: #606266;
  line-height: 1.8;
  margin: 0;
}

.relevance-chart {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.relevance-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.relevance-label {
  font-size: 14px;
  color: #606266;
  width: 100px;
}

.relevance-bar {
  flex: 1;
  height: 8px;
  background: #F0F0F0;
  border-radius: 4px;
  overflow: hidden;
  
  .bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #409EFF, #67C23A);
    border-radius: 4px;
    transition: width 0.5s ease;
  }
}

.relevance-value {
  font-size: 14px;
  font-weight: 600;
  color: #409EFF;
  width: 50px;
  text-align: right;
}

.related-papers {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.links-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.external-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #F5F7FA;
  border-radius: 8px;
  color: #409EFF;
  font-size: 14px;
  transition: background 0.3s;
  
  &:hover {
    background: #EBEEF5;
  }
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #F0F0F0;
  
  &:last-child {
    border-bottom: none;
  }
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.stat-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.empty-state {
  padding: 60px;
  background: white;
  border-radius: 12px;
}

@media (max-width: 992px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .related-papers {
    grid-template-columns: 1fr;
  }
}
</style>
