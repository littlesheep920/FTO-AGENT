import { defineStore } from 'pinia'
import request from '../utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.userInfo?.role === 9,
  },
  actions: {
    setToken(t) { this.token = t; localStorage.setItem('token', t) },
    setUserInfo(u) { this.userInfo = u; localStorage.setItem('userInfo', JSON.stringify(u)) },
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
    async fetchUserInfo() {
      const res = await request.get('/api/user/info')
      this.setUserInfo(res.data)
    },
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },
  },
})
