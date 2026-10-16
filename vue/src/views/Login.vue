<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">FTO 专利自由实施分析系统</h2>
      <p class="subtitle">控弯导管领域 · 多 Agent 自由实施分析</p>
      <el-form @submit.prevent>
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" size="large" show-password @keyup.enter="doLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="doLogin">登 录</el-button>
        <div class="tip">默认管理员：admin / admin123</div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const username = ref('')
const password = ref('')
const loading = ref(false)
const store = useUserStore()
const router = useRouter()
const route = useRoute()

async function doLogin() {
  if (!username.value || !password.value) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    await store.login(username.value, password.value)
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #2f6bff 0%, #6a5cff 100%); }
.login-card { width: 400px; }
.title { text-align: center; margin: 8px 0 4px; }
.subtitle { text-align: center; color: #909399; font-size: 13px; margin-bottom: 20px; }
.tip { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 12px; }
</style>
