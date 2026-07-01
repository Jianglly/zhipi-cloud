<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="logo-icon">📚</span>
        <div>
          <div class="logo-title">智批云</div>
          <div class="logo-sub">学生端</div>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/student/dashboard" class="nav-item">
          <span class="nav-icon">🏠</span>
          <span>我的主页</span>
        </router-link>
        <router-link to="/student/score" class="nav-item">
          <span class="nav-icon">📋</span>
          <span>成绩查询</span>
        </router-link>
        <router-link to="/student/trend" class="nav-item">
          <span class="nav-icon">📈</span>
          <span>成绩趋势</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-avatar" style="background:#06b6d4">{{ userName.charAt(0) }}</div>
          <div>
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ userClass }} · 学生</div>
          </div>
        </div>
        <button @click="logout" class="logout-btn" title="退出登录">⬅️</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const user = JSON.parse(localStorage.getItem('user') || '{}')
const userName = computed(() => user.name || '同学')
const userClass = computed(() => user.class_id || '')
const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 220px; background: #0f172a; display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-header {
  display: flex; align-items: center; gap: 10px; padding: 22px 18px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-icon { font-size: 26px; }
.logo-title { font-size: 17px; font-weight: 700; color: white; }
.logo-sub { font-size: 12px; color: #94a3b8; }
.sidebar-nav { flex: 1; padding: 14px 10px; display: flex; flex-direction: column; gap: 3px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
  color: #94a3b8; text-decoration: none; font-size: 14px; font-weight: 500; transition: all 0.15s;
}
.nav-item:hover { background: rgba(255,255,255,0.08); color: white; }
.nav-item.router-link-active { background: #06b6d4; color: white; }
.nav-icon { font-size: 15px; }
.sidebar-footer {
  padding: 14px; border-top: 1px solid rgba(255,255,255,0.1);
  display: flex; align-items: center; gap: 8px;
}
.user-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.user-avatar {
  width: 34px; height: 34px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 13px; flex-shrink: 0;
}
.user-name { font-size: 13px; font-weight: 500; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: 11px; color: #64748b; }
.logout-btn { background: none; border: none; cursor: pointer; font-size: 17px; padding: 4px; border-radius: 4px; }
.logout-btn:hover { background: rgba(255,255,255,0.1); }
.main-content { flex: 1; overflow: auto; background: #f8fafc; }
</style>
