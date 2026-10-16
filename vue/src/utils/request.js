import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import router from '../router'

function buildRequest(getToken) {
  const req = axios.create({ baseURL: '', timeout: 180000 })

  req.interceptors.request.use((config) => {
    config.headers['X-Client-Type'] = 'web'
    const t = getToken()
    if (t) config.headers['token'] = t
    return config
  })

  req.interceptors.response.use(
    (res) => {
      const ct = (res.headers['content-type'] || '').toLowerCase()
      if (res.config.responseType === 'blob' || ct.includes('pdf') || ct.includes('markdown')) {
        return res
      }
      const data = res.data
      if (data && (data.code === 200 || data.code === 0)) return data
      if (data && data.code === 401) {
        const store = useUserStore()
        store.logout()
        ElMessage.error(data.msg || '登录已过期')
        router.push('/login')
        return Promise.reject(new Error(data.msg || '登录已过期'))
      }
      ElMessage.error(data?.msg || data?.message || '请求失败')
      return Promise.reject(new Error(data?.msg || '请求失败'))
    },
    (err) => {
      const status = err.response?.status
      if (status === 401) {
        const store = useUserStore()
        store.logout()
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      } else {
        ElMessage.error(err.response?.data?.detail || '网络异常，请稍后重试')
      }
      return Promise.reject(err)
    },
  )
  return req
}

// 用户请求（带用户 token）
export const request = buildRequest(() => useUserStore().token)
// 管理员请求（带管理员 token）
export const adminRequest = buildRequest(() => useUserStore().adminToken)
export default request
