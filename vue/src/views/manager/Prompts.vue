<template>
  <div>
    <el-card>
      <template #header><h3 style="margin:0">Prompt 管理（在线编辑，保存即热生效）</h3></template>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="scene" label="场景" width="150" />
        <el-table-column prop="content" label="内容" min-width="300" show-overflow-tooltip />
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="70" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="edit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="`编辑 Prompt - ${form.scene}`" width="720px">
      <el-form label-width="60px">
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="12" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ scene: '', content: '', enabled: 1 })

async function load() {
  loading.value = true
  try { const res = await request.get('/api/fto/prompt'); list.value = res.data || [] } finally { loading.value = false }
}
function edit(row) {
  form.value = { scene: row.scene, content: row.content, enabled: row.enabled }
  dialogVisible.value = true
}
async function save() {
  saving.value = true
  try {
    await request.put('/api/fto/prompt', form.value)
    ElMessage.success('已保存（热生效）')
    dialogVisible.value = false
    load()
  } finally { saving.value = false }
}
onMounted(load)
</script>
