<template><div class="paper-count">已发现 <strong>{{ count }}</strong> 篇论文</div></template>
<script setup lang="ts">
import type { AcademicPaper } from '@/types'
const props = defineProps<{ data: unknown }>()
const count = (() => {
  if (Array.isArray(props.data)) return props.data.length
  if (props.data && typeof props.data === 'object') {
    const d = props.data as { count?: number; papers?: AcademicPaper[]; papersCount?: number; papers_count?: number }
    if (typeof d.count === 'number') return d.count
    if (typeof d.papersCount === 'number') return d.papersCount
    if (typeof d.papers_count === 'number') return d.papers_count
    if (Array.isArray(d.papers)) return d.papers.length
  }
  return 0
})()
</script>
<style scoped>.paper-count{font-size:14px;color:#606266}.paper-count strong{color:#409eff;font-size:18px}</style>
