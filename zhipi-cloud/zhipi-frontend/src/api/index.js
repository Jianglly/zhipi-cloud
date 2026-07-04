/**
 * API 接口服务层
 * 封装所有后端请求，统一管理 token 和错误处理
 *
 * 地址优先级（Android 真机调试用）：
 *   1. localStorage 中手动设置的 apiServer（无需重新打包）
 *   2. VITE_API_BASE_URL 环境变量（打包时写入）
 *   3. 默认 '/api'（开发环境 Vite 代理 / 同机部署）
 */
import axios from 'axios'

function getBaseURL() {
  // 运行时覆盖：在浏览器控制台执行 localStorage.setItem('apiServer', 'http://192.168.x.x:8000/api')
  const runtimeServer = localStorage.getItem('apiServer')
  if (runtimeServer) return runtimeServer

  return import.meta.env.VITE_API_BASE_URL || '/api'
}

const BASE_URL = getBaseURL()

// 创建 axios 实例
const http = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
})

// ===================== 请求拦截器：自动附加 token =====================
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 开发模式：打印请求日志
    if (import.meta.env.DEV) {
      console.log(`[API] → ${config.method.toUpperCase()} ${config.baseURL}${config.url}`,
        config.params || config.data || '')
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ===================== 响应拦截器：统一错误处理 =====================
http.interceptors.response.use(
  (response) => {
    // 开发模式：打印响应日志
    if (import.meta.env.DEV) {
      console.log(`[API] ← ${response.status} ${response.config.url}`,
        typeof response.data === 'object' ? '(data)' : response.data?.substring?.(0, 50))
    }
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 避免循环依赖：不 import router，直接用 location
      if (window.location.hash) {
        window.location.hash = '#/login'
      } else {
        window.location.href = '/login'
      }
    }
    // 打印错误详情
    const errMsg = error.response?.data?.detail || error.message || '网络请求失败'
    console.error(`[API] ✗ ${error.config?.url || '?'} | ${error.response?.status || 'NET'} | ${errMsg}`)
    return Promise.reject(new Error(errMsg))
  }
)

// ===================== 认证 API =====================
export const authApi = {
  login: (user_id, password, role) =>
    http.post('/auth/login', { user_id, password, role }),

  register: (data) =>
    http.post('/auth/register', data),

  getClasses: () =>
    http.get('/auth/classes'),

  getMe: () => http.get('/auth/me'),

  getTeacherClasses: () => http.get('/auth/me/classes'),
}

// ===================== 统计 API =====================
export const statsApi = {
  // 学生接口
  getMyScores: (subject) =>
    http.get('/stats/student/scores', { params: { subject } }),

  getMyTrend: (subject) =>
    http.get('/stats/student/trend', { params: { subject } }),

  getMyRanking: (subject, exam_date) =>
    http.get('/stats/student/ranking', { params: { subject, exam_date } }),

  // 教师接口
  getClassOverview: (class_id, subject) =>
    http.get('/stats/teacher/class-overview', { params: { class_id, subject } }),

  getClassRanking: (subject, exam_date, class_id) =>
    http.get('/stats/teacher/class-ranking', { params: { subject, exam_date, class_id } }),

  getStudents: (class_id) =>
    http.get('/stats/teacher/students', { params: { class_id } }),

  getScoreDistribution: (subject, exam_date, class_id) =>
    http.get('/stats/teacher/score-distribution', { params: { subject, exam_date, class_id } }),
}

// ===================== 试卷 API =====================
export const paperApi = {
  getList: (class_id, subject) =>
    http.get('/papers', { params: { class_id, subject } }),

  create: (data) => http.post('/papers', data),

  getDetail: (paper_id) =>
    http.get(`/papers/${paper_id}`),

  update: (paper_id, data) =>
    http.put(`/papers/${paper_id}`, data),

  delete: (paper_id) =>
    http.delete(`/papers/${paper_id}`),

  getClasses: () =>
    http.get('/papers/classes'),

  getPending: (class_id) =>
    http.get('/papers/pending', { params: { class_id } }),

  getCompleted: (class_id) =>
    http.get('/papers/completed', { params: { class_id } }),

  submitScore: (paper_id, student_id, manual_score) =>
    http.post(`/papers/${paper_id}/submit-score`, null, {
      params: { student_id, manual_score }
    }),

  // 恢复意外提交的成绩到待审核状态
  recoverScore: (paper_id, student_id) =>
    http.post(`/papers/${paper_id}/recover-score`, null, {
      params: { student_id }
    }),
}

// ===================== OCR 批阅 API =====================
export const ocrApi = {
  // 上传答卷图片
  uploadImage: (paper_id, student_id, file) => {
    const formData = new FormData()
    formData.append('paper_id', paper_id)
    formData.append('student_id', student_id)
    formData.append('file', file)
    return http.post('/ocr/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // OCR 识别答案（参数用 query string）
  recognize: (paper_id, student_id) =>
    http.post('/ocr/recognize', null, { params: { paper_id, student_id } }),

  // 自动批改（参数用 query string）
  autoGrade: (paper_id, student_id) =>
    http.post('/ocr/auto-grade', null, { params: { paper_id, student_id } }),

  // 查看批改结果
  getGradeResults: (paper_id) =>
    http.get(`/ocr/grade-results/${paper_id}`),

  // AI批改大题（客观题正则 + 主观题LLM）
  llmGrade: (paper_id, student_id) =>
    http.post('/ocr/llm-grade', null, {
      params: { paper_id, student_id },
      timeout: 120000,  // LLM 调用较慢，2分钟超时
    }),
}

// ===================== 管理员 API =====================
export const adminApi = {
  // 系统总览
  getOverview: () => http.get('/admin/overview'),

  // 教师管理
  getTeachers: (keyword) =>
    http.get('/admin/teachers', { params: { keyword } }),
  createTeacher: (data) => http.post('/admin/teachers', data),
  updateTeacher: (teacher_id, data) =>
    http.put(`/admin/teachers/${teacher_id}`, data),
  deleteTeacher: (teacher_id) =>
    http.delete(`/admin/teachers/${teacher_id}`),
  resetTeacherPassword: (teacher_id, new_password) =>
    http.post(`/admin/teachers/${teacher_id}/reset-password`, { new_password }),

  // 学生管理
  getStudents: (class_id, keyword) =>
    http.get('/admin/students', { params: { class_id, keyword } }),
  createStudent: (data) => http.post('/admin/students', data),
  updateStudent: (student_id, data) =>
    http.put(`/admin/students/${student_id}`, data),
  deleteStudent: (student_id) =>
    http.delete(`/admin/students/${student_id}`),
  resetStudentPassword: (student_id, new_password) =>
    http.post(`/admin/students/${student_id}/reset-password`, { new_password }),

  // 班级管理
  getClasses: () => http.get('/admin/classes'),
  createClass: (data) => http.post('/admin/classes', data),
  updateClass: (class_id, data) =>
    http.put(`/admin/classes/${class_id}`, data),
  deleteClass: (class_id) =>
    http.delete(`/admin/classes/${class_id}`),

  // 试卷总览
  getPapers: (subject, status) =>
    http.get('/admin/papers', { params: { subject, status } }),

  // 成绩总览
  getScores: (class_id, subject, page, page_size) =>
    http.get('/admin/scores', { params: { class_id, subject, page, page_size } }),

  // 操作日志
  getLogs: (user_id, module, page, page_size) =>
    http.get('/admin/logs', { params: { user_id, module, page, page_size } }),
}

export default http
