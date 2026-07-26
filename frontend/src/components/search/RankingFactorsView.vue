<template><div class="ranking-factors"><span v-for="(value, key) in factors" :key="key">{{ key }}: {{ (Number(value) * 100).toFixed(0) }}%</span></div></template>
<script setup lang="ts">
import type { RankingFactors } from '@/types'
const props = defineProps<{ data: unknown }>()
const factors = ((props.data as { rankingFactors?: RankingFactors })?.rankingFactors || props.data || {}) as RankingFactors
</script>
<style scoped>.ranking-factors{display:flex;gap:12px;flex-wrap:wrap;color:#606266;font-size:13px}.ranking-factors span{background:#fff;padding:4px 8px;border-radius:4px}</style>
