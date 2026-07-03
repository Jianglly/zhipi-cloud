<template>
  <div class="login-page">
    <div class="bg-decor"></div>

    <div class="login-box register-box">
      <div class="login-header">
        <div class="logo">📚</div>
        <h1>注册账号</h1>
        <p>智批云 AI 智能批阅系统</p>
      </div>

      <!-- 角色切换 -->
      <div class="role-tabs">
        <button
          :class="['role-tab', form.role === 'teacher' ? 'active' : '']"
          @click="switchRole('teacher')"
        >
          👨‍🏫 教师注册
        </button>
        <button
          :class="['role-tab', form.role === 'student' ? 'active' : '']"
          @click="switchRole('student')"
        >
          👨‍🎓 学生注册
        </button>
      </div>

      <!-- 注册表单 -->
      <form @submit.prevent="handleRegister" class="login-form">
        <div class="form-group">
          <label class="form-label">
            {{ form.role === 'teacher' ? '教师编号' : '学号' }}
          </label>
          <input
            v-model.trim="form.user_id"
            class="form-input"
            :placeholder="form.role === 'teacher' ? '请输入教师编号（如 T008）' : '请输入学号（如 2414100311）'"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">姓名</label>
          <input
            v-model.trim="form.name"
            class="form-input"
            placeholder="请输入真实姓名"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">所在班级</label>
          <select
            v-model="form.class_id"
            class="form-input"
            required
          >
            <option value="" disabled>请选择班级</option>
            <option v-for="c in classList" :key="c.class_id" :value="c.class_id">
              {{ c.class_name }}（{{ c.class_id }}）
            </option>
          </select>
        </div>

        <!-- 教师注册需要填写任教科目 -->
        <div v-if="form.role === 'teacher'" class="form-group">
          <label class="form-label">任教科目</label>
          <input
            v-model.trim="form.subject"
            class="form-input"
            placeholder="请输入任教科目（如 数据库系统）"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            v-model="form.password"
            class="form-input"
            type="password"
            placeholder="至少 6 位密码"
            required
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input
            v-model="form.confirm_password"
            class="form-input"
            type="password"
            placeholder="请再次输入密码"
            required
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <label class="form-label">联系电话（选填）</label>
          <input
            v-model.trim="form.phone"
            class="form-input"
            placeholder="请输入手机号（可选）"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-msg">{{ successMsg }}</div>

        <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
      </form>

      <!-- 返回登录 -->
      <div class="demo-hint" style="text-align: center;">
        <p>已有账号？<router-link to="/login" style="color: #4f46e5; font-weight: 600;">返回登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'

const router = useRouter()
const userStore = useUserStore()

const classList = ref([])
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const form = reactive({
  role: 'student',
  user_id: '',
  name: '',
  class_id: '',
  subject: '',
  password: '',
  confirm_password: '',
  phone: '',
})

// 加载班级列表
onMounted(async () => {
  try {
    const res = await authApi.getClasses()
    classList.value = res
  } catch (err) {
    console.error('获取班级列表失败', err)
  }
})

function switchRole(r) {
  form.role = r
  // 切换角色时清空科目字段
  form.subject = ''
  errorMsg.value = ''
  successMsg.value = ''
}

function validate() {
  if (!form.user_id) return `${form.role === 'teacher' ? '教师编号' : '学号'}不能为空`
  if (!form.name) return '姓名不能为空'
  if (!form.class_id) return '请选择所在班级'
  if (form.role === 'teacher' && !form.subject) return '教师请填写任教科目'
  if (form.password.length < 6) return '密码至少 6 位'
  if (form.password !== form.confirm_password) return '两次输入的密码不一致'
  return null
}

async function handleRegister() {
  errorMsg.value = ''
  successMsg.value = ''

  const err = validate()
  if (err) {
    errorMsg.value = err
    return
  }

  loading.value = true
  try {
    const res = await userStore.register({
      role: form.role,
      user_id: form.user_id,
      name: form.name,
      class_id: form.class_id,
      subject: form.role === 'teacher' ? form.subject : null,
      password: form.password,
      confirm_password: form.confirm_password,
      phone: form.phone || null,
    })

    successMsg.value = res.message || '注册成功！正在跳转登录页...'

    // 延迟跳转到登录页
    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } catch (err) {
    errorMsg.value = err.message || '注册失败，请稍后重试'
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
.register-box {
  max-width: 460px;
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
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
  margin-bottom: 20px;
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
.login-form .form-group {
  margin-bottom: 14px;
}
.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
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
.error-msg {
  color: #ef4444;
  font-size: 13px;
  margin: 8px 0;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 6px;
}
.success-msg {
  color: #16a34a;
  font-size: 13px;
  margin: 8px 0;
  padding: 8px 12px;
  background: #f0fdf4;
  border-radius: 6px;
}
.demo-hint {
  margin-top: 16px;
  padding: 10px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 14px;
  color: #64748b;
}
</style>
