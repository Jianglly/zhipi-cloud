<template>
  <div class="app-layout" :class="{ 'sidebar-open': sidebarOpen }">
    <!-- 移动端遮罩层 -->
    <transition name="overlay">
      <div v-if="sidebarOpen" class="sidebar-overlay" @click="closeSidebar" />
    </transition>

    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <span class="logo-icon">📚</span>
        <div>
          <div class="logo-title">智批云</div>
          <div class="logo-sub">{{ roleLabel }}</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          @click="closeSidebar"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-avatar">{{ firstChar }}</div>
          <div class="user-detail">
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ userClass }} · {{ roleLabel }}</div>
          </div>
        </div>
        <button class="logout-btn" @click="handleLogout" title="退出登录">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16,17 21,12 16,7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-area">
      <!-- 顶部导航条（移动端可见） -->
      <header class="top-bar">
        <button class="hamburger" @click="toggleSidebar" aria-label="切换菜单">
          <span /><span /><span />
        </button>
        <h1 class="top-bar-title">{{ pageTitle }}</h1>
        <div class="top-bar-actions">
          <slot name="header-actions" />
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  /** 导航项列表 [{ to, icon, label }] */
  navItems: { type: Array, required: true },
  /** 角色标签，如"教师端"、"学生端" */
  roleLabel: { type: String, default: '' },
})

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const sidebarOpen = ref(false)

// ── 用户信息 ──
const userName = computed(() => userStore.user?.name || '用户')
const userClass = computed(() => userStore.user?.class_id || '')
const firstChar = computed(() => userName.value.charAt(0))

// ── 当前页面标题 ──
const pageTitle = computed(() => {
  const match = props.navItems.find(n => route.path.startsWith(n.to))
  return match?.label || '智批云'
})

// ── 侧边栏开关 ──
const toggleSidebar = () => { sidebarOpen.value = !sidebarOpen.value }
const closeSidebar  = () => { sidebarOpen.value = false }

// ── 登出 ──
const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

// ── 路由切换自动关闭侧栏 ──
watch(() => route.path, closeSidebar)
</script>

<style scoped>
/* ==================== 布局容器 ==================== */
.app-layout {
  display: flex;
  min-height: 100vh;
  position: relative;
}

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: 240px;
  background: #1e293b;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 30;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo-icon { font-size: 28px; line-height: 1; }
.logo-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  line-height: 1.3;
}
.logo-sub {
  font-size: 12px;
  color: #94a3b8;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
}
.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.nav-item.router-link-active {
  background: var(--nav-active-bg, #4f46e5);
  color: #fff;
}
.nav-icon { font-size: 16px; line-height: 1; }

/* 底部用户区 */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
  background: var(--nav-active-bg, #4f46e5);
}
.user-detail {
  min-width: 0;
}
.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role {
  font-size: 12px;
  color: #64748b;
}
.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  border-radius: 8px;
  transition: all 0.15s;
  flex-shrink: 0;
}
.logout-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #f87171;
}

/* ==================== 主内容区 ==================== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg);
}

/* 顶部导航条（移动端） */
.top-bar {
  display: none;
  align-items: center;
  gap: 12px;
  height: 52px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 20;
  flex-shrink: 0;
}
.top-bar-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 汉堡按钮 */
.hamburger {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 44px;
  height: 44px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background 0.15s;
}
.hamburger:hover { background: var(--bg); }
.hamburger span {
  display: block;
  width: 22px;
  height: 2px;
  background: var(--text);
  border-radius: 2px;
  transition: all 0.2s;
  transform-origin: center;
}
/* 菜单打开时汉堡变叉号 */
.sidebar-open .hamburger span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}
.sidebar-open .hamburger span:nth-child(2) {
  opacity: 0;
}
.sidebar-open .hamburger span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* 内容区 */
.content {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 24px;
}

/* ==================== 遮罩层 ==================== */
.sidebar-overlay {
  display: none;
}

/* ==================== 响应式：平板及以下 ==================== */
@media (max-width: 768px) {
  .top-bar { display: flex; }

  .content {
    padding: 16px;
  }

  /* 侧边栏变身抽屉 */
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    height: 100dvh;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: none;
  }
  .sidebar.open {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.25);
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 29;
    backdrop-filter: blur(2px);
  }

  /* 遮罩过渡 */
  .overlay-enter-active,
  .overlay-leave-active {
    transition: opacity 0.3s ease;
  }
  .overlay-enter-from,
  .overlay-leave-to {
    opacity: 0;
  }
}
</style>
