<template>
  <el-container class="app">
    <el-header v-if="store.isLoggedIn" class="header">
      <div class="logo" @click="$router.push('/')">FTO 专利自由实施分析系统</div>
      <el-menu mode="horizontal" :default-active="$route.path" router :ellipsis="false" class="nav">
        <el-menu-item index="/">分析列表</el-menu-item>
        <template v-if="store.isAdmin">
          <el-menu-item index="/admin/logs">Agent 日志</el-menu-item>
          <el-menu-item index="/admin/prompts">Prompt 管理</el-menu-item>
          <el-menu-item index="/admin/llm">模型配置</el-menu-item>
        </template>
      </el-menu>
      <div class="user">
        <el-tag v-if="store.isAdmin" size="small" type="warning">管理员</el-tag>
        <span class="uname">{{ store.userInfo?.nickname || store.userInfo?.username }}</span>
        <el-button link type="primary" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useUserStore } from './store/user'
import { useRouter } from 'vue-router'
const store = useUserStore()
const router = useRouter()
function logout() { store.logout(); router.push('/login') }
</script>

<style>
body { margin: 0; background: #f5f7fa; }
.header { display: flex; align-items: center; gap: 20px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.logo { font-weight: 700; font-size: 16px; cursor: pointer; white-space: nowrap; color: #2f6bff; }
.nav { flex: 1; border-bottom: none; }
.user { display: flex; align-items: center; gap: 10px; }
.uname { font-size: 14px; color: #606266; }
.main { padding: 20px; }
</style>
