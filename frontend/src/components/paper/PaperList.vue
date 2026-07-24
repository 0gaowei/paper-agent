<template>
  <div class="paper-list">
    <div class="list-header">
      <div class="list-info">
        <span class="result-count">共找到 {{ papers.length }} 篇论文</span>
      </div>
      <div class="view-toggle">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button label="card">
            <el-icon><Grid /></el-icon>
          </el-radio-button>
          <el-radio-button label="list">
            <el-icon><List /></el-icon>
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>
    
    <div v-if="papers.length === 0" class="empty-state">
      <el-empty description="暂无论文数据" />
    </div>
    
    <div v-else :class="['paper-container', viewMode]">
      <transition-group name="list">
        <PaperCard
          v-for="paper in papers"
          :key="paper.id"
          :paper="paper"
        />
      </transition-group>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Grid, List } from '@element-plus/icons-vue'
import PaperCard from './PaperCard.vue'
import type { Paper } from '@/types'

defineProps<{
  papers: Paper[]
}>()

const viewMode = ref<'card' | 'list'>('card')
</script>

<style lang="scss" scoped>
.paper-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.result-count {
  font-size: 14px;
  color: #606266;
}

.view-toggle {
  :deep(.el-radio-group) {
    display: flex;
  }
  
  :deep(.el-radio-button__inner) {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 12px;
  }
}

.empty-state {
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
}

.paper-container {
  &.card {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 20px;
  }
  
  &.list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    :deep(.paper-card) {
      padding: 16px 20px;
      
      .abstract {
        -webkit-line-clamp: 2;
      }
    }
  }
}

.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.list-move {
  transition: transform 0.4s ease;
}
</style>
