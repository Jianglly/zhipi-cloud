<template>
  <div class="score-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">成绩查询</h1>
        <p class="page-subtitle">查看您的所有考试成绩与班级排名</p>
      </div>
    </div>

    <!-- 科目筛选 -->
    <div class="card filter-row">
      <label class="form-label" style="margin:0">科目筛选：</label>
      <select v-model="filterSubject" class="form-select" style="width:160px" @change="loadScores">
        <option value="">全部科目</option>
        <option v-for="s in allSubjects" :key="s" :value="s">{{ s }}</option>
      </select>
    </div>

    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="scores.length === 0" class="empty-state">
        <div class="icon">📋</div>
        <p>暂无成绩记录</p>
        <p style="font-size:13px;margin-top:8px">等待教师完成批阅后成绩将在此显示</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>考试名称</th>
            <th>科目</th>
            <th>成绩</th>
            <th>得分率</th>
            <th>班级排名</th>
            <th>考试日期</th>
            <th>等级</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in scores" :key="s.score_id">
            <td style="font-weight:500">{{ s.paper_title }}</td>
            <td><span class="badge badge-info">{{ s.subject }}</span></td>
            <td>
              <span :class="['score-display', getScoreColor(s.score, s.total_score)]">
                {{ s.score }}
              </span>
              <span class="total-score"> / {{ s.total_score }}</span>
            </td>
            <td>
              <div class="score-bar-wrap">
                <div class="score-bar">
                  <div
                    class="score-bar-fill"
                    :style="{ width: getPercent(s.score, s.total_score) + '%', background: getBarColor(s.score, s.total_score) }"
                  ></div>
                </div>
                <span class="percent-label">{{ getPercent(s.score, s.total_score) }}%</span>
              </div>
            </td>
            <td>
              <span v-if="s.rank_in_class" class="rank-display">🏆 第 {{ s.rank_in_class }} 名</span>
              <span v-else class="text-secondary">—</span>
            </td>
            <td>{{ s.exam_date }}</td>
            <td>
              <span :class="['badge', getLevelBadge(s.score, s.total_score)]">
                {{ getLevel(s.score, s.total_score) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '@/api'
import { ALL_SUBJECTS } from '@/constants'

const scores = ref([])
const loading = ref(false)
const filterSubject = ref('')
const allSubjects = ALL_SUBJECTS

const loadScores = async () => {
  loading.value = true
  try {
    scores.value = await statsApi.getMyScores(filterSubject.value || null) || []
  } finally {
    loading.value = false
  }
}

const getPercent = (score, total) => Math.round((score / total) * 100)
const getScoreColor = (score, total) => {
  const pct = (score / total) * 100
  return pct >= 80 ? 'text-success' : pct >= 60 ? 'text-warning' : 'text-danger'
}
const getBarColor = (score, total) => {
  const pct = (score / total) * 100
  return pct >= 80 ? '#10b981' : pct >= 60 ? '#f59e0b' : '#ef4444'
}
const getLevel = (score, total) => {
  const pct = (score / total) * 100
  if (pct >= 90) return '优秀'
  if (pct >= 75) return '良好'
  if (pct >= 60) return '及格'
  return '不及格'
}
const getLevelBadge = (score, total) => {
  const l = getLevel(score, total)
  return l === '优秀' ? 'badge-success' : l === '良好' ? 'badge-info' : l === '及格' ? 'badge-warning' : 'badge-danger'
}

onMounted(loadScores)
</script>

<style scoped>
.score-page { padding: 28px; max-width: 1100px; }
.page-header { margin-bottom: 20px; }
.filter-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 14px 20px;
}
.score-display { font-size: 18px; font-weight: 700; }
.total-score { font-size: 13px; color: var(--text-secondary); }
.score-bar-wrap { display: flex; align-items: center; gap: 8px; }
.score-bar {
  width: 80px; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;
}
.score-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.percent-label { font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.rank-display { color: var(--primary); font-weight: 500; font-size: 13px; }
</style>
