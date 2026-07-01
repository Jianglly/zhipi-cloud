<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decor"></div>

    <div class="login-box">
      <!-- Logo 区域 -->
      <div class="login-header">
        <div class="logo">📚</div>
        <h1>智批云</h1>
        <p>AI 智能批阅系统</p>
      </div>

      <!-- 角色切换 -->
      <div class="role-tabs">
        <button
          :class="['role-tab', role === 'teacher' ? 'active' : '']"
          @click="role = 'teacher'"
        >
          👨‍🏫 教师登录
        </button>
        <button
          :class="['role-tab', role === 'student' ? 'active' : '']"
          @click="role = 'student'"
        >
          👨‍🎓 学生登录
        </button>
      </div>

      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label class="form-label">
            {{ role === 'teacher' ? '教师编号' : '学号' }}
          </label>
          <input
            v-model="userId"
            class="form-input"
            :placeholder="role === 'teacher' ? '请输入教师编号（如 T001）' : '请输入学号（如 2414100311）'"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            v-model="password"
            class="form-input"
            type="password"
            placeholder="请输入密码"
            required
            autocomplete="current-password"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
      </form>

      <!-- 演示账号提示 -->
      <div class="demo-hint">
        <p>🔑 演示账号</p>
        <p>教师：T007 / 123456</p>
        <p>学生：S032 / 123456</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'

const router = useRouter()
const role = ref('teacher')
const userId = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

const handleLogin = async () => {
  if (!userId.value || !password.value) {
    errorMsg.value = '请填写完整的登录信息'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await authApi.login(userId.value, password.value, role.value)
    // 存储 token 和用户信息
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify({
      user_id: res.user_id,
      name: res.name,
      role: res.role,
      class_id: res.class_id,
    }))
    // 跳转到对应首页
    router.push(res.role === 'teacher' ? '/teacher/dashboard' : '/student/dashboard')
  } catch (err) {
    errorMsg.value = err.message || '登录失败，请检查账号密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}
.bg-decor {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
}
.login-box {
  background: white;
  border-radius: 20px;
  padding: 40px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  position: relative;
  z-index: 1;
}
.login-header {
  text-align: center;
  margin-bottom: 28px;
}
.logo {
  font-size: 48px;
  margin-bottom: 8px;
}
.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}
.login-header p {
  color: #64748b;
  font-size: 14px;
}
.role-tabs {
  display: flex;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}
.role-tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: #64748b;
}
.role-tab.active {
  background: white;
  color: #4f46e5;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.login-btn {
  width: 100%;
  justify-content: center;
  padding: 12px;
  font-size: 16px;
  margin-top: 8px;
}
.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none !important;
}
.demo-hint {
  margin-top: 20px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.8;
}
.demo-hint p:first-child {
  font-weight: 600;
  color: #4f46e5;
}
</style>
