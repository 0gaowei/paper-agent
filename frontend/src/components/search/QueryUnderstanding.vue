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
      
      <div class="entity-section" v-if="entityList.length > 0">
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><Collection /></el-icon>
            <span>识别实体</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="(entity, idx) in entityList"
              :key="idx"
              size="small"
              :type="tagType(idx)"
            >
              {{ entity }}
            </el-tag>
          </div>
        </div>
      </div>
      
      <div class="entity-section" v-if="understanding.domain">
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><Grid /></el-icon>
            <span>领域</span>
          </div>
          <div class="entity-tags">
            <el-tag size="small" type="info">{{ understanding.domain }}</el-tag>
          </div>
        </div>
      </div>
      
      <div class="entity-section" v-if="suitableSources.length > 0">
        <div class="entity-group">
          <div class="entity-label">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据源</span>
          </div>
          <div class="entity-tags">
            <el-tag
              v-for="source in suitableSources"
              :key="source"
              size="small"
              type="warning"
            >
              {{ source }}
            </el-tag>
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
import { Connection, Collection, DataAnalysis, Grid } from '@element-plus/icons-vue'
import type { QueryUnderstanding } from '@/types'

const props = defineProps<{
  understanding: QueryUnderstanding | undefined
}>()

// Backend sends entities as a flat array of strings (e.g. ["mamba snake", "Mamba framework"])
const entityList = computed(() => {
  const entities = props.understanding?.entities
  if (Array.isArray(entities)) return entities
  if (entities && typeof entities === 'object') {
    // Legacy format with topics/methods/datasets/domains sub-arrays
    const e = entities as Record<string, unknown>
    return [
      ...(Array.isArray(e.topics) ? e.topics as string[] : []),
      ...(Array.isArray(e.methods) ? e.methods as string[] : []),
      ...(Array.isArray(e.datasets) ? e.datasets as string[] : []),
      ...(Array.isArray(e.domains) ? e.domains as string[] : []),
    ]
  }
  return []
})

const suitableSources = computed(() => {
  return Array.isArray(props.understanding?.suitableSources)
    ? props.understanding!.suitableSources
    : []
})

const tagTypes = ['primary', 'success', 'warning', 'info'] as const
const tagType = (idx: number) => tagTypes[idx % tagTypes.length]

const intentText = computed(() => {
  const intentMap: Record<string, string> = {
    general: '通用查询',
    survey: '综述查询',
    specific: '具体查询',
    comparative: '对比查询',
    current_state: '现状查询',
    background: '背景查询',
    methodology: '方法查询'
  }
  return intentMap[props.understanding?.intent || ''] || '未知'
})

const intentType = computed(() => {
  const typeMap: Record<string, string> = {
    general: 'info',
    survey: 'primary',
    specific: 'success',
    comparative: 'warning',
    current_state: 'primary',
    background: 'info',
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
