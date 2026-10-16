<template>
  <div>
    <div class="toolbar">
      <h2>我的分析</h2>
      <el-button type="primary" @click="dialogVisible = true">新建分析</el-button>
    </div>

    <el-table :data="list" v-loading="loading" @row-click="(r) => $router.push(`/analysis/${r.id}`)" class="table">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="风险" width="200">
        <template #default="{ row }">
          <template v-if="row.risk_summary">
            <el-tag size="small" type="danger">高{{ row.risk_summary.high }}</el-tag>
            <el-tag size="small" type="warning">中{{ row.risk_summary.medium }}</el-tag>
            <el-tag size="small" type="success">低{{ row.risk_summary.low }}</el-tag>
            <el-tag size="small" type="info">排除{{ row.risk_summary.excluded }}</el-tag>
          </template>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" label="创建时间" width="170" />
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建 FTO 分析" width="560px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="如：控弯导管 FTO 分析" />
        </el-form-item>
        <el-form-item label="产品描述">
          <el-input v-model="form.product_description" type="textarea" :rows="5"
                    placeholder="描述你的产品，例如：一种控弯导管，远端可弯曲段由拉线机构控制弯曲方向，管体材料为聚氨酯…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建并进入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '../../utils/request'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const creating = ref(false)
const form = ref({ title: '', product_description: '' })
const router = useRouter()

const STATUS = { 1: '草稿', 2: '进行中', 3: '待追问', 4: '完成', 5: '失败' }
function statusText(s) { return STATUS[s] || s }
function statusType(s) { return { 1: 'info', 2: 'primary', 3: 'warning', 4: 'success', 5: 'danger' }[s] || 'info' }

async function load() {
  loading.value = true
  try { const res = await request.get('/api/fto/analysis/list'); list.value = res.data || [] } finally { loading.value = false }
}
async function create() {
  creating.value = true
  try {
    const res = await request.post('/api/fto/analysis', form.value)
    dialogVisible.value = false
    router.push(`/analysis/${res.data.id}`)
  } finally { creating.value = false }
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.table { cursor: pointer; background: #fff; }
.muted { color: #c0c4cc; }
</style>
