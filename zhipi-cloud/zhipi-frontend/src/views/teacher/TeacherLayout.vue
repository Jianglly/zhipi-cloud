<template>
  <AppLayout :nav-items="navItems" role-label="教师端" style="--nav-active-bg: #4f46e5">
    <template #header-actions>
      <!-- 教师端顶部扩展按钮位 -->
    </template>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/components/AppLayout.vue'

const navItems = [
  { to: '/teacher/dashboard', icon: '📊', label: '工作台' },
  { to: '/teacher/papers',    icon: '📝', label: '试卷管理' },
  { to: '/teacher/marking',   icon: '✏️', label: '批阅管理' },
  { to: '/teacher/analysis',  icon: '📈', label: '学情分析' },
]
</script>
