<template>
  <div v-loading="loading">
    <el-card class="head-card">
      <div class="head-row">
        <div>
          <h2>{{ analysis.title || '未命名分析' }}</h2>
          <el-tag :type="statusType(analysis.status)">{{ statusText(analysis.status) }}</el-tag>
          <span class="muted" style="margin-left:10px">ID: {{ analysis.id }}</span>
        </div>
        <div>
          <el-button type="primary" :loading="running" @click="run">运行分析</el-button>
          <el-button v-if="analysis.status === 4" @click="exportMd">导出 Markdown</el-button>
          <el-button v-if="analysis.status === 4" type="success" @click="exportPdf">导出 PDF</el-button>
        </div>
      </div>
      <div class="desc">{{ analysis.product_description || '（无产品描述）' }}</div>
    </el-card>

    <!-- 追问对话框 -->
    <el-dialog v-model="clarifyVisible" title="补充产品信息" width="600px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" style="margin-bottom:14px"
                title="系统发现以下信息不明确，请补充后再继续分析" />
      <el-form label-position="top">
        <el-form-item v-for="q in questions" :key="q.fact_id" :label="q.question">
          <el-input v-model="answers[q.fact_id]" type="textarea" :rows="2" placeholder="请输入补充说明（可留空）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="clarifyVisible = false">稍后再说</el-button>
        <el-button type="primary" :loading="running" @click="submitClarify">提交并继续</el-button>
      </template>
    </el-dialog>

    <!-- Dossier -->
    <DossierView v-if="dossier.markdown" :markdown="dossier.markdown" :risk-summary="dossier.summary" />
    <el-empty v-else-if="analysis.status === 1" description="尚未运行，点击右上角「运行分析」开始" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'
import DossierView from '../../components/DossierView.vue'

const route = useRoute()
const id = route.params.id
const analysis = ref({})
const loading = ref(false)
const running = ref(false)
const clarifyVisible = ref(false)
const questions = ref([])
const answers = reactive({})
const dossier = reactive({ markdown: '', summary: null })

const STATUS = { 1: '草稿', 2: '进行中', 3: '待追问', 4: '完成', 5: '失败' }
function statusText(s) { return STATUS[s] || s }
function statusType(s) { return { 1: 'info', 2: 'primary', 3: 'warning', 4: 'success', 5: 'danger' }[s] || 'info' }

async function load() {
  loading.value = true
  try {
    const res = await request.get(`/api/fto/analysis/${id}`)
    analysis.value = res.data
    if (analysis.value.status === 4) await loadDossier()
  } finally { loading.value = false }
}

async function loadDossier() {
  const res = await request.get(`/api/fto/analysis/${id}/dossier`)
  dossier.markdown = res.data.dossier_markdown || ''
  dossier.summary = res.data.risk_summary || null
}

async function run() {
  running.value = true
  try {
    const res = await request.post(`/api/fto/analysis/${id}/run`)
    const d = res.data || {}
    analysis.value.status = d.status
    if (d.need_clarification) {
      questions.value = d.questions || []
      for (const q of questions.value) if (!(q.fact_id in answers)) answers[q.fact_id] = ''
      clarifyVisible.value = true
    } else if (d.status === 4) {
      ElMessage.success('分析完成')
      await loadDossier()
    }
  } finally { running.value = false }
}

async function submitClarify() {
  running.value = true
  try {
    const list = questions.value.map((q) => ({ fact_id: q.fact_id, answer: answers[q.fact_id] || '' }))
    const res = await request.post(`/api/fto/analysis/${id}/clarify`, { answers: list })
    clarifyVisible.value = false
    const d = res.data || {}
    analysis.value.status = d.status
    if (d.need_clarification) {
      questions.value = d.questions || []
      clarifyVisible.value = true
    } else if (d.status === 4) {
      ElMessage.success('分析完成')
      await loadDossier()
    }
  } finally { running.value = false }
}

function downloadBlob(res, filename) {
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
async function exportMd() {
  const res = await request.get(`/api/fto/analysis/${id}/export/markdown`, { responseType: 'blob' })
  downloadBlob(res, `FTO_dossier_${id}.md`)
}
async function exportPdf() {
  const res = await request.get(`/api/fto/analysis/${id}/export/pdf`, { responseType: 'blob' })
  downloadBlob(res, `FTO_dossier_${id}.pdf`)
}

onMounted(load)
</script>

<style scoped>
.head-card { margin-bottom: 16px; }
.head-row { display: flex; justify-content: space-between; align-items: center; }
.desc { margin-top: 12px; color: #606266; background: #f5f7fa; padding: 10px 14px; border-radius: 6px; white-space: pre-wrap; }
.muted { color: #909399; }
</style>
