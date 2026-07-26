<template><div class="paper-count">已发现 <strong>{{ count }}</strong> 篇论文</div></template>
<script setup lang="ts">
import type { AcademicPaper } from '@/types'
const props = defineProps<{ data: unknown }>()
const count = Array.isArray(props.data) ? props.data.length : (((props.data as { count?: number; papers?: AcademicPaper[] })?.count) ?? (props.data as { papers?: AcademicPaper[] })?.papers?.length ?? 0)
</script>
<style scoped>.paper-count{font-size:14px;color:#606266}.paper-count strong{color:#409eff;font-size:18px}</style>
