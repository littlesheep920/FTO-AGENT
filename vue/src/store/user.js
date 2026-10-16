import { defineStore } from 'pinia'
import { request, adminRequest } from '../utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    // 普通用户
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
    // 管理员（独立）
    adminToken: localStorage.getItem('adminToken') || '',
    adminInfo: JSON.parse(localStorage.getItem('adminInfo') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token || !!s.adminToken,
    isAdmin: (s) => !!s.adminToken,
    displayName: (s) => (s.adminInfo?.nickname || s.adminInfo?.username || s.userInfo?.nickname || s.userInfo?.username || ''),
  },
  actions: {
    setToken(t) { this.token = t; localStorage.setItem('token', t) },
    setUserInfo(u) { this.userInfo = u; localStorage.setItem('userInfo', JSON.stringify(u)) },
    setAdminToken(t) { this.adminToken = t; localStorage.setItem('adminToken', t) },
    setAdminInfo(a) { this.adminInfo = a; localStorage.setItem('adminInfo', JSON.stringify(a)) },

    async login(username, password) {
      const res = await request.post('/api/auth/login', { username, password })
      this.setToken(res.data.token)
      this.setUserInfo(res.data.user)
      return res
    },
    async register(username, password, nickname) {
      const res = await request.post('/api/auth/register', { username, password, nickname })
      this.setToken(res.data.token)
      this.setUserInfo(res.data.user)
      return res
    },
    async adminLogin(username, password) {
      const res = await adminRequest.post('/api/auth/admin/login', { username, password })
      this.setAdminToken(res.data.token)
      this.setAdminInfo(res.data.admin)
      return res
    },
    logout() {
      this.token = ''
      this.userInfo = null
      this.adminToken = ''
      this.adminInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      localStorage.removeItem('adminToken')
      localStorage.removeItem('adminInfo')
    },
  },
})
