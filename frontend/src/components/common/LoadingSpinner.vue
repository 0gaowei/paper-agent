<template>
  <div class="loading-spinner" :class="sizeClass">
    <div class="spinner" :style="spinnerStyle">
      <div v-for="i in 4" :key="i" class="spinner-blade" :style="{ animationDelay: `${(i - 1) * 0.125}s` }" />
    </div>
    <div v-if="text" class="loading-text">{{ text }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: 'small' | 'medium' | 'large'
  color?: string
  text?: string
}>(), {
  size: 'medium',
  color: '#409EFF'
})

const sizeClass = computed(() => `size-${props.size}`)

const spinnerStyle = computed(() => ({
  '--spinner-color': props.color
}))
</script>

<style lang="scss" scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  
  &.size-small {
    .spinner {
      width: 20px;
      height: 20px;
    }
  }
  
  &.size-medium {
    .spinner {
      width: 36px;
      height: 36px;
    }
  }
  
  &.size-large {
    .spinner {
      width: 48px;
      height: 48px;
    }
  }
}

.spinner {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 4px;
  animation: spinner-rotate 1s linear infinite;
}

.spinner-blade {
  width: 100%;
  height: 100%;
  background: var(--spinner-color);
  border-radius: 50%;
  animation: spinner-pulse 0.8s ease-in-out infinite;
}

.loading-text {
  font-size: 14px;
  color: #909399;
}

@keyframes spinner-rotate {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes spinner-pulse {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
}
</style>
