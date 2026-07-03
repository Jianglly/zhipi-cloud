<template>
  <AppLayout :nav-items="navItems" role-label="管理员端" style="--nav-active-bg: #0F6E56">
    <template #header-actions>
    </template>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/components/AppLayout.vue'

const navItems = [
  { to: '/admin/dashboard', icon: '📊', label: '系统总览' },
  { to: '/admin/users',     icon: '👥', label: '用户管理' },
  { to: '/admin/classes',   icon: '🏫', label: '班级管理' },
  { to: '/admin/papers',    icon: '📝', label: '试卷总览' },
  { to: '/admin/logs',      icon: '📋', label: '操作日志' },
]
</script>
