<template>
  <div class="graph-view">
    <div class="graph-header">
      <div class="header-left">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h1 class="page-title">引用关系图谱</h1>
      </div>
      <div class="header-actions">
        <el-button @click="refreshGraph">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <div class="graph-content">
      <CitationGraph
        ref="graphRef"
        :nodes="graphData.nodes"
        :edges="graphData.edges"
        :session-id="sessionId"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { getCitationGraph } from '@/api'
import CitationGraph from '@/components/graph/CitationGraph.vue'
import type { GraphData } from '@/types'

const router = useRouter()
const route = useRoute()
const graphRef = ref<InstanceType<typeof CitationGraph> | null>(null)

const sessionId = ref('')
const graphData = ref<GraphData>({ nodes: [], edges: [] })
const loading = ref(false)

const goBack = () => {
  router.back()
}

const refreshGraph = async () => {
  loading.value = true
  try {
    const data = await getCitationGraph(sessionId.value)
    graphData.value = data
    graphRef.value?.initGraph()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  sessionId.value = route.params.sessionId as string
  if (sessionId.value) {
    loading.value = true
    try {
      const data = await getCitationGraph(sessionId.value)
      graphData.value = data
    } finally {
      loading.value = false
    }
  }
})
</script>

<style lang="scss" scoped>
.graph-view {
  min-height: calc(100vh - 100px);
}

.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  
  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.graph-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
</style>
