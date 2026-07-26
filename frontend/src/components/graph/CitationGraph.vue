<template>
  <div class="citation-graph">
    <div class="graph-header">
      <h3 class="graph-title">引用关系图谱</h3>
      <div class="graph-controls">
        <el-button size="small" @click="resetZoom">
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
        <el-button size="small" @click="zoomIn">
          <el-icon><ZoomIn /></el-icon>
        </el-button>
        <el-button size="small" @click="zoomOut">
          <el-icon><ZoomOut /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="graph-container" ref="containerRef">
      <svg ref="svgRef" class="graph-svg"></svg>
      
      <div v-if="loading" class="loading-overlay">
        <LoadingSpinner size="large" text="加载图谱数据..." />
      </div>
    </div>
    
    <div class="graph-legend">
      <div class="legend-item">
        <span class="legend-dot center"></span>
        <span>中心论文</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot reference"></span>
        <span>参考文献</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot cited-by"></span>
        <span>被引文献</span>
      </div>
    </div>
    
    <transition name="fade">
      <div v-if="selectedNode" class="node-detail">
        <div class="detail-header">
          <h4>{{ selectedNode.title || selectedNode.label || selectedNode.id }}</h4>
          <el-button :icon="Close" text circle @click="selectedNode = null" />
        </div>
        <div class="detail-content">
          <div class="detail-row">
            <span class="detail-label">类型</span>
            <el-tag size="small" :type="nodeTypeTag">{{ nodeTypeText }}</el-tag>
          </div>
          <div class="detail-row" v-if="selectedNode.year">
            <span class="detail-label">年份</span>
            <span>{{ selectedNode.year }}</span>
          </div>
          <div class="detail-row" v-if="selectedNode.citationCount">
            <span class="detail-label">引用数</span>
            <span>{{ selectedNode.citationCount }}</span>
          </div>
          <div class="detail-row" v-if="selectedNode.relevance">
            <span class="detail-label">相关性</span>
            <span>{{ (selectedNode.relevance * 100).toFixed(0) }}%</span>
          </div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" size="small" @click="viewPaper">查看详情</el-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'
import { RefreshLeft, ZoomIn, ZoomOut, Close } from '@element-plus/icons-vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { GraphNode, GraphEdge } from '@/types'

const props = defineProps<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  sessionId?: string
}>()

const router = useRouter()

const svgRef = ref<SVGSVGElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const selectedNode = ref<GraphNode | null>(null)

let simulation: d3.Simulation<GraphNode, GraphEdge> | null = null
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let g: d3.Selection<SVGGElement, unknown, null, undefined> | null = null
let zoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null

const nodeTypeText = computed(() => {
  if (!selectedNode.value) return ''
  const typeMap: Record<string, string> = {
    center: '中心论文',
    reference: '参考文献',
    citedBy: '被引文献'
  }
  return typeMap[selectedNode.value.type] || selectedNode.value.type
})

const nodeTypeTag = computed(() => {
  if (!selectedNode.value) return ''
  const typeMap: Record<string, string> = {
    center: 'primary',
    reference: 'success',
    citedBy: 'warning'
  }
  return typeMap[selectedNode.value.type] || 'info'
})

const initGraph = () => {
  if (!svgRef.value || !containerRef.value || props.nodes.length === 0) return
  
  const width = containerRef.value.clientWidth
  const height = 500
  
  svg = d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)
  
  svg.selectAll('*').remove()
  
  const defs = svg.append('defs')
  
  const gradient = defs.append('linearGradient')
    .attr('id', 'link-gradient')
    .attr('gradientUnits', 'userSpaceOnUse')
  
  gradient.append('stop')
    .attr('offset', '0%')
    .attr('stop-color', '#67C23A')
  
  gradient.append('stop')
    .attr('offset', '100%')
    .attr('stop-color', '#409EFF')
  
  g = svg.append('g')
  
  zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.3, 3])
    .on('zoom', (event) => {
      g?.attr('transform', event.transform)
    })
  
  svg.call(zoom)
  
  const nodesCopy = props.nodes.map(n => ({ ...n }))
  const edgesCopy = props.edges.map(e => ({ ...e }))
  
  simulation = d3.forceSimulation(nodesCopy)
    .force('link', d3.forceLink<GraphNode, GraphEdge>(edgesCopy)
      .id(d => d.id)
      .distance(120))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(50))
  
  const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(edgesCopy)
    .join('line')
    .attr('stroke', 'url(#link-gradient)')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', 2)
  
  const nodeGroup = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(nodesCopy)
    .join('g')
    .attr('class', 'node')
    .call(d3.drag<SVGGElement, GraphNode>()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended) as any)
    .on('click', (event, d) => {
      event.stopPropagation()
      selectedNode.value = d
    })
  
  nodeGroup.append('circle')
    .attr('r', d => d.type === 'center' ? 30 : 20)
    .attr('fill', d => nodeColor(d.type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
  
  nodeGroup.append('text')
    .text(d => {
      const label = d.title || d.label || d.id
      return label.substring(0, 15) + (label.length > 15 ? '...' : '')
    })
    .attr('x', 0)
    .attr('y', d => d.type === 'center' ? 45 : 35)
    .attr('text-anchor', 'middle')
    .attr('font-size', '11px')
    .attr('fill', '#606266')
  
  nodeGroup.append('text')
    .text(d => d.year?.toString() || '')
    .attr('x', 0)
    .attr('y', d => d.type === 'center' ? 58 : 48)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', '#909399')
  
  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)
    
    nodeGroup.attr('transform', d => `translate(${d.x},${d.y})`)
  })
  
  function dragstarted(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
    if (!event.active) simulation?.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
  }
  
  function dragged(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
    d.fx = event.x
    d.fy = event.y
  }
  
  function dragended(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) {
    if (!event.active) simulation?.alphaTarget(0)
    d.fx = null
    d.fy = null
  }
}

const nodeColor = (type: string) => {
  const colors: Record<string, string> = {
    center: '#409EFF',
    reference: '#67C23A',
    citedBy: '#E6A23C'
  }
  return colors[type] || '#909399'
}

const resetZoom = () => {
  if (svg && zoom) {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity)
  }
}

const zoomIn = () => {
  if (svg && zoom) {
    svg.transition().duration(300).call(zoom.scaleBy, 1.3)
  }
}

const zoomOut = () => {
  if (svg && zoom) {
    svg.transition().duration(300).call(zoom.scaleBy, 0.7)
  }
}

const viewPaper = () => {
  if (selectedNode.value) {
    router.push({ name: 'PaperDetail', params: { paperId: selectedNode.value.id } })
  }
}

watch(() => props.nodes, () => {
  initGraph()
}, { deep: true })

onMounted(() => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
    initGraph()
  }, 500)
})

onUnmounted(() => {
  simulation?.stop()
})

defineExpose({ initGraph })
</script>

<style lang="scss" scoped>
.citation-graph {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: relative;
}

.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.graph-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.graph-controls {
  display: flex;
  gap: 8px;
}

.graph-container {
  position: relative;
  width: 100%;
  height: 500px;
  background: linear-gradient(135deg, #F5F7FA 0%, #E4E8EC 100%);
  border-radius: 8px;
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
  
  :deep(.node) {
    &:hover circle {
      filter: brightness(1.1);
    }
  }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
}

.graph-legend {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #F0F0F0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  
  &.center {
    background: #409EFF;
  }
  
  &.reference {
    background: #67C23A;
  }
  
  &.cited-by {
    background: #E6A23C;
  }
}

.node-detail {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 280px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
  
  h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    flex: 1;
    margin-right: 8px;
    line-height: 1.4;
  }
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.detail-label {
  color: #909399;
}

.detail-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #F0F0F0;
  
  .el-button {
    width: 100%;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}
</style>
