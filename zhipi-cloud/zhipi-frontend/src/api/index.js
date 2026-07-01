/**
 * API 接口服务层
 * 封装所有后端请求，统一管理 token 和错误处理
 */
import axios from 'axios'
import router from '@/router'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

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
    return config
  },
  (error) => Promise.reject(error)
)

// ===================== 响应拦截器：统一错误处理 =====================
http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
    }
    const message = error.response?.data?.detail || '网络请求失败，请稍后重试'
    return Promise.reject(new Error(message))
  }
)

// ===================== 认证 API =====================
export const authApi = {
  login: (user_id, password, role) =>
    http.post('/auth/login', { user_id, password, role }),

  getMe: () => http.get('/auth/me'),
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

  getPending: (class_id) =>
    http.get('/papers/pending', { params: { class_id } }),

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
}

export default http
