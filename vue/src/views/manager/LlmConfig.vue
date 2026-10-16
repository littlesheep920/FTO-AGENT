<template>
  <div>
    <el-card>
      <template #header><h3 style="margin:0">模型配置</h3></template>
      <el-form label-width="120px" style="max-width:560px" v-loading="loading">
        <el-form-item label="Provider">
          <el-input v-model="form.provider" placeholder="如 deepseek" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="Chat Model">
          <el-input v-model="form.chat_model" placeholder="deepseek-chat" />
        </el-form-item>
        <el-form-item label="Vision Model">
          <el-input v-model="form.vision_model" placeholder="视觉模型（可选）" />
        </el-form-item>
        <el-form-item label="Embed Model">
          <el-input v-model="form.embed_model" placeholder="text-embedding-3-small" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password
                    :placeholder="keyPlaceholder" />
          <div class="muted">{{ keyHint }}</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const loading = ref(false)
const saving = ref(false)
const form = ref({ provider: '', base_url: '', chat_model: '', vision_model: '', embed_model: '', api_key: '', enabled: 1 })
const keyInfo = ref({ configured: false, source: 'none' })

const keyPlaceholder = computed(() => (keyInfo.value.configured ? '留空则保持现有 Key' : '未配置 Key（走规则引擎降级）'))
const keyHint = computed(() => {
  if (keyInfo.value.source === 'env') return '当前 Key 来自环境变量（不落库）'
  if (keyInfo.value.source === 'database') return '当前 Key 已保存在数据库'
  return '未配置'
})

async function load() {
  loading.value = true
  try {
    const res = await request.get('/api/fto/llm/config')
    const d = res.data
    form.value = { provider: d.provider, base_url: d.base_url, chat_model: d.chat_model, vision_model: d.vision_model, embed_model: d.embed_model, api_key: '', enabled: d.enabled }
    keyInfo.value = { configured: d.api_key_configured, source: d.api_key_source }
  } finally { loading.value = false }
}
async function save() {
  saving.value = true
  try {
    await request.put('/api/fto/llm/config', form.value)
    ElMessage.success('已保存')
    load()
  } finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.muted { color: #909399; font-size: 12px; margin-top: 4px; }
</style>
