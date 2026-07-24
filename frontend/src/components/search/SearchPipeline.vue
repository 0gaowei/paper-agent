<template>
  <div class="search-pipeline">
    <div class="pipeline-header">
      <h3 class="pipeline-title">搜索流程</h3>
      <span class="pipeline-status" :class="overallStatus">
        {{ statusText }}
      </span>
    </div>
    
    <div class="pipeline-steps">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="pipeline-step"
        :class="step.status"
      >
        <div class="step-connector" v-if="index > 0">
          <div class="connector-line" :class="{ active: step.status !== 'pending' }" />
        </div>
        
        <div class="step-content">
          <div class="step-icon">
            <el-icon v-if="step.status === 'pending'" :size="20"><Minus /></el-icon>
            <el-icon v-else-if="step.status === 'running'" class="spin" :size="20"><Loading /></el-icon>
            <el-icon v-else-if="step.status === 'completed'" :size="20"><Check /></el-icon>
            <el-icon v-else-if="step.status === 'error'" :size="20"><Close /></el-icon>
          </div>
          
          <div class="step-info">
            <div class="step-name">{{ step.name }}</div>
            <div class="step-description" v-if="step.description">
              {{ step.description }}
            </div>
          </div>
          
          <div class="step-status-badge" :class="step.status">
            {{ statusLabel(step.status) }}
          </div>
        </div>
        
        <transition name="fade">
          <div v-if="step.result && step.status === 'completed'" class="step-result">
            <component :is="getResultComponent(step.id)" :data="step.result" />
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Minus, Check, Close, Loading } from '@element-plus/icons-vue'
import type { PipelineStep } from '@/types'

const props = defineProps<{
  steps: PipelineStep[]
}>()

const overallStatus = computed(() => {
  if (props.steps.every(s => s.status === 'pending')) return 'pending'
  if (props.steps.every(s => s.status === 'completed')) return 'completed'
  if (props.steps.some(s => s.status === 'error')) return 'error'
  return 'running'
})

const statusText = computed(() => {
  switch (overallStatus.value) {
    case 'pending': return '等待开始'
    case 'running': return '搜索中...'
    case 'completed': return '搜索完成'
    case 'error': return '搜索出错'
    default: return ''
  }
})

const statusLabel = (status: PipelineStep['status']) => {
  const labels: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    completed: '已完成',
    error: '错误'
  }
  return labels[status] || status
}

const getResultComponent = (_stepId: string) => {
  return null
}
</script>

<style lang="scss" scoped>
.search-pipeline {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.pipeline-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.pipeline-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  
  &.pending {
    background: #F0F0F0;
    color: #909399;
  }
  
  &.running {
    background: rgba(64, 158, 255, 0.1);
    color: #409EFF;
  }
  
  &.completed {
    background: rgba(103, 194, 58, 0.1);
    color: #67C23A;
  }
  
  &.error {
    background: rgba(245, 108, 108, 0.1);
    color: #F56C6C;
  }
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.pipeline-step {
  position: relative;
  padding-left: 60px;
  
  &.pending {
    .step-icon {
      background: #F0F0F0;
      color: #C0C4CC;
    }
    
    .step-name {
      color: #C0C4CC;
    }
  }
  
  &.running {
    .step-icon {
      background: linear-gradient(135deg, #409EFF 0%, #53A8FF 100%);
      color: white;
    }
    
    .step-name {
      color: #409EFF;
    }
  }
  
  &.completed {
    .step-icon {
      background: linear-gradient(135deg, #67C23A 0%, #85CE61 100%);
      color: white;
    }
    
    .step-name {
      color: #303133;
    }
  }
  
  &.error {
    .step-icon {
      background: linear-gradient(135deg, #F56C6C 0%, #F78989 100%);
      color: white;
    }
    
    .step-name {
      color: #F56C6C;
    }
  }
}

.step-connector {
  position: absolute;
  left: 22px;
  top: -12px;
  height: 12px;
  
  .connector-line {
    width: 2px;
    height: 100%;
    background: #E4E7ED;
    transition: background 0.3s;
    
    &.active {
      background: linear-gradient(180deg, #67C23A 0%, #409EFF 100%);
    }
  }
}

.step-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  position: relative;
}

.step-icon {
  position: absolute;
  left: -52px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .spin {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-info {
  flex: 1;
}

.step-name {
  font-size: 15px;
  font-weight: 500;
  transition: color 0.3s;
}

.step-description {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.step-status-badge {
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  
  &.pending {
    background: #F0F0F0;
    color: #909399;
  }
  
  &.running {
    background: rgba(64, 158, 255, 0.1);
    color: #409EFF;
  }
  
  &.completed {
    background: rgba(103, 194, 58, 0.1);
    color: #67C23A;
  }
  
  &.error {
    background: rgba(245, 108, 108, 0.1);
    color: #F56C6C;
  }
}

.step-result {
  padding: 12px 16px;
  background: #F5F7FA;
  border-radius: 8px;
  margin-bottom: 16px;
  margin-left: -60px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
