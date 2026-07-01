<template>
  <div class="dashboard-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">工作台</h1>
        <p class="page-subtitle">欢迎回来，{{ userName }}老师 👋</p>
      </div>
      <div class="header-meta">{{ today }}</div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background:#ede9fe; color:#7c3aed">📝</div>
        <div class="stat-info">
          <div class="stat-value">{{ overview.total_papers }}</div>
          <div class="stat-label">总试卷数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#d1fae5; color:#065f46">✅</div>
        <div class="stat-info">
          <div class="stat-value">{{ overview.completed_scores }}</div>
          <div class="stat-label">已完成批阅</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#fef3c7; color:#92400e">⏳</div>
        <div class="stat-info">
          <div class="stat-value">{{ overview.pending_scores }}</div>
          <div class="stat-label">待批阅</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#dbeafe; color:#1e40af">👥</div>
        <div class="stat-info">
          <div class="stat-value">{{ overview.total_students }}</div>
          <div class="stat-label">班级学生数</div>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <!-- 班级成绩概览 -->
      <div class="card">
        <div class="card-header">
          <h3>班级考试概览</h3>
          <select v-model="selectedSubject" class="form-select mini-select" @change="loadOverview">
            <option value="">全部科目</option>
            <option v-for="s in allSubjects" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div v-if="loadingOverview" class="loading">加载中...</div>
        <div v-else-if="classOverview.length === 0" class="empty-state">
          <div class="icon">📊</div>
          <p>暂无考试数据</p>
        </div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>考试名称</th>
              <th>科目</th>
              <th>日期</th>
              <th>人数</th>
              <th>平均分</th>
              <th>最高分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in classOverview" :key="item.exam_date + item.subject">
              <td>{{ item.paper_title }}</td>
              <td><span class="badge badge-info">{{ item.subject }}</span></td>
              <td>{{ item.exam_date }}</td>
              <td>{{ item.student_count }}</td>
              <td>
                <span :class="['score-val', getScoreClass(item.avg_score, item.total_score)]">
                  {{ item.avg_score }}
                </span>
              </td>
              <td>{{ item.max_score }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 快捷操作 -->
      <div class="card">
        <div class="card-header"><h3>快捷操作</h3></div>
        <div class="quick-actions">
          <router-link to="/teacher/marking" class="quick-action-item">
            <div class="qa-icon" style="background:#ede9fe">✏️</div>
            <div class="qa-info">
              <div class="qa-title">去批阅</div>
              <div class="qa-desc">处理待批阅答卷</div>
            </div>
          </router-link>
          <router-link to="/teacher/analysis" class="quick-action-item">
            <div class="qa-icon" style="background:#d1fae5">📈</div>
            <div class="qa-info">
              <div class="qa-title">学情分析</div>
              <div class="qa-desc">查看成绩分布排名</div>
            </div>
          </router-link>
          <router-link to="/teacher/papers" class="quick-action-item">
            <div class="qa-icon" style="background:#dbeafe">📝</div>
            <div class="qa-info">
              <div class="qa-title">试卷管理</div>
              <div class="qa-desc">创建和管理试卷</div>
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { statsApi } from '@/api'
import { ALL_SUBJECTS } from '@/constants'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const userName = computed(() => user.name || '老师')
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const overview = ref({ total_papers: 0, completed_scores: 0, pending_scores: 0, total_students: 0 })
const classOverview = ref([])
const selectedSubject = ref('')
const allSubjects = ALL_SUBJECTS
const loadingOverview = ref(false)

const loadOverview = async () => {
  loadingOverview.value = true
  try {
    const data = await statsApi.getClassOverview(null, selectedSubject.value || null)
    classOverview.value = data || []
    // 简单统计
    overview.value.total_papers = data?.length || 0
    const studentsData = await statsApi.getStudents()
    overview.value.total_students = studentsData?.length || 0
  } catch (e) {
    classOverview.value = []
  } finally {
    loadingOverview.value = false
  }
}

const getScoreClass = (score, total) => {
  const pct = (score / total) * 100
  if (pct >= 80) return 'text-success'
  if (pct >= 60) return 'text-warning'
  return 'text-danger'
}

onMounted(loadOverview)
</script>

<style scoped>
.dashboard-page {
  padding: 28px;
  max-width: 1200px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
}
.header-meta {
  font-size: 14px;
  color: var(--text-secondary);
  padding-top: 6px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: white;
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
  margin-bottom: 4px;
}
.stat-label { font-size: 13px; color: var(--text-secondary); }
.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.card-header h3 {
  font-size: 16px;
  font-weight: 600;
}
.mini-select {
  width: 140px;
  padding: 6px 10px;
  font-size: 13px;
}
.score-val { font-weight: 600; }
.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.quick-action-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}
.quick-action-item:hover {
  border-color: var(--primary);
  background: #f5f3ff;
  transform: translateX(4px);
}
.qa-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.qa-title { font-weight: 600; font-size: 14px; }
.qa-desc { font-size: 12px; color: var(--text-secondary); }

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
}
</style>
