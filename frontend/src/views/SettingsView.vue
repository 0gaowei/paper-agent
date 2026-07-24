<template>
  <div class="settings-view">
    <div class="settings-header">
      <h1 class="page-title">设置</h1>
      <el-button type="primary" @click="saveAllSettings" :loading="saving">
        <el-icon><Check /></el-icon>
        保存设置
      </el-button>
    </div>
    
    <div class="settings-content">
      <el-tabs v-model="activeTab" class="settings-tabs">
        <el-tab-pane label="API 配置" name="api">
          <div class="settings-section">
            <h2 class="section-title">API 配置</h2>
            
            <div class="form-group">
              <label class="form-label">提供商</label>
              <el-select v-model="apiConfig.provider" class="form-input">
                <el-option label="OpenAI" value="openai" />
                <el-option label="Anthropic" value="anthropic" />
                <el-option label="DeepSeek" value="deepseek" />
                <el-option label="Qwen" value="qwen" />
              </el-select>
            </div>
            
            <div class="form-group">
              <label class="form-label">API Key</label>
              <el-input
                v-model="apiConfig.apiKey"
                type="password"
                placeholder="输入您的 API Key"
                show-password
                class="form-input"
              />
            </div>
            
            <div class="form-group">
              <label class="form-label">Base URL</label>
              <el-input
                v-model="apiConfig.baseUrl"
                placeholder="可选，API 请求地址"
                class="form-input"
              />
            </div>
            
            <div class="form-group">
              <label class="form-label">模型</label>
              <el-input
                v-model="apiConfig.model"
                placeholder="例如: gpt-4-turbo, claude-3-opus"
                class="form-input"
              />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="搜索策略" name="search">
          <div class="settings-section">
            <h2 class="section-title">搜索策略配置</h2>
            
            <div class="form-group">
              <div class="form-row">
                <div class="form-info">
                  <label class="form-label">启用查询分解</label>
                  <p class="form-hint">将复杂查询拆分为多个子查询分别检索</p>
                </div>
                <el-switch v-model="searchConfig.enableQueryDecomposition" />
              </div>
            </div>
            
            <div class="form-group">
              <div class="form-row">
                <div class="form-info">
                  <label class="form-label">启用迭代检索</label>
                  <p class="form-hint">根据检索结果迭代优化查询</p>
                </div>
                <el-switch v-model="searchConfig.enableIterativeSearch" />
              </div>
            </div>
            
            <div class="form-group">
              <div class="form-row">
                <div class="form-info">
                  <label class="form-label">启用查询改写</label>
                  <p class="form-hint">使用 LLM 改写优化查询表达</p>
                </div>
                <el-switch v-model="searchConfig.enableQueryRewrite" />
              </div>
            </div>
            
            <div class="form-group">
              <label class="form-label">最大迭代次数</label>
              <el-slider
                v-model="searchConfig.maxIterations"
                :min="1"
                :max="10"
                show-stops
              />
            </div>
            
            <div class="form-group">
              <label class="form-label">最大结果数</label>
              <el-input-number
                v-model="searchConfig.maxResults"
                :min="10"
                :max="500"
                :step="10"
              />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="数据源" name="sources">
          <div class="settings-section">
            <h2 class="section-title">数据源配置</h2>
            
            <div class="sources-list">
              <div
                v-for="source in dataSources"
                :key="source.name"
                class="source-item"
              >
                <div class="source-info">
                  <el-checkbox
                    v-model="source.enabled"
                    :label="source.name"
                  />
                  <span class="source-priority">优先级: {{ source.priority }}</span>
                </div>
                <el-button
                  size="small"
                  :icon="source.enabled ? ArrowUp : ArrowDown"
                  @click="toggleSourcePriority(source.name)"
                />
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="使用统计" name="stats">
          <div class="settings-section">
            <h2 class="section-title">使用统计</h2>
            
            <div class="stats-grid">
              <StatCard
                :icon="Search"
                label="搜索次数"
                :value="stats.searchCount"
              />
              <StatCard
                :icon="Document"
                label="论文浏览"
                :value="stats.paperViews"
              />
              <StatCard
                :icon="Connection"
                label="API 调用"
                :value="stats.apiCalls"
              />
              <StatCard
                :icon="Coin"
                label="Token 消耗"
                :value="stats.tokenUsage"
              />
            </div>
            
            <div class="stats-chart">
              <h3>每日搜索趋势</h3>
              <div class="chart-placeholder">
                <p>趋势图表区域</p>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Check, ArrowUp, ArrowDown, Search, Document, Coin, Connection } from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settings'
import StatCard from '@/components/common/StatCard.vue'

const settingsStore = useSettingsStore()

const activeTab = ref('api')
const saving = ref(false)

const apiConfig = reactive({
  provider: 'openai' as const,
  apiKey: '',
  baseUrl: '',
  model: 'gpt-4-turbo'
})

const searchConfig = reactive({
  enableQueryDecomposition: true,
  enableIterativeSearch: true,
  enableQueryRewrite: true,
  maxIterations: 3,
  maxResults: 100
})

const dataSources = reactive([
  { name: 'arXiv', enabled: true, priority: 1 },
  { name: 'Semantic Scholar', enabled: true, priority: 2 },
  { name: 'PubMed', enabled: false, priority: 3 },
  { name: 'IEEE Xplore', enabled: false, priority: 4 }
])

const stats = reactive({
  searchCount: 42,
  paperViews: 156,
  apiCalls: 89,
  tokenUsage: 125000
})

const saveAllSettings = async () => {
  saving.value = true
  try {
    settingsStore.updateApiConfig(apiConfig)
    settingsStore.updateSearchConfig(searchConfig)
    await settingsStore.saveSettings()
  } finally {
    saving.value = false
  }
}

const toggleSourcePriority = (name: string) => {
  const source = dataSources.find(s => s.name === name)
  if (source) {
    source.priority = source.priority === 1 ? 2 : 1
  }
}

onMounted(async () => {
  await settingsStore.loadSettings()
  Object.assign(apiConfig, settingsStore.apiConfig)
  Object.assign(searchConfig, settingsStore.searchConfig)
  dataSources.splice(0, dataSources.length, ...settingsStore.dataSources)
})
</script>

<style lang="scss" scoped>
.settings-view {
  max-width: 1000px;
  margin: 0 auto;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.settings-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  padding: 24px;
}

.settings-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 24px;
  }
  
  :deep(.el-tabs__item) {
    font-size: 15px;
  }
}

.settings-section {
  max-width: 600px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #F0F0F0;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 8px;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.form-input {
  width: 100%;
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #F5F7FA;
  border-radius: 8px;
}

.form-info {
  flex: 1;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #F5F7FA;
  border-radius: 8px;
}

.source-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.source-priority {
  font-size: 12px;
  color: #909399;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stats-chart {
  h3 {
    font-size: 14px;
    font-weight: 600;
    color: #606266;
    margin: 0 0 16px 0;
  }
}

.chart-placeholder {
  height: 200px;
  background: #F5F7FA;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  p {
    color: #909399;
    font-size: 14px;
  }
}
</style>
