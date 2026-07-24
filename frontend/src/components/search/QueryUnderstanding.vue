<template>
  <div class="query-understanding" v-if="understanding">
    <div class="understanding-header">
      <el-icon class="header-icon"><Connection /></el-icon>
      <span class="header-title">查询理解结果</span>
    </div>
    
    <div class="understanding-content">
      <div class="original-query">
        <span class="query-label">原始查询</span>
        <span class="query-text">{{ understanding.originalQuery }}</span>
      </div>
      
      <div class="entity-section">
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><Collection /></el-icon>
            <span>主题</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="topic in understanding.entities.topics"
              :key="topic"
              size="small"
              type="primary"
            >
              {{ topic }}
            </el-tag>
            <span v-if="!understanding.entities.topics.length" class="empty-text">未识别到主题</span>
          </div>
        </div>
        
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><Tools /></el-icon>
            <span>方法</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="method in understanding.entities.methods"
              :key="method"
              size="small"
              type="success"
            >
              {{ method }}
            </el-tag>
            <span v-if="!understanding.entities.methods.length" class="empty-text">未识别到方法</span>
          </div>
        </div>
        
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据集</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="dataset in understanding.entities.datasets"
              :key="dataset"
              size="small"
              type="warning"
            >
              {{ dataset }}
            </el-tag>
            <span v-if="!understanding.entities.datasets.length" class="empty-text">未识别到数据集</span>
          </div>
        </div>
        
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><Grid /></el-icon>
            <span>领域</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="domain in understanding.entities.domains"
              :key="domain"
              size="small"
              type="info"
            >
              {{ domain }}
            </el-tag>
            <span v-if="!understanding.entities.domains.length" class="empty-text">未识别到领域</span>
          </div>
        </div>
      </div>
      
      <div class="intent-section">
        <div class="intent-label">查询意图</div>
        <div class="intent-value">
          <el-tag :type="intentType" size="default">
            {{ intentText }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Connection, Collection, Tools, DataAnalysis, Grid } from '@element-plus/icons-vue'
import type { QueryUnderstanding } from '@/types'

const props = defineProps<{
  understanding: QueryUnderstanding | undefined
}>()

const intentText = computed(() => {
  const intentMap: Record<string, string> = {
    survey: '综述查询',
    specific: '具体查询',
    comparative: '对比查询',
    methodology: '方法查询'
  }
  return intentMap[props.understanding?.intent || ''] || '未知'
})

const intentType = computed(() => {
  const typeMap: Record<string, string> = {
    survey: 'primary',
    specific: 'success',
    comparative: 'warning',
    methodology: 'info'
  }
  return typeMap[props.understanding?.intent || ''] || 'info'
})
</script>

<style lang="scss" scoped>
.query-understanding {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.understanding-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  
  .header-icon {
    font-size: 20px;
    color: #409EFF;
  }
  
  .header-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }
}

.understanding-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.original-query {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.05) 0%, rgba(64, 158, 255, 0.1) 100%);
  border-radius: 8px;
  border-left: 3px solid #409EFF;
  
  .query-label {
    font-size: 12px;
    color: #909399;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  
  .query-text {
    font-size: 15px;
    color: #303133;
    font-weight: 500;
  }
}

.entity-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.entity-group {
  padding: 12px;
  background: #F5F7FA;
  border-radius: 8px;
}

.entity-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
  
  .el-icon {
    font-size: 14px;
    color: #909399;
  }
}

.entity-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-text {
  font-size: 12px;
  color: #C0C4CC;
  font-style: italic;
}

.intent-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #F5F7FA;
  border-radius: 8px;
}

.intent-label {
  font-size: 14px;
  color: #606266;
}

.intent-value {
  :deep(.el-tag) {
    font-weight: 500;
  }
}
</style>
