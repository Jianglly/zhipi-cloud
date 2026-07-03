<template>
  <div class="admin-papers">
    <div class="page-header">
      <div>
        <h1 class="page-title">试卷总览</h1>
        <p class="page-subtitle">查看全校所有试卷</p>
      </div>
    </div>

    <div class="toolbar">
      <select v-model="filterSubject" class="form-select" @change="loadData">
        <option value="">全部科目</option>
        <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filterStatus" class="form-select" @change="loadData">
        <option :value="-1">全部状态</option>
        <option :value="0">草稿</option>
        <option :value="1">已发布</option>
        <option :value="2">批阅中</option>
        <option :value="3">已完成</option>
      </select>
    </div>

    <div class="card">
      <table class="table" v-if="!loading">
        <thead>
          <tr>
            <th>ID</th><th>标题</th><th>科目</th><th>班级</th>
            <th>出卷教师</th><th>考试日期</th><th>成绩数</th><th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in list" :key="p.paper_id">
            <td>{{ p.paper_id }}</td>
            <td>{{ p.title }}</td>
            <td><span class="badge badge-info">{{ p.subject }}</span></td>
            <td>{{ p.class_id }}</td>
            <td>{{ p.teacher_name }}</td>
            <td>{{ p.exam_date }}</td>
            <td>{{ p.score_count }}</td>
            <td><span :class="['badge', getStatusClass(p.status)]">{{ p.status_text }}</span></td>
          </tr>
          <tr v-if="list.length === 0"><td colspan="8" class="empty-row">暂无试卷数据</td></tr>
        </tbody>
      </table>
      <div v-else class="loading-state">加载中...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api'
import { ALL_SUBJECTS } from '@/constants'

const subjects = ALL_SUBJECTS
const filterSubject = ref('')
const filterStatus = ref(-1)
const list = ref([])
const loading = ref(false)

const statusClassMap = { 0: 'badge-secondary', 1: 'badge-info', 2: 'badge-warning', 3: 'badge-success' }
const getStatusClass = (s) => statusClassMap[s] || 'badge-secondary'

async function loadData() {
  loading.value = true
  try {
    list.value = await adminApi.getPapers(filterSubject.value || undefined, filterStatus.value) || []
  } catch { list.value = [] }
  finally { loading.value = false }
}

onMounted(loadData)
</script>

<style scoped>
.admin-papers { padding: 28px; max-width: 1200px; }
.page-header { margin-bottom: 20px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.toolbar .form-select { width: 160px; }
.loading-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.empty-row { text-align: center; padding: 24px; color: var(--text-secondary); }
.badge-secondary { background: #f1f5f9; color: #475569; }
</style>
