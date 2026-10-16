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
          <el-button v-if="analysis.status === 4" @click="loadTrace(traceVisible = true)">查看链路</el-button>
          <el-button v-if="analysis.status === 4" @click="exportMd">导出 Markdown</el-button>
          <el-button v-if="analysis.status === 4" type="success" @click="exportPdf">导出 PDF</el-button>
        </div>
      </div>
      <div class="desc">{{ analysis.product_description || '（无产品描述）' }}</div>

      <el-divider content-position="left">上传资料（草图 / 参数表 / 权利要求草稿）</el-divider>
      <div class="upload-row">
        <el-upload :show-file-list="false" accept=".png,.jpg,.jpeg,.webp,.bmp" :http-request="(o) => uploadFile(o)">
          <el-button size="small" icon="Picture">上传结构草图</el-button>
        </el-upload>
        <el-upload :show-file-list="false" accept=".xlsx,.xls" :http-request="(o) => uploadFile(o)">
          <el-button size="small" icon="Document">上传参数表</el-button>
        </el-upload>
        <el-upload :show-file-list="false" accept=".pdf,.txt,.md" :http-request="(o) => uploadFile(o)">
          <el-button size="small" icon="Tickets">上传权要草稿</el-button>
        </el-upload>
      </div>
      <div v-if="files.length" class="file-list">
        <el-tag v-for="f in files" :key="f.id" size="small" closable @close="removeFile(f)" :type="fileTagType(f.type)">
          {{ fileTypeText(f.type) }}: {{ f.name }}
        </el-tag>
      </div>
    </el-card>

    <!-- 追问对话框 -->
    <el-dialog v-model="clarifyVisible" title="补充产品信息" width="600px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" style="margin-bottom:14px" title="系统发现以下信息不明确，请补充后再继续分析" />
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

    <!-- Agent 链路回放 -->
    <el-dialog v-model="traceVisible" title="Agent 链路回放" width="760px">
      <el-timeline>
        <el-timeline-item v-for="t in trace" :key="t.id" :timestamp="`${t.create_time} · ${t.duration_ms}ms`"
                          :type="t.status === 1 ? 'success' : t.status === 2 ? 'warning' : 'danger'">
          <div class="trace-node">
            <b>{{ nodeName(t.node) }}</b>（{{ t.intent || '-' }}）
            <el-tag size="small" :type="{1:'success',2:'warning',3:'danger'}[t.status]">{{ {1:'成功',2:'降级',3:'失败'}[t.status] }}</el-tag>
          </div>
          <el-collapse v-if="t.input || t.output || t.tool_calls">
            <el-collapse-item title="查看输入输出">
              <div v-if="t.input" class="trace-io"><b>输入：</b>{{ JSON.stringify(t.input) }}</div>
              <div v-if="t.output" class="trace-io"><b>输出：</b>{{ JSON.stringify(t.output) }}</div>
              <div v-if="t.tool_calls" class="trace-io"><b>工具调用：</b>{{ JSON.stringify(t.tool_calls) }}</div>
            </el-collapse-item>
          </el-collapse>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>

    <!-- Dossier -->
    <DossierView v-if="dossier.markdown" :markdown="dossier.markdown" :risk-summary="dossier.summary" />
    <el-empty v-else-if="analysis.status === 1" description="尚未运行，可先上传资料，再点击「运行分析」" />
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
const traceVisible = ref(false)
const questions = ref([])
const answers = reactive({})
const dossier = reactive({ markdown: '', summary: null })
const files = ref([])
const trace = ref([])

const STATUS = { 1: '草稿', 2: '进行中', 3: '待追问', 4: '完成', 5: '失败' }
const NODE_NAMES = { fact: '① 事实提取', planner: '② 检索规划', searcher: '③ 检索执行', family: '④ 家族解析', status: '⑤ 法律状态', parser: '⑥ 权要解析', chart: '⑦ 特征比对', reviewer: '⑧ 卷宗生成' }
function statusText(s) { return STATUS[s] || s }
function statusType(s) { return { 1: 'info', 2: 'primary', 3: 'warning', 4: 'success', 5: 'danger' }[s] || 'info' }
function nodeName(n) { return NODE_NAMES[n] || n }
function fileTypeText(t) { return { image: '草图', excel: '参数表', pdf: '权要草稿', text: '文本' }[t] || t }
function fileTagType(t) { return { image: 'primary', excel: 'warning', pdf: 'info', text: 'info' }[t] || 'info' }

async function load() {
  loading.value = true
  try {
    const res = await request.get(`/api/fto/analysis/${id}`)
    analysis.value = res.data
    await loadFiles()
    if (analysis.value.status === 4) await loadDossier()
  } finally { loading.value = false }
}
async function loadFiles() {
  try { const res = await request.get(`/api/fto/analysis/${id}/files`); files.value = res.data || [] } catch { /* ignore */ }
}
async function loadDossier() {
  const res = await request.get(`/api/fto/analysis/${id}/dossier`)
  dossier.markdown = res.data.dossier_markdown || ''
  dossier.summary = res.data.risk_summary || null
}
async function loadTrace() {
  const res = await request.get(`/api/fto/analysis/${id}/trace`)
  trace.value = res.data || []
}

async function uploadFile(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  fd.append('analysis_id', id)
  const res = await request.post('/api/files/upload', fd)
  files.value.push({ id: res.data.id, type: res.data.type, name: res.data.name })
  ElMessage.success('上传成功')
}
async function removeFile(f) {
  files.value = files.value.filter(x => x.id !== f.id)
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
.upload-row { display: flex; gap: 10px; }
.file-list { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.trace-node { font-size: 14px; margin-bottom: 4px; }
.trace-io { font-size: 12px; color: #606266; word-break: break-all; margin-bottom: 6px; }
</style>
