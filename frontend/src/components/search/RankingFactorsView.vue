<template><div class="ranking-factors"><span v-for="(value, key) in factors" :key="key">{{ key }}: {{ (Number(value) * 100).toFixed(0) }}%</span><span v-if="Object.keys(factors).length === 0" class="empty-text">无排序数据</span></div></template>
<script setup lang="ts">
import type { RankingFactors } from '@/types'
const props = defineProps<{ data: unknown }>()
const raw = ((props.data as { rankingFactors?: RankingFactors })?.rankingFactors || props.data || {}) as Record<string, unknown>
// Only show numeric values (filter out strings like stop_reason, type, etc.)
const factors = Object.fromEntries(
  Object.entries(raw).filter(([_, v]) => typeof v === 'number' && !Number.isNaN(v))
) as RankingFactors
</script>
<style scoped>.ranking-factors{display:flex;gap:12px;flex-wrap:wrap;color:#606266;font-size:13px}.ranking-factors span{background:#fff;padding:4px 8px;border-radius:4px}.empty-text{color:#C0C4CC;font-style:italic}</style>
