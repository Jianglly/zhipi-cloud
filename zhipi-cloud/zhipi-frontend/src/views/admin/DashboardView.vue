<template>
  <div class="admin-dashboard">
    <div class="page-header">
      <div>
        <h1 class="page-title">系统总览</h1>
        <p class="page-subtitle">智批云全局运行数据</p>
      </div>
      <div class="header-meta">{{ today }}</div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid" v-if="!loading">
      <div class="stat-card" v-for="card in statCards" :key="card.label">
        <div class="stat-icon" :style="{ background: card.bg, color: card.color }">{{ card.icon }}</div>
        <div class="stat-info">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>
    <div class="stats-grid" v-else>
      <div class="stat-card skeleton" v-for="i in 7" :key="i">
        <div class="stat-icon" style="background:#f1f5f9">···</div>
        <div class="stat-info">
          <div class="stat-value">--</div>
          <div class="stat-label">加载中</div>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <!-- 试卷状态分布 -->
      <div class="card">
        <div class="card-header"><h3>试卷状态分布</h3></div>
        <div v-if="overview.paper_status_dist?.length" class="dist-list">
          <div class="dist-item" v-for="item in overview.paper_status_dist" :key="item.status">
            <span class="dist-label">{{ item.status }}</span>
            <div class="dist-bar-wrap">
              <div class="dist-bar" :style="{ width: getBarWidth(item.count) }">{{ item.count }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state"><div class="icon">📊</div><p>暂无数据</p></div>
      </div>

      <!-- 科目分布 -->
      <div class="card">
        <div class="card-header"><h3>科目分布</h3></div>
        <div v-if="overview.paper_subject_dist?.length" class="dist-list">
          <div class="dist-item" v-for="item in overview.paper_subject_dist" :key="item.subject">
            <span class="dist-label">{{ item.subject }}</span>
            <div class="dist-bar-wrap">
              <div class="dist-bar" :style="{ width: getBarWidth(item.count) }">{{ item.count }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state"><div class="icon">📚</div><p>暂无数据</p></div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="card" style="margin-top: 20px">
      <div class="card-header"><h3>快捷操作</h3></div>
      <div class="quick-actions">
        <router-link to="/admin/users" class="quick-action-item">
          <div class="qa-icon" style="background:#dbeafe">👥</div>
          <div class="qa-info"><div class="qa-title">用户管理</div><div class="qa-desc">管理教师和学生账号</div></div>
        </router-link>
        <router-link to="/admin/classes" class="quick-action-item">
          <div class="qa-icon" style="background:#d1fae5">🏫</div>
          <div class="qa-info"><div class="qa-title">班级管理</div><div class="qa-desc">创建和管理班级</div></div>
        </router-link>
        <router-link to="/admin/logs" class="quick-action-item">
          <div class="qa-icon" style="background:#fef3c7">📋</div>
          <div class="qa-info"><div class="qa-title">操作日志</div><div class="qa-desc">查看系统审计记录</div></div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { adminApi } from '@/api'

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
const overview = ref({})
const loading = ref(true)

const statCards = computed(() => [
  { label: '学生总数', value: overview.value.total_students || 0, icon: '👨‍🎓', bg: '#dbeafe', color: '#1e40af' },
  { label: '教师总数', value: overview.value.total_teachers || 0, icon: '👨‍🏫', bg: '#ede9fe', color: '#7c3aed' },
  { label: '班级总数', value: overview.value.total_classes || 0, icon: '🏫', bg: '#d1fae5', color: '#065f46' },
  { label: '试卷总数', value: overview.value.total_papers || 0, icon: '📝', bg: '#fef3c7', color: '#92400e' },
  { label: '成绩总数', value: overview.value.total_scores || 0, icon: '📄', bg: '#fce7f3', color: '#be185d' },
  { label: '已完成批阅', value: overview.value.completed_scores || 0, icon: '✅', bg: '#d1fae5', color: '#065f46' },
  { label: '待批阅', value: overview.value.pending_scores || 0, icon: '⏳', bg: '#fef3c7', color: '#92400e' },
])

const maxPaperCount = computed(() => {
  const all = [...(overview.value.paper_status_dist || []), ...(overview.value.paper_subject_dist || [])]
  return Math.max(...all.map(i => i.count), 1)
})

const getBarWidth = (count) => {
  return `${Math.max((count / maxPaperCount.value) * 100, 15)}%`
}

onMounted(async () => {
  try {
    overview.value = await adminApi.getOverview()
  } catch (e) {
    console.error('加载失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.admin-dashboard { padding: 28px; max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }
.header-meta { font-size: 14px; color: var(--text-secondary); padding-top: 6px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: white; border-radius: var(--radius); padding: 20px;
  display: flex; align-items: center; gap: 16px;
  border: 1px solid var(--border); box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-card.skeleton { opacity: 0.6; }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.stat-value { font-size: 28px; font-weight: 700; color: var(--text); line-height: 1; margin-bottom: 4px; }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-header h3 { font-size: 16px; font-weight: 600; }
.dist-list { display: flex; flex-direction: column; gap: 12px; }
.dist-item { display: flex; align-items: center; gap: 12px; }
.dist-label { width: 80px; font-size: 14px; font-weight: 500; flex-shrink: 0; }
.dist-bar-wrap { flex: 1; }
.dist-bar {
  background: #0F6E56; color: white; padding: 6px 12px; border-radius: 6px;
  font-size: 13px; font-weight: 600; min-width: 30px; text-align: center;
  transition: width 0.3s ease;
}
.quick-actions { display: flex; flex-direction: column; gap: 12px; }
.quick-action-item {
  display: flex; align-items: center; gap: 14px; padding: 14px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  text-decoration: none; color: inherit; transition: all 0.2s;
}
.quick-action-item:hover { border-color: #0F6E56; background: #f0fdf9; transform: translateX(4px); }
.qa-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.qa-title { font-weight: 600; font-size: 14px; }
.qa-desc { font-size: 12px; color: var(--text-secondary); }
.empty-state { text-align: center; padding: 32px; color: var(--text-secondary); }
.empty-state .icon { font-size: 32px; margin-bottom: 8px; }
@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
}
</style>
