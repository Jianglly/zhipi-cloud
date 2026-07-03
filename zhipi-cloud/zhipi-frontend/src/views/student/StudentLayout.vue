<template>
  <AppLayout :nav-items="navItems" role-label="学生端" style="--nav-active-bg: #06b6d4">
    <template #header-actions>
      <!-- 学生端顶部扩展按钮位 -->
    </template>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/components/AppLayout.vue'

const navItems = [
  { to: '/student/dashboard', icon: '🏠', label: '我的主页' },
  { to: '/student/score',     icon: '📋', label: '成绩查询' },
  { to: '/student/trend',     icon: '📈', label: '成绩趋势' },
]
</script>
