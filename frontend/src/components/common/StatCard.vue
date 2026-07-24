<template>
  <div class="stat-card" :class="{ clickable: clickable }" @click="handleClick">
    <div class="stat-icon" :style="{ background: iconBgColor }">
      <el-icon :size="24" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="stat-content">
      <div class="stat-label">{{ label }}</div>
      <div class="stat-value">{{ formattedValue }}</div>
      <div v-if="change" class="stat-change" :class="changeClass">
        <el-icon v-if="changeType === 'up'"><Top /></el-icon>
        <el-icon v-else-if="changeType === 'down'"><Bottom /></el-icon>
        <span>{{ change }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Top, Bottom } from '@element-plus/icons-vue'
import type { Component } from 'vue'

const props = withDefaults(defineProps<{
  icon: Component
  label: string
  value: number | string
  format?: 'number' | 'currency' | 'percent' | 'duration'
  change?: string
  changeType?: 'up' | 'down' | 'neutral'
  iconColor?: string
  iconBgColor?: string
  clickable?: boolean
}>(), {
  iconBgColor: 'rgba(64, 158, 255, 0.1)',
  iconColor: '#409EFF',
  clickable: false
})

const changeClass = computed(() => {
  if (props.changeType === 'up') return 'positive'
  if (props.changeType === 'down') return 'negative'
  return ''
})

const formattedValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  
  switch (props.format) {
    case 'currency':
      return `$${props.value.toFixed(2)}`
    case 'percent':
      return `${props.value.toFixed(1)}%`
    case 'duration':
      return `${props.value.toFixed(1)}s`
    default:
      if (props.value >= 1000000) {
        return `${(props.value / 1000000).toFixed(1)}M`
      }
      if (props.value >= 1000) {
        return `${(props.value / 1000).toFixed(1)}K`
      }
      return props.value.toString()
  }
})

const emit = defineEmits<{
  click: []
}>()

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style lang="scss" scoped>
.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  
  &.clickable {
    cursor: pointer;
    
    &:hover {
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
    }
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.stat-change {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-top: 4px;
  
  &.positive {
    color: #67c23a;
  }
  
  &.negative {
    color: #f56c6c;
  }
}
</style>
