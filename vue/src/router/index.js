import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { title: '登录' } },
  { path: '/', name: 'Home', component: () => import('../views/front/Home.vue'), meta: { title: '分析列表', requireAuth: true } },
  { path: '/analysis/:id', name: 'AnalysisDetail', component: () => import('../views/front/AnalysisDetail.vue'), meta: { title: '分析详情', requireAuth: true } },
  { path: '/admin/logs', name: 'Logs', component: () => import('../views/manager/Logs.vue'), meta: { title: 'Agent 日志', requireAdmin: true } },
  { path: '/admin/prompts', name: 'Prompts', component: () => import('../views/manager/Prompts.vue'), meta: { title: 'Prompt 管理', requireAdmin: true } },
  { path: '/admin/llm', name: 'LlmConfig', component: () => import('../views/manager/LlmConfig.vue'), meta: { title: '模型配置', requireAdmin: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const store = useUserStore()
  document.title = to.meta.title ? `${to.meta.title} - FTO Agent` : 'FTO Agent'
  // 用户页面：需要用户 token（管理员 token 不算）
  if (to.meta.requireAuth && !store.token) return { path: '/login', query: { redirect: to.fullPath } }
  // 管理页面：需要管理员 token
  if (to.meta.requireAdmin && !store.adminToken) return { path: '/login' }
  return true
})

export default router
