<template>
  <div class="papers-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">试卷管理</h1>
        <p class="page-subtitle">创建和管理考试试卷</p>
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">+ 新建试卷</button>
    </div>

    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="papers.length === 0" class="empty-state">
        <div class="icon">📝</div>
        <p>还没有试卷，点击右上角创建</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>试卷名称</th>
            <th>科目</th>
            <th>班级</th>
            <th>总分</th>
            <th>考试日期</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in papers" :key="p.paper_id">
            <td style="font-weight:500">{{ p.title }}</td>
            <td><span class="badge badge-info">{{ p.subject }}</span></td>
            <td>{{ p.class_id }}</td>
            <td>{{ p.total_score }}</td>
            <td>{{ p.exam_date }}</td>
            <td>
              <span :class="['badge', statusBadge[p.status]]">{{ p.status_text }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建试卷弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-box">
        <h3 class="modal-title">新建试卷</h3>
        <div class="form-group">
          <label class="form-label">试卷标题 *</label>
          <input v-model="newPaper.title" class="form-input" placeholder="如：2025年期末数据库系统考试" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">科目 *</label>
            <select v-model="newPaper.subject" class="form-select">
              <option v-for="s in allSubjects" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">总分</label>
            <input v-model.number="newPaper.total_score" type="number" class="form-input" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">适用班级 *</label>
            <input v-model="newPaper.class_id" class="form-input" placeholder="如：24计科2班" />
          </div>
          <div class="form-group">
            <label class="form-label">考试日期 *</label>
            <input v-model="newPaper.exam_date" type="date" class="form-input" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">试卷说明（选填）</label>
          <textarea v-model="newPaper.description" class="form-input" rows="2" placeholder="考试范围、注意事项等"></textarea>
        </div>
        <div v-if="createError" class="error-msg">{{ createError }}</div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createPaper" :disabled="creating">
            {{ creating ? '创建中...' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { paperApi } from '@/api'
import { ALL_SUBJECTS, DEFAULT_SUBJECT } from '@/constants'

const papers = ref([])
const loading = ref(false)
const showCreateModal = ref(false)
const allSubjects = ALL_SUBJECTS
const creating = ref(false)
const createError = ref('')

const statusBadge = { 0: 'badge-gray', 1: 'badge-info', 2: 'badge-warning', 3: 'badge-success' }

const newPaper = ref({
  title: '',
  subject: DEFAULT_SUBJECT,
  class_id: '',
  total_score: 150,
  exam_date: '',
  description: '',
})

const loadPapers = async () => {
  loading.value = true
  try {
    papers.value = await paperApi.getList() || []
  } finally {
    loading.value = false
  }
}

const createPaper = async () => {
  if (!newPaper.value.title || !newPaper.value.class_id || !newPaper.value.exam_date) {
    createError.value = '请填写必填项'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    await paperApi.create(newPaper.value)
    showCreateModal.value = false
    newPaper.value = { title: '', subject: DEFAULT_SUBJECT, class_id: '', total_score: 150, exam_date: '', description: '' }
    await loadPapers()
  } catch (e) {
    createError.value = e.message || '创建失败'
  } finally {
    creating.value = false
  }
}

onMounted(loadPapers)
</script>

<style scoped>
.papers-page { padding: 28px; max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: white; border-radius: 16px; padding: 32px; width: 520px; max-width: 94vw;
}
.modal-title { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.modal-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }
</style>
