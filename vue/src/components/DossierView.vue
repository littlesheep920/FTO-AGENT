<template>
  <div class="dossier">
    <el-card v-if="riskSummary" class="risk-cards">
      <div class="risk-grid">
        <div class="risk-item risk-high"><div class="num">{{ riskSummary.high }}</div><div class="label">高风险</div></div>
        <div class="risk-item risk-mid"><div class="num">{{ riskSummary.medium }}</div><div class="label">中风险</div></div>
        <div class="risk-item risk-low"><div class="num">{{ riskSummary.low }}</div><div class="label">低风险</div></div>
        <div class="risk-item risk-ex"><div class="num">{{ riskSummary.excluded }}</div><div class="label">排除</div></div>
      </div>
    </el-card>
    <div class="md-body" v-html="html"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  markdown: { type: String, default: '' },
  riskSummary: { type: Object, default: null },
})

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const html = computed(() => {
  let h = md.render(props.markdown || '')
  h = h
    .replace(/命中/g, '<span class="tag tag-hit">命中</span>')
    .replace(/缺失/g, '<span class="tag tag-miss">缺失</span>')
    .replace(/部分/g, '<span class="tag tag-part">部分</span>')
    .replace(/存疑/g, '<span class="tag tag-doubt">存疑</span>')
    .replace(/高风险/g, '<span class="tag tag-high">高风险</span>')
    .replace(/中风险/g, '<span class="tag tag-mid">中风险</span>')
    .replace(/低风险/g, '<span class="tag tag-low">低风险</span>')
  return h
})
</script>

<style scoped>
.risk-cards { margin-bottom: 16px; }
.risk-grid { display: flex; gap: 12px; }
.risk-item { flex: 1; text-align: center; padding: 14px; border-radius: 8px; color: #fff; }
.risk-item .num { font-size: 28px; font-weight: 700; }
.risk-item .label { font-size: 13px; opacity: .9; }
.risk-high { background: #f56c6c; }
.risk-mid { background: #e6a23c; }
.risk-low { background: #67c23a; }
.risk-ex { background: #909399; }
</style>

<style>
.md-body { background: #fff; padding: 24px; border-radius: 8px; line-height: 1.7; }
.md-body h1 { font-size: 22px; border-bottom: 2px solid #2f6bff; padding-bottom: 8px; }
.md-body h2 { font-size: 17px; margin-top: 24px; border-left: 4px solid #2f6bff; padding-left: 10px; }
.md-body table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
.md-body th, .md-body td { border: 1px solid #e4e7ed; padding: 6px 10px; text-align: left; }
.md-body th { background: #eef2f7; }
.md-body blockquote { border-left: 4px solid #e6a23c; background: #fdf6ec; margin: 8px 0; padding: 8px 12px; color: #b45309; }
.tag { display: inline-block; padding: 0 6px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.tag-hit { background: #e8f8ee; color: #22c55e; }
.tag-miss { background: #fdeaea; color: #ef4444; }
.tag-part { background: #fff4e8; color: #ff8a00; }
.tag-doubt { background: #f1f2f3; color: #909399; }
.tag-high { background: #fdeaea; color: #ef4444; }
.tag-mid { background: #fff4e8; color: #ff8a00; }
.tag-low { background: #e8f8ee; color: #22c55e; }
</style>
