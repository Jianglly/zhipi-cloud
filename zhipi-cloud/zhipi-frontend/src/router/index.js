import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 默认重定向到登录
  {
    path: '/',
    redirect: '/login'
  },
  // 登录页
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresGuest: true }
  },
  // 教师端
  {
    path: '/teacher',
    component: () => import('@/views/teacher/TeacherLayout.vue'),
    meta: { requiresAuth: true, role: 'teacher' },
    children: [
      {
        path: '',
        redirect: '/teacher/dashboard'
      },
      {
        path: 'dashboard',
        name: 'TeacherDashboard',
        component: () => import('@/views/teacher/DashboardView.vue'),
      },
      {
        path: 'marking',
        name: 'TeacherMarking',
        component: () => import('@/views/teacher/MarkingView.vue'),
      },
      {
        path: 'analysis',
        name: 'TeacherAnalysis',
        component: () => import('@/views/teacher/AnalysisView.vue'),
      },
      {
        path: 'papers',
        name: 'TeacherPapers',
        component: () => import('@/views/teacher/PapersView.vue'),
      }
    ]
  },
  // 学生端
  {
    path: '/student',
    component: () => import('@/views/student/StudentLayout.vue'),
    meta: { requiresAuth: true, role: 'student' },
    children: [
      {
        path: '',
        redirect: '/student/dashboard'
      },
      {
        path: 'dashboard',
        name: 'StudentDashboard',
        component: () => import('@/views/student/DashboardView.vue'),
      },
      {
        path: 'score',
        name: 'StudentScore',
        component: () => import('@/views/student/ScoreView.vue'),
      },
      {
        path: 'trend',
        name: 'StudentTrend',
        component: () => import('@/views/student/TrendView.vue'),
      }
    ]
  },
  // 404
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ===================== 路由守卫 =====================
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null

  // 需要登录但未登录
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }

  // 已登录访问登录页，重定向到对应首页
  if (to.meta.requiresGuest && token && user) {
    return next(user.role === 'teacher' ? '/teacher' : '/student')
  }

  // 角色权限检查
  if (to.meta.role && user && user.role !== to.meta.role) {
    return next(user.role === 'teacher' ? '/teacher' : '/student')
  }

  next()
})

export default router
