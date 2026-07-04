/**
 * 用户状态管理 (Pinia)
 * 集中管理用户信息、token、登录/登出逻辑
 * 消除组件中散落的 localStorage 读取
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useUserStore = defineStore('user', () => {
  // ——— 状态 ———
  const user = ref(null)       // { user_id, name, role, class_id, subject }
  const token = ref(null)

  // ——— 计算属性 ———
  const isLoggedIn = computed(() => !!token.value)
  const isTeacher   = computed(() => user.value?.role === 'teacher')
  const isStudent   = computed(() => user.value?.role === 'student')
  const isAdmin     = computed(() => user.value?.role === 'admin')

  // ——— 初始化：从 localStorage 恢复 ———
  function restore() {
    const savedToken = localStorage.getItem('token')
    const savedUser  = localStorage.getItem('user')
    if (savedToken) token.value = savedToken
    if (savedUser) {
      try { user.value = JSON.parse(savedUser) }
      catch { user.value = null }
    }
  }

  // ——— 登录 ———
  async function login(userId, password, role) {
    const res = await authApi.login(userId, password, role)
    const userData = {
      user_id: res.user_id,
      name: res.name,
      role: res.role,
      class_id: res.class_id,
      subject: res.subject || null,
    }
    token.value = res.access_token
    user.value = userData
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(userData))
    return res
  }

  // ——— 注册 ———
  async function register(payload) {
    const res = await authApi.register(payload)
    return res  // { message, user_id, name, role, class_id }
  }

  // ——— 登出 ———
  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // ——— 更新用户信息 ———
  function setUser(userData) {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  // 自动恢复
  restore()

  return { user, token, isLoggedIn, isTeacher, isStudent, isAdmin, login, register, logout, setUser, restore }
})
