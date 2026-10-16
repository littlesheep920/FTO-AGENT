<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">FTO 专利自由实施分析系统</h2>
      <p class="subtitle">控弯导管领域 · 多 Agent 自由实施分析</p>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="用户登录" name="user" />
        <el-tab-pane label="管理员登录" name="admin" />
      </el-tabs>
      <el-form @submit.prevent>
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" size="large" show-password @keyup.enter="doLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="doLogin">
          {{ mode === 'admin' ? '管理员登录' : '登 录' }}
        </el-button>
        <div class="tip">
          <template v-if="mode === 'user'">还没有账号？<el-link type="primary" @click="registerVisible = true">注册</el-link></template>
        </div>
      </el-form>
    </el-card>

    <el-dialog v-model="registerVisible" title="注册" width="420px">
      <el-form label-width="60px">
        <el-form-item label="用户名"><el-input v-model="reg.username" /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="reg.nickname" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="reg.password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="doRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const mode = ref('user')
const username = ref('')
const password = ref('')
const loading = ref(false)
const registerVisible = ref(false)
const reg = ref({ username: '', nickname: '', password: '' })
const store = useUserStore()
const router = useRouter()
const route = useRoute()

async function doLogin() {
  if (!username.value || !password.value) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    if (mode.value === 'admin') {
      await store.adminLogin(username.value, password.value)
      ElMessage.success('管理员登录成功')
      router.push('/admin/logs')
    } else {
      await store.login(username.value, password.value)
      ElMessage.success('登录成功')
      router.push(route.query.redirect || '/')
    }
  } finally { loading.value = false }
}

async function doRegister() {
  if (reg.value.username.length < 3 || reg.value.password.length < 6) { ElMessage.warning('用户名至少 3 位，密码至少 6 位'); return }
  loading.value = true
  try {
    await store.register(reg.value.username, reg.value.password, reg.value.nickname || reg.value.username)
    ElMessage.success('注册成功')
    registerVisible.value = false
    router.push('/')
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-wrap { display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #2f6bff 0%, #6a5cff 100%); }
.login-card { width: 400px; }
.title { text-align: center; margin: 8px 0 4px; }
.subtitle { text-align: center; color: #909399; font-size: 13px; margin-bottom: 8px; }
.tip { text-align: center; color: #c0c4cc; font-size: 13px; margin-top: 12px; }
</style>
