<template>
  <div class="subquery-list">
    <el-tag v-for="item in items" :key="itemKey(item)" size="small" effect="plain">{{ itemLabel(item) }}</el-tag>
    <span v-if="!items.length" class="empty">暂无子查询</span>
  </div>
</template>
<script setup lang="ts">
import type { SubQuery } from '@/types'
defineProps<{ data: unknown }>()
const props = defineProps<{ data: unknown }>()
const items = (Array.isArray(props.data) ? props.data : ((props.data as { subqueries?: SubQuery[] })?.subqueries || [])) as SubQuery[]
function itemKey(item: SubQuery) {
  return item.id ?? item.query ?? item.text ?? JSON.stringify(item)
}
function itemLabel(item: SubQuery) {
  return item.query ?? item.text ?? ''
}
</script>
<style scoped>.subquery-list{display:flex;flex-wrap:wrap;gap:8px}.empty{color:#909399;font-size:13px}</style>
