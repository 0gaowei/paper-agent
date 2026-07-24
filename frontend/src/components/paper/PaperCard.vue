<template>
  <div class="paper-card" @click="handleClick">
    <div class="card-header">
      <div class="venue-badge" :class="{ openAccess: paper.isOpenAccess }">
        <el-icon v-if="paper.isOpenAccess"><Unlock /></el-icon>
        <el-icon v-else><Lock /></el-icon>
        <span>{{ paper.venue || paper.journal || 'arXiv' }}</span>
      </div>
      <span class="year-badge">{{ paper.year }}</span>
    </div>
    
    <h3 class="paper-title">{{ paper.title }}</h3>
    
    <div class="authors">
      <span v-for="(author, index) in displayAuthors" :key="index" class="author">
        {{ author }}<span v-if="index < displayAuthors.length - 1">, </span>
      </span>
      <span v-if="paper.authors.length > 3" class="more-authors">
        +{{ paper.authors.length - 3 }}
      </span>
    </div>
    
    <p class="abstract" v-if="paper.abstract">
      {{ truncatedAbstract }}
    </p>
    
    <div class="tags" v-if="paper.tags?.length">
      <el-tag
        v-for="tag in paper.tags.slice(0, 3)"
        :key="tag"
        size="small"
        effect="plain"
      >
        {{ tag }}
      </el-tag>
    </div>
    
    <div class="card-footer">
      <div class="metrics">
        <div class="metric" v-if="paper.relevance !== undefined">
          <el-icon><Aim /></el-icon>
          <span>{{ (paper.relevance * 100).toFixed(0) }}%</span>
        </div>
        <div class="metric" v-if="paper.citationCount !== undefined">
          <el-icon><ChatLineSquare /></el-icon>
          <span>{{ paper.citationCount }}</span>
        </div>
      </div>
      
      <div class="actions">
        <el-button size="small" @click.stop="viewDetails">
          <el-icon><View /></el-icon>
          详情
        </el-button>
        <el-button size="small" type="primary" plain @click.stop="viewGraph">
          <el-icon><Connection /></el-icon>
          图谱
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Unlock, Lock, Aim, ChatLineSquare, View, Connection } from '@element-plus/icons-vue'
import type { Paper } from '@/types'

const props = defineProps<{
  paper: Paper
}>()

const router = useRouter()

const displayAuthors = computed(() => {
  return props.paper.authors.slice(0, 3)
})

const truncatedAbstract = computed(() => {
  const abstract = props.paper.abstract || ''
  if (abstract.length <= 200) return abstract
  return abstract.substring(0, 200) + '...'
})

const handleClick = () => {
  viewDetails()
}

const viewDetails = () => {
  router.push({ name: 'PaperDetail', params: { paperId: props.paper.id } })
}

const viewGraph = () => {
  router.push({ name: 'Graph', params: { sessionId: props.paper.id } })
}
</script>

<style lang="scss" scoped>
.paper-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  cursor: pointer;
  
  &:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    transform: translateY(-4px);
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.venue-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: #F0F0F0;
  color: #606266;
  
  &.openAccess {
    background: rgba(103, 194, 58, 0.1);
    color: #67C23A;
  }
}

.year-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: #F5F7FA;
  color: #909399;
}

.paper-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 10px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.authors {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
  line-height: 1.5;
  
  .author {
    color: #409EFF;
  }
  
  .more-authors {
    color: #909399;
  }
}

.abstract {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  
  :deep(.el-tag) {
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.2);
    color: #409EFF;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #F0F0F0;
}

.metrics {
  display: flex;
  gap: 16px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #606266;
  
  .el-icon {
    font-size: 14px;
    color: #909399;
  }
}

.actions {
  display: flex;
  gap: 8px;
  
  :deep(.el-button) {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}
</style>
