<template>
  <div class="history-view">
    <div class="history-header">
      <h1 class="page-title">搜索历史</h1>
      <el-button @click="refreshHistory" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <div v-if="loading" class="loading-state">
      <LoadingSpinner size="large" text="加载历史记录..." />
    </div>
    
    <template v-else>
      <div v-if="groupedHistory.length > 0" class="history-list">
        <div v-for="group in groupedHistory" :key="group.date" class="history-group">
          <div class="group-header">
            <el-icon><Calendar /></el-icon>
            <span>{{ group.date }}</span>
            <span class="group-count">{{ group.records.length }} 条记录</span>
          </div>
          
          <div class="group-records">
            <div
              v-for="record in group.records"
              :key="record.id"
              class="history-card"
            >
              <div class="record-main">
                <div class="record-query">
                  <el-icon><Search /></el-icon>
                  <span>{{ record.query }}</span>
                </div>
                <div class="record-meta">
                  <span class="meta-item">
                    <el-icon><Document /></el-icon>
                    {{ record.papersCount ?? record.paperCount ?? 0 }} 篇论文
                  </span>
                  <span class="meta-item">
                    <el-icon><Timer /></el-icon>
                    {{ (record.duration ?? 0).toFixed(1) }}s
                  </span>
                  <span class="meta-item">
                    <el-icon><Coin /></el-icon>
                    ${{ (record.cost ?? 0).toFixed(2) }}
                  </span>
                </div>
              </div>
              
              <div class="record-actions">
                <el-button size="small" type="primary" @click="viewResults(record)">
                  查看结果
                </el-button>
                <el-button size="small" @click="rerunSearch(record)">
                  重新搜索
                </el-button>
                <el-button size="small" type="danger" text @click="deleteRecord(record.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="empty-state">
        <el-empty description="暂无搜索历史">
          <el-button type="primary" @click="goToSearch">开始搜索</el-button>
        </el-empty>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Calendar, Search, Document, Timer, Coin, Delete } from '@element-plus/icons-vue'
import { deleteHistoryRecord, getSearchHistory } from '@/api'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { HistoryRecord } from '@/types'

const router = useRouter()

const loading = ref(false)
const history = ref<HistoryRecord[]>([])

const groupedHistory = computed(() => {
  const groups: Record<string, HistoryRecord[]> = {}
  
  history.value.forEach(record => {
    const date = new Date(record.createdAt).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
    
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(record)
  })
  
  return Object.entries(groups).map(([date, records]) => ({
    date,
    records
  }))
})

const refreshHistory = async () => {
  loading.value = true
  try {
    history.value = await getSearchHistory()
  } finally {
    loading.value = false
  }
}

const viewResults = (record: HistoryRecord) => {
  router.push({ name: 'Results', params: { sessionId: record.sessionId ?? record.id } })
}

const rerunSearch = async (record: HistoryRecord) => {
  router.push({ path: '/', query: { q: record.query } })
}

const deleteRecord = async (id: string) => {
  await deleteHistoryRecord(id)
  history.value = history.value.filter(r => r.id !== id)
}

const goToSearch = () => {
  router.push({ name: 'Search' })
}

onMounted(() => {
  refreshHistory()
})
</script>

<style lang="scss" scoped>
.history-view {
  max-width: 1000px;
  margin: 0 auto;
}

.history-header {
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

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
  background: white;
  border-radius: 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.history-group {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.05) 0%, rgba(64, 158, 255, 0.1) 100%);
  border-bottom: 1px solid #F0F0F0;
  font-size: 14px;
  color: #606266;
  
  .el-icon {
    color: #409EFF;
  }
  
  .group-count {
    margin-left: auto;
    font-size: 12px;
    color: #909399;
  }
}

.group-records {
  display: flex;
  flex-direction: column;
}

.history-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #F0F0F0;
  transition: background 0.3s;
  
  &:last-child {
    border-bottom: none;
  }
  
  &:hover {
    background: #F5F7FA;
  }
}

.record-main {
  flex: 1;
}

.record-query {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 8px;
  
  .el-icon {
    color: #409EFF;
  }
}

.record-meta {
  display: flex;
  gap: 20px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #909399;
  
  .el-icon {
    font-size: 14px;
  }
}

.record-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  padding: 60px;
  background: white;
  border-radius: 12px;
  text-align: center;
}
</style>
