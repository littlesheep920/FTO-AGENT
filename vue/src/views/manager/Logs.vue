<template>
  <div>
    <el-card>
      <template #header><h3 style="margin:0">Agent 运行日志</h3></template>
      <el-table :data="records" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="analysis_id" label="分析ID" width="90" />
        <el-table-column prop="node" label="节点" width="110" />
        <el-table-column prop="intent" label="意图" width="110" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="{1:'success',2:'warning',3:'danger'}[row.status] || 'info'">
              {{ {1:'成功',2:'降级',3:'失败'}[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
        <el-table-column prop="create_time" label="时间" width="170" />
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="size" :total="total"
                     layout="total, prev, pager, next" @current-change="load" style="margin-top:12px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminRequest as request } from '../../utils/request'

const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await request.get('/api/fto/agent/logs', { params: { page: page.value, size: size.value } })
    records.value = res.data.records || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
onMounted(load)
</script>
