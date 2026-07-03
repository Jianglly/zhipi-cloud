<template>
  <div class="analysis-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">学情分析</h1>
        <p class="page-subtitle">查看班级成绩分布与学生排名</p>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="card filter-card">
      <div class="filter-row">
        <div class="form-group" style="flex:1">
          <label class="form-label">科目</label>
          <select v-model="filter.subject" class="form-select">
            <option v-for="s in allSubjects" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="form-group" style="flex:1">
          <label class="form-label">考试日期（可选）</label>
          <input v-model="filter.exam_date" type="date" class="form-input" />
        </div>
        <div class="form-group" style="align-self: flex-end">
          <button class="btn btn-primary" @click="loadData" :disabled="loading">
            {{ loading ? '加载中...' : '🔍 查询' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 成绩分布图 -->
    <div class="charts-grid">
      <div class="card">
        <h3 class="card-title">成绩分布（{{ filter.subject }}）</h3>
        <div v-if="distributionData" style="position:relative;height:260px">
          <canvas ref="barChartRef"></canvas>
        </div>
        <div v-else class="empty-state">
          <div class="icon">📊</div>
          <p>暂无数据，请先查询</p>
        </div>
      </div>

      <!-- 概览指标 -->
      <div class="card">
        <h3 class="card-title">考试概览</h3>
        <div v-if="overviewData.length > 0">
          <div v-for="item in overviewData" :key="item.exam_date" class="overview-item">
            <div class="ov-title">{{ item.paper_title }}</div>
            <div class="ov-date">{{ item.exam_date }}</div>
            <div class="ov-metrics">
              <div class="ov-metric">
                <span class="ov-val">{{ item.avg_score }}</span>
                <span class="ov-key">平均分</span>
              </div>
              <div class="ov-metric">
                <span class="ov-val text-success">{{ item.max_score }}</span>
                <span class="ov-key">最高分</span>
              </div>
              <div class="ov-metric">
                <span class="ov-val text-danger">{{ item.min_score }}</span>
                <span class="ov-key">最低分</span>
              </div>
              <div class="ov-metric">
                <span class="ov-val">{{ item.student_count }}</span>
                <span class="ov-key">参考人数</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state"><div class="icon">📈</div><p>暂无数据</p></div>
      </div>
    </div>

    <!-- 成绩排名表格 -->
    <div class="card ranking-card">
      <h3 class="card-title">成绩排名</h3>
      <div v-if="loading" class="skeleton-table-body">
        <SkeletonLoader v-for="i in 5" :key="i" variant="table-row" />
      </div>
      <div v-else-if="rankingData.length === 0" class="empty-state">
        <div class="icon">🏆</div>
        <p>暂无排名数据，请先查询</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>排名</th>
            <th>学号</th>
            <th>姓名</th>
            <th>成绩</th>
            <th>得分率</th>
            <th>等级</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in rankingData" :key="item.student_id">
            <td>
              <span :class="['rank-badge', `rank-${item.rank}`]">
                {{ item.rank <= 3 ? ['🥇','🥈','🥉'][item.rank-1] : item.rank }}
              </span>
            </td>
            <td>{{ item.student_id }}</td>
            <td>{{ item.name }}</td>
            <td class="font-bold">{{ item.score }} / {{ item.total_score }}</td>
            <td>
              <div class="progress-bar">
                <div class="progress-fill" :style="{width: item.percent + '%', background: getBarColor(item.percent)}"></div>
              </div>
              <span class="percent-text">{{ item.percent }}%</span>
            </td>
            <td>
              <span :class="['badge', getLevelBadge(item.grade_level)]">{{ item.grade_level }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { statsApi } from '@/api'
import { ALL_SUBJECTS, DEFAULT_SUBJECT } from '@/constants'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const filter = ref({ subject: DEFAULT_SUBJECT, exam_date: '' })
const rankingData = ref([])
const overviewData = ref([])
const distributionData = ref(null)
const loading = ref(false)
const barChartRef = ref(null)
let chartInstance = null

const loadData = async () => {
  loading.value = true
  try {
    const [ranking, overview, dist] = await Promise.all([
      statsApi.getClassRanking(filter.value.subject, filter.value.exam_date || null),
      statsApi.getClassOverview(null, filter.value.subject),
      statsApi.getScoreDistribution(filter.value.subject, filter.value.exam_date || null),
    ])
    rankingData.value = ranking || []
    overviewData.value = overview || []
    distributionData.value = dist

    await nextTick()
    renderChart(dist)
  } catch (e) {
    rankingData.value = []
    overviewData.value = []
  } finally {
    loading.value = false
  }
}

const renderChart = async (dist) => {
  if (!dist || !barChartRef.value) return
  // 动态导入 Chart.js
  const { Chart, registerables } = await import('chart.js')
  Chart.register(...registerables)
  if (chartInstance) chartInstance.destroy()
  chartInstance = new Chart(barChartRef.value, {
    type: 'bar',
    data: {
      labels: dist.labels,
      datasets: [{
        label: '人数',
        data: dist.values,
        backgroundColor: ['#4f46e5', '#06b6d4', '#f59e0b', '#ef4444'],
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  })
}

const getBarColor = (pct) => pct >= 90 ? '#10b981' : pct >= 75 ? '#06b6d4' : pct >= 60 ? '#f59e0b' : '#ef4444'
const getLevelBadge = (l) => l === '优秀' ? 'badge-success' : l === '良好' ? 'badge-info' : l === '及格' ? 'badge-warning' : 'badge-danger'

onMounted(loadData)
</script>

<style scoped>
.analysis-page { padding: 28px; max-width: 1200px; }
.page-header { margin-bottom: 24px; }
.filter-card { margin-bottom: 20px; }
.filter-row { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.form-group { margin-bottom: 0; }
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.ranking-card { }
.rank-badge { font-size: 16px; }
.font-bold { font-weight: 600; }
.progress-bar {
  display: inline-block; width: 80px; height: 6px; background: #e2e8f0;
  border-radius: 3px; vertical-align: middle; margin-right: 6px; overflow: hidden;
}
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.percent-text { font-size: 13px; color: var(--text-secondary); }
.overview-item {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 12px;
}
.ov-title { font-weight: 600; font-size: 14px; margin-bottom: 2px; }
.ov-date { font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; }
.ov-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.ov-metric { text-align: center; }
.ov-val { display: block; font-size: 20px; font-weight: 700; }
.ov-key { font-size: 11px; color: var(--text-secondary); }
@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
