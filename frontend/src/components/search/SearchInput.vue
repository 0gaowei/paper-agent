<template>
  <div class="search-input-container">
    <div class="search-box" :class="{ focused: isFocused, searching: isSearching }">
      <el-icon class="search-icon" :size="22">
        <Search />
      </el-icon>
      <input
        ref="inputRef"
        v-model="searchQuery"
        type="text"
        class="search-field"
        :placeholder="placeholder"
        :disabled="isSearching"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keyup.enter="handleSearch"
      />
      <el-button
        v-if="searchQuery"
        class="clear-btn"
        :icon="Close"
        text
        @click="clearSearch"
      />
      <el-button
        class="search-btn"
        type="primary"
        :loading="isSearching"
        @click="handleSearch"
      >
        {{ isSearching ? '搜索中...' : '搜索' }}
      </el-button>
    </div>
    
    <div class="advanced-toggle" @click="showAdvanced = !showAdvanced">
      <el-icon><ArrowDown v-if="!showAdvanced" /><ArrowUp v-else /></el-icon>
      <span>高级选项</span>
    </div>
    
    <transition name="slide">
      <div v-show="showAdvanced" class="advanced-options">
        <div class="option-row">
          <span class="option-label">启用查询分解</span>
          <el-switch v-model="options.enableQueryDecomposition" />
        </div>
        <div class="option-row">
          <span class="option-label">启用迭代检索</span>
          <el-switch v-model="options.enableIterativeSearch" />
        </div>
        <div class="option-row">
          <span class="option-label">启用查询改写</span>
          <el-switch v-model="options.enableQueryRewrite" />
        </div>
        <div class="option-row">
          <span class="option-label">最大迭代次数</span>
          <el-input-number v-model="options.maxIterations" :min="1" :max="10" size="small" />
        </div>
        <div class="option-row">
          <span class="option-label">最大结果数</span>
          <el-input-number v-model="options.maxResults" :min="10" :max="500" :step="10" size="small" />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Search, Close, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { ElIcon, ElButton, ElSwitch, ElInputNumber } from 'element-plus'

const props = withDefaults(defineProps<{
  placeholder?: string
  isSearching?: boolean
}>(), {
  placeholder: '输入搜索关键词，例如：transformer architecture, BERT, diffusion model...',
  isSearching: false
})

const emit = defineEmits<{
  search: [query: string, options: SearchOptions]
  clear: []
}>()

interface SearchOptions {
  enableQueryDecomposition: boolean
  enableIterativeSearch: boolean
  enableQueryRewrite: boolean
  maxIterations: number
  maxResults: number
}

const searchQuery = ref('')
const isFocused = ref(false)
const showAdvanced = ref(false)
const inputRef = ref<HTMLInputElement | null>(null)

const options = reactive<SearchOptions>({
  enableQueryDecomposition: true,
  enableIterativeSearch: true,
  enableQueryRewrite: true,
  maxIterations: 3,
  maxResults: 100
})

const handleSearch = () => {
  if (searchQuery.value.trim() && !props.isSearching) {
    emit('search', searchQuery.value.trim(), { ...options })
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  emit('clear')
  inputRef.value?.focus()
}

const focus = () => {
  inputRef.value?.focus()
}

defineExpose({ focus })
</script>

<style lang="scss" scoped>
.search-input-container {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.search-box {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 50px;
  padding: 8px 8px 8px 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  transition: all 0.3s ease;
  
  &.focused {
    border-color: #409EFF;
    box-shadow: 0 4px 24px rgba(64, 158, 255, 0.25);
  }
  
  &.searching {
    opacity: 0.9;
  }
}

.search-icon {
  color: #909399;
  margin-right: 12px;
  flex-shrink: 0;
}

.search-field {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  color: #303133;
  background: transparent;
  
  &::placeholder {
    color: #C0C4CC;
  }
  
  &:disabled {
    cursor: not-allowed;
  }
}

.clear-btn {
  margin-right: 8px;
  color: #909399;
  
  &:hover {
    color: #606266;
  }
}

.search-btn {
  border-radius: 24px;
  padding: 12px 28px;
  font-weight: 500;
}

.advanced-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
  color: #606266;
  font-size: 14px;
  cursor: pointer;
  transition: color 0.3s;
  
  &:hover {
    color: #409EFF;
  }
}

.advanced-options {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-top: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #F0F0F0;
  
  &:last-child {
    border-bottom: none;
  }
}

.option-label {
  font-size: 14px;
  color: #606266;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
