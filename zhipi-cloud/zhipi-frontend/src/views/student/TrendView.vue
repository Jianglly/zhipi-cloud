<template>
  <div class="trend-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">成绩趋势</h1>
        <p class="page-subtitle">查看历次考试成绩走势与排名变化</p>
      </div>
    </div>

    <!-- 科目筛选 -->
    <div class="card filter-row">
      <label class="form-label" style="margin:0">选择科目：</label>
      <div class="subject-tabs">
        <button
          v-for="s in subjects"
          :key="s"
          :class="['subject-btn', filterSubject === s ? 'active' : '']"
          @click="filterSubject = s; loadTrend()"
        >
          {{ s }}
        </button>
      </div>
    </div>

    <!-- 趋势折线图 -->
    <div class="card chart-card">
      <h3 class="card-title">成绩趋势折线图 · {{ filterSubject }}</h3>
      <div v-if="loading" class="skeleton-block skeleton-chart">
        <SkeletonLoader variant="block" height="280px" />
      </div>
      <div v-else-if="trendData.length === 0" class="empty-state">
        <div class="icon">📈</div>
        <p>暂无该科目的考试趋势数据</p>
      </div>
      <div v-else style="position:relative;height:300px">
        <canvas ref="lineChartRef"></canvas>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="card" v-if="trendData.length > 0">
      <h3 class="card-title">历次成绩明细</h3>
      <table class="table">
        <thead>
          <tr>
            <th>考试日期</th>
            <th>科目</th>
            <th>成绩</th>
            <th>总分</th>
            <th>得分率</th>
            <th>班级排名</th>
            <th>变化趋势</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in trendData" :key="idx">
            <td>{{ item.exam_date }}</td>
            <td><span class="badge badge-info">{{ item.subject }}</span></td>
            <td>
              <span :class="getScoreColor(item.score, item.total_score)" style="font-weight:600">
                {{ item.score }}
              </span>
            </td>
            <td>{{ item.total_score }}</td>
            <td>{{ Math.round(item.score / item.total_score * 100) }}%</td>
            <td>{{ item.rank_in_class ? `第 ${item.rank_in_class} 名` : '—' }}</td>
            <td>
              <span v-if="idx === 0" class="trend-tag trend-neutral">—</span>
              <span v-else-if="item.score > trendData[idx-1].score" class="trend-tag trend-up">📈 上升</span>
              <span v-else-if="item.score < trendData[idx-1].score" class="trend-tag trend-down">📉 下降</span>
              <span v-else class="trend-tag trend-neutral">➡️ 持平</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { statsApi } from '@/api'
import { ALL_SUBJECTS, DEFAULT_SUBJECT } from '@/constants'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const subjects = ALL_SUBJECTS
const filterSubject = ref(DEFAULT_SUBJECT)
const trendData = ref([])
const loading = ref(false)
const lineChartRef = ref(null)
let chartInstance = null

const loadTrend = async () => {
  loading.value = true
  try {
    trendData.value = await statsApi.getMyTrend(filterSubject.value) || []
    await nextTick()
    if (trendData.value.length > 0) renderChart()
  } finally {
    loading.value = false
  }
}

const renderChart = async () => {
  if (!lineChartRef.value) return
  const { Chart, registerables } = await import('chart.js')
  Chart.register(...registerables)
  if (chartInstance) chartInstance.destroy()

  const labels = trendData.value.map(d => d.exam_date)
  const scores = trendData.value.map(d => d.score)
  const percents = trendData.value.map(d => Math.round(d.score / d.total_score * 100))

  chartInstance = new Chart(lineChartRef.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '原始分',
          data: scores,
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 6,
          pointHoverRadius: 8,
          yAxisID: 'y',
        },
        {
          label: '得分率%',
          data: percents,
          borderColor: '#4f46e5',
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          tension: 0.4,
          pointRadius: 4,
          yAxisID: 'y1',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              if (ctx.datasetIndex === 0) return `成绩：${ctx.raw} 分`
              return `得分率：${ctx.raw}%`
            }
          }
        }
      },
      scales: {
        y: {
          type: 'linear',
          position: 'left',
          title: { display: true, text: '分数' },
        },
        y1: {
          type: 'linear',
          position: 'right',
          title: { display: true, text: '得分率 (%)' },
          grid: { drawOnChartArea: false },
          min: 0,
          max: 100,
        }
      }
    }
  })
}

const getScoreColor = (score, total) => {
  const pct = (score / total) * 100
  return pct >= 80 ? 'text-success' : pct >= 60 ? 'text-warning' : 'text-danger'
}

onMounted(loadTrend)
</script>

<style scoped>
.trend-page { padding: 28px; max-width: 1100px; }
.page-header { margin-bottom: 20px; }
.filter-row { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; padding: 14px 20px; }
.subject-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.subject-btn {
  padding: 6px 16px; border-radius: 20px; border: 1px solid var(--border);
  background: white; cursor: pointer; font-size: 14px; color: var(--text-secondary); transition: all 0.2s;
}
.subject-btn:hover { border-color: #06b6d4; color: #06b6d4; }
.subject-btn.active { background: #06b6d4; color: white; border-color: #06b6d4; }
.chart-card { margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.trend-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.trend-up { color: #065f46; background: #d1fae5; }
.trend-down { color: #991b1b; background: #fee2e2; }
.trend-neutral { color: #475569; background: #f1f5f9; }
</style>
