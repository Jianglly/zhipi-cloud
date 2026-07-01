<template>
  <div class="student-dashboard">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的主页</h1>
        <p class="page-subtitle">欢迎回来，{{ userName }} 同学 👋</p>
      </div>
      <div class="header-meta">{{ today }}</div>
    </div>

    <!-- 个人统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background:#dbeafe;color:#1e40af">📋</div>
        <div>
          <div class="stat-value">{{ myScores.length }}</div>
          <div class="stat-label">已出成绩考试</div>
        </div>
      </div>
      <div class="stat-card" v-if="latestScore">
        <div class="stat-icon" style="background:#d1fae5;color:#065f46">🎯</div>
        <div>
          <div class="stat-value">{{ latestScore.score }}</div>
          <div class="stat-label">最近考试成绩</div>
        </div>
      </div>
      <div class="stat-card" v-if="avgScore !== null">
        <div class="stat-icon" style="background:#fef3c7;color:#92400e">📊</div>
        <div>
          <div class="stat-value">{{ avgScore }}</div>
          <div class="stat-label">平均分</div>
        </div>
      </div>
      <div class="stat-card" v-if="bestRank !== null">
        <div class="stat-icon" style="background:#ede9fe;color:#7c3aed">🏆</div>
        <div>
          <div class="stat-value">第 {{ bestRank }} 名</div>
          <div class="stat-label">最好班级排名</div>
        </div>
      </div>
    </div>

    <!-- 最新成绩 + 快捷入口 -->
    <div class="content-grid">
      <div class="card">
        <h3 class="card-title">最近考试成绩</h3>
        <div v-if="loadingScores" class="loading">加载中...</div>
        <div v-else-if="myScores.length === 0" class="empty-state">
          <div class="icon">📝</div>
          <p>暂无成绩数据</p>
        </div>
        <table v-else class="table">
          <thead>
            <tr>
              <th>考试</th>
              <th>科目</th>
              <th>成绩</th>
              <th>班级排名</th>
              <th>日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in myScores.slice(0, 5)" :key="s.score_id">
              <td style="font-size:13px;max-width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {{ s.paper_title }}
              </td>
              <td><span class="badge badge-info">{{ s.subject }}</span></td>
              <td>
                <span :class="['font-bold', getScoreColor(s.score, s.total_score)]">
                  {{ s.score }} / {{ s.total_score }}
                </span>
              </td>
              <td>
                <span v-if="s.rank_in_class" class="rank-text">第 {{ s.rank_in_class }} 名</span>
                <span v-else class="text-secondary">—</span>
              </td>
              <td>{{ s.exam_date }}</td>
            </tr>
          </tbody>
        </table>
        <router-link to="/student/score" class="view-all-link">查看全部成绩 →</router-link>
      </div>

      <div class="card">
        <h3 class="card-title">快捷入口</h3>
        <div class="quick-links">
          <router-link to="/student/score" class="ql-item">
            <div class="ql-icon" style="background:#dbeafe">📋</div>
            <div>
              <div class="ql-title">成绩查询</div>
              <div class="ql-desc">查看各科目考试成绩</div>
            </div>
          </router-link>
          <router-link to="/student/trend" class="ql-item">
            <div class="ql-icon" style="background:#d1fae5">📈</div>
            <div>
              <div class="ql-title">成绩趋势</div>
              <div class="ql-desc">查看历次考试趋势图</div>
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

const user = JSON.parse(localStorage.getItem('user') || '{}')
const userName = computed(() => user.name || '同学')
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const myScores = ref([])
const loadingScores = ref(false)

const latestScore = computed(() => myScores.value[0] || null)
const avgScore = computed(() => {
  if (!myScores.value.length) return null
  const avg = myScores.value.reduce((sum, s) => sum + parseFloat(s.score), 0) / myScores.value.length
  return avg.toFixed(1)
})
const bestRank = computed(() => {
  const ranks = myScores.value.map(s => s.rank_in_class).filter(r => r)
  return ranks.length ? Math.min(...ranks) : null
})

const loadScores = async () => {
  loadingScores.value = true
  try {
    myScores.value = await statsApi.getMyScores() || []
  } finally {
    loadingScores.value = false
  }
}

const getScoreColor = (score, total) => {
  const pct = (score / total) * 100
  if (pct >= 80) return 'text-success'
  if (pct >= 60) return 'text-warning'
  return 'text-danger'
}

onMounted(loadScores)
</script>

<style scoped>
.student-dashboard { padding: 28px; max-width: 1100px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.header-meta { font-size: 13px; color: var(--text-secondary); padding-top: 6px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.stat-card {
  background: white; border-radius: 12px; padding: 18px; display: flex; align-items: center;
  gap: 14px; border: 1px solid var(--border); box-shadow: var(--shadow); transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-icon {
  width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center;
  justify-content: center; font-size: 18px; flex-shrink: 0;
}
.stat-value { font-size: 24px; font-weight: 700; color: var(--text); line-height: 1; margin-bottom: 2px; }
.stat-label { font-size: 12px; color: var(--text-secondary); }
.content-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 18px; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 14px; }
.font-bold { font-weight: 600; }
.rank-text { color: var(--primary); font-weight: 500; }
.view-all-link {
  display: block; text-align: right; margin-top: 12px; font-size: 13px;
  color: var(--primary); text-decoration: none;
}
.view-all-link:hover { text-decoration: underline; }
.quick-links { display: flex; flex-direction: column; gap: 12px; }
.ql-item {
  display: flex; align-items: center; gap: 14px; padding: 14px; border-radius: 10px;
  border: 1px solid var(--border); text-decoration: none; color: inherit; transition: all 0.2s;
}
.ql-item:hover { border-color: #06b6d4; background: #f0fdfe; transform: translateX(4px); }
.ql-icon {
  width: 40px; height: 40px; border-radius: 10px; display: flex;
  align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;
}
.ql-title { font-weight: 600; font-size: 14px; }
.ql-desc { font-size: 12px; color: var(--text-secondary); }
@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .content-grid { grid-template-columns: 1fr; }
}
</style>
