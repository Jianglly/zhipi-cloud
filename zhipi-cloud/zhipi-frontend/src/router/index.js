import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/login/RegisterView.vue'),
    meta: { requiresGuest: true }
  },
    {
    path: '/teacher',
    component: () => import('@/views/teacher/TeacherLayout.vue'),
    meta: { requiresAuth: true, role: 'teacher' },
    children: [
      { path: '', redirect: '/teacher/dashboard' },
      { path: 'dashboard', name: 'TeacherDashboard', component: () => import('@/views/teacher/DashboardView.vue') },
      { path: 'marking',   name: 'TeacherMarking',   component: () => import('@/views/teacher/MarkingView.vue') },
      { path: 'marking/:paperId/:studentId',   name: 'TeacherMarkingDetail',   component: () => import('@/views/teacher/MarkingDetailView.vue'), props: true },
      { path: 'analysis',  name: 'TeacherAnalysis',  component: () => import('@/views/teacher/AnalysisView.vue') },
      { path: 'papers',    name: 'TeacherPapers',    component: () => import('@/views/teacher/PapersView.vue') },
    ]
  },
  {
    path: '/student',
    component: () => import('@/views/student/StudentLayout.vue'),
    meta: { requiresAuth: true, role: 'student' },
    children: [
      { path: '', redirect: '/student/dashboard' },
      { path: 'dashboard', name: 'StudentDashboard', component: () => import('@/views/student/DashboardView.vue') },
      { path: 'score',     name: 'StudentScore',     component: () => import('@/views/student/ScoreView.vue') },
      { path: 'trend',     name: 'StudentTrend',     component: () => import('@/views/student/TrendView.vue') },
    ]
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'AdminDashboard', component: () => import('@/views/admin/DashboardView.vue') },
      { path: 'users',     name: 'AdminUsers',     component: () => import('@/views/admin/UsersView.vue') },
      { path: 'classes',   name: 'AdminClasses',   component: () => import('@/views/admin/ClassesView.vue') },
      { path: 'papers',    name: 'AdminPapers',    component: () => import('@/views/admin/PapersView.vue') },
      { path: 'logs',      name: 'AdminLogs',      component: () => import('@/views/admin/LogsView.vue') },
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  // Hash 模式：WebView 不支持 HTML5 History API，必须用 hash 路由
  history: createWebHashHistory(),
  routes
})

// ===================== 路由守卫 =====================
function getHomeByRole(role) {
  if (role === 'admin') return '/admin'
  if (role === 'teacher') return '/teacher'
  return '/student'
}

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.token) {
    return next('/login')
  }
  if (to.meta.requiresGuest && userStore.token && userStore.user) {
    return next(getHomeByRole(userStore.user.role))
  }
  if (to.meta.role && userStore.user && userStore.user.role !== to.meta.role) {
    return next(getHomeByRole(userStore.user.role))
  }
  next()
})

export default router
