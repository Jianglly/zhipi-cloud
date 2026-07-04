<template>
  <div class="marking-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">批阅管理</h1>
        <p class="page-subtitle">管理学生答卷批阅流程</p>
      </div>
      <button class="btn btn-primary" @click="openBatchModal" v-if="activeTab === 'pending' && pendingList.length > 0">
        ⚡ 批量批阅
      </button>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        :class="['tab-btn', { active: activeTab === 'pending' }]"
        @click="switchTab('pending')"
      >
        ⏳ 待批阅
        <span v-if="pendingList.length" class="tab-badge">{{ pendingList.length }}</span>
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'completed' }]"
        @click="switchTab('completed')"
      >
        ✅ 已批阅
        <span v-if="completedList.length" class="tab-badge green">{{ completedList.length }}</span>
      </button>
    </div>

    <!-- 待批阅列表 -->
    <div v-if="activeTab === 'pending'" class="card list-card">
      <div class="card-header">
        <h3>待批阅列表</h3>
        <button class="btn btn-secondary btn-sm" @click="loadPending">🔄 刷新</button>
      </div>
      <div v-if="loadingPending" class="skeleton-table-body">
        <SkeletonLoader v-for="i in 5" :key="i" variant="table-row" />
      </div>
      <div v-else-if="pendingError" class="error-msg">{{ pendingError }}</div>
      <div v-else-if="pendingList.length === 0" class="empty-state">
        <div class="icon">🎉</div>
        <p>暂无待批阅答卷</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>试卷</th>
            <th>科目</th>
            <th>考试日期</th>
            <th>AI得分</th>
            <th>答卷</th>
            <th>答案</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pendingList" :key="item.score_id">
            <td>{{ item.student_id }}</td>
            <td>{{ item.name }}</td>
            <td class="ellipsis">{{ item.paper_title }}</td>
            <td><span class="badge badge-info">{{ item.subject }}</span></td>
            <td>{{ item.exam_date }}</td>
            <td>
              <span :class="item.ai_score != null ? 'text-indigo fw600' : 'text-gray'">
                {{ item.ai_score ?? '—' }}
              </span>
            </td>
            <td>
              <span v-if="item.answer_image" class="badge badge-success">已上传</span>
              <span v-else class="badge badge-gray">未上传</span>
            </td>
            <td>
              <span v-if="item.has_answer_key" class="badge badge-success">已录入</span>
              <span v-else class="badge badge-warning">未录入</span>
            </td>
            <td><span :class="['badge', getStatusBadge(item.status)]">{{ item.status_text }}</span></td>
            <td>
              <router-link
                :to="{ name: 'TeacherMarkingDetail', params: { paperId: item.paper_id, studentId: item.student_id } }"
                class="btn btn-primary btn-sm"
              >
                批阅
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 已批阅列表 -->
    <div v-if="activeTab === 'completed'" class="card list-card">
      <div class="card-header">
        <h3>已批阅列表</h3>
        <button class="btn btn-secondary btn-sm" @click="loadCompleted">🔄 刷新</button>
      </div>
      <div v-if="loadingCompleted" class="skeleton-table-body">
        <SkeletonLoader v-for="i in 5" :key="i" variant="table-row" />
      </div>
      <div v-else-if="completedError" class="error-msg">{{ completedError }}</div>
      <div v-else-if="completedList.length === 0" class="empty-state">
        <div class="icon">📭</div>
        <p>暂无已批阅答卷</p>
        <p class="empty-hint">提交批改成绩后的记录会显示在这里</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>学号</th>
            <th>姓名</th>
            <th>试卷</th>
            <th>科目</th>
            <th>考试日期</th>
            <th>AI得分</th>
            <th>手工得分</th>
            <th>总分</th>
            <th>排名</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in completedList" :key="item.score_id">
            <td>{{ item.student_id }}</td>
            <td>{{ item.name }}</td>
            <td class="ellipsis">{{ item.paper_title }}</td>
            <td><span class="badge badge-info">{{ item.subject }}</span></td>
            <td>{{ item.exam_date }}</td>
            <td>
              <span :class="item.ai_score != null ? 'text-indigo fw600' : 'text-gray'">
                {{ item.ai_score ?? '—' }}
              </span>
            </td>
            <td class="fw600">{{ item.manual_score ?? '—' }}</td>
            <td class="fw600 text-indigo">{{ item.total_score ?? '—' }}</td>
            <td>
              <span v-if="item.rank_in_class" class="rank-badge">第 {{ item.rank_in_class }} 名</span>
              <span v-else class="text-gray">—</span>
            </td>
            <td>
              <router-link
                :to="{ name: 'TeacherMarkingDetail', params: { paperId: item.paper_id, studentId: item.student_id } }"
                class="btn btn-outline btn-sm"
              >
                查看详情
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 批量批阅弹窗 -->
    <div v-if="showBatchModal" class="modal-overlay" @click.self="!batchProcessing && (showBatchModal = false)">
      <div class="modal-box modal-box-lg">
        <h3 class="modal-title">⚡ 批量批阅</h3>

        <!-- 选择试卷 -->
        <div v-if="!batchProcessing && batchResults.length === 0" class="batch-step">
          <p class="batch-hint">
            选择一张试卷，系统将对所有已上传答卷的学生一键执行 OCR 识别 + 选择题自动批改。
            <strong>填空题/主观题需教师手动评分。</strong>
          </p>

          <div v-if="batchPaperGroups.length === 0" class="empty-batch">
            <div class="icon">📭</div>
            <p>暂无可批量批阅的试卷</p>
            <p class="empty-hint">需要同一试卷下有多个已上传答卷的学生</p>
          </div>

          <div v-else class="paper-select-list">
            <div v-for="group in batchPaperGroups" :key="group.paper_id"
                 :class="['paper-select-card', { selected: selectedBatchPaperId === group.paper_id }]"
                 @click="selectBatchPaper(group)">
              <div class="paper-card-top">
                <span class="paper-card-title">{{ group.paper_title }}</span>
                <span class="badge badge-info">{{ group.subject }}</span>
              </div>
              <div class="paper-card-meta">
                <span>{{ group.readyCount }} 人可批阅</span>
                <span v-if="!group.has_answer_key" class="badge badge-warning">未录入答案</span>
                <span v-else-if="group.has_subjective" class="badge badge-info">含主观题</span>
                <span v-else class="badge badge-success">可批量批阅</span>
              </div>
            </div>
          </div>

          <!-- 选中试卷后显示学生列表 -->
          <div v-if="selectedBatchGroup" class="student-select-area">
            <div class="student-select-header">
              <label class="checkbox-label">
                <input type="checkbox" :checked="allStudentsSelected" @change="toggleSelectAll" />
                <span>全选 ({{ selectedBatchGroup.students.length }} 人)</span>
              </label>
              <span class="selected-count">已选 {{ batchSelectedIds.length }} 人</span>
            </div>
            <div class="student-list-mini">
              <label v-for="s in selectedBatchGroup.students" :key="s.student_id" class="student-item">
                <input type="checkbox" :value="s.student_id" v-model="batchSelectedIds" />
                <span class="stu-name">{{ s.name }}</span>
                <span class="stu-id">{{ s.student_id }}</span>
              </label>
            </div>
          </div>

          <div v-if="batchError" class="error-msg">{{ batchError }}</div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showBatchModal = false">取消</button>
            <button class="btn btn-primary" @click="startBatchGrade"
                    :disabled="!canStartBatch">
              开始批量批阅 ({{ batchSelectedIds.length }} 人)
            </button>
          </div>
        </div>

        <!-- 批处理进度 -->
        <div v-if="batchProcessing || batchResults.length > 0" class="batch-progress-area">
          <!-- 进度条 -->
          <div class="progress-bar-container">
            <div class="progress-bar-fill" :style="{ width: batchProgressPercent + '%' }"></div>
          </div>
          <div class="progress-text">
            {{ batchDoneCount }} / {{ batchTotalCount }}
            <span v-if="batchProcessing" class="progress-status">批阅中...</span>
            <span v-else class="progress-status done">完成</span>
          </div>

          <!-- 当前处理项 -->
          <div v-if="batchProcessing && currentBatchItem" class="current-item">
            <span class="spinner-sm"></span>
            正在批阅：{{ currentBatchItem.name }} ({{ currentBatchItem.student_id }})
          </div>

          <!-- 结果列表 -->
          <div class="batch-result-list">
            <div v-for="r in batchResults" :key="r.student_id" class="batch-result-row"
                 :class="{ 'r-success': r.status === 'done', 'r-error': r.status === 'error' }">
              <span class="r-icon">{{ r.status === 'done' ? '✅' : '❌' }}</span>
              <span class="r-name">{{ r.name }}</span>
              <span class="r-id">{{ r.student_id }}</span>
              <span v-if="r.status === 'done'" class="r-score">AI得分：{{ r.ai_score }}</span>
              <span v-else class="r-err">{{ r.error }}</span>
            </div>
          </div>

          <!-- 批量提交 -->
          <div v-if="!batchProcessing && batchResults.length > 0" class="batch-submit-area">
            <p class="batch-summary">
              共 {{ batchDoneCount }} 人批阅完成，{{ batchErrorCount }} 人失败。
              AI 得分已保存，您可以逐个审核后提交，或一键提交全部。
            </p>
            <div class="modal-actions">
              <button class="btn btn-secondary" @click="closeBatchModal">关闭</button>
              <button class="btn btn-primary" @click="batchSubmitAll" :disabled="batchSubmitting">
                {{ batchSubmitting ? '提交中...' : '一键提交全部成绩' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <transition name="toast-fade">
      <div v-if="toast.show" :class="['toast', `toast-${toast.type}`]">{{ toast.msg }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { paperApi, ocrApi } from '@/api'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const activeTab = ref('pending')
const pendingList = ref([])
const completedList = ref([])
const loadingPending = ref(false)
const loadingCompleted = ref(false)
const pendingError = ref('')
const completedError = ref('')

// ============ Toast ============
const toast = reactive({ show: false, msg: '', type: 'success' })
const showToast = (msg, type = 'success') => {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

const loadPending = async () => {
  loadingPending.value = true
  pendingError.value = ''
  try {
    pendingList.value = await paperApi.getPending() || []
  } catch (e) {
    console.error('[MarkingView] 待批阅列表加载失败:', e)
    pendingError.value = '加载失败：' + (e.message || '未知错误')
    pendingList.value = []
  } finally {
    loadingPending.value = false
  }
}

const loadCompleted = async () => {
  loadingCompleted.value = true
  completedError.value = ''
  try {
    const data = await paperApi.getCompleted() || []
    completedList.value = data
  } catch (e) {
    console.error('[MarkingView] 已批阅列表加载失败:', e)
    completedError.value = '加载失败：' + (e.message || '未知错误，请检查是否已登录')
    completedList.value = []
  } finally {
    loadingCompleted.value = false
  }
}

const switchTab = (tab) => {
  activeTab.value = tab
  if (tab === 'pending') {
    loadPending()
  } else if (tab === 'completed') {
    loadCompleted()
  }
}

const getStatusBadge = (status) => {
  return ['badge-gray', 'badge-warning', 'badge-info', 'badge-success'][status] || 'badge-gray'
}

// ============ 批量批阅 ============
const showBatchModal = ref(false)
const batchPaperGroups = ref([])
const selectedBatchPaperId = ref(null)
const selectedBatchGroup = ref(null)
const batchSelectedIds = ref([])
const batchError = ref('')
const batchProcessing = ref(false)
const batchResults = ref([])
const batchTotalCount = ref(0)
const batchDoneCount = ref(0)
const currentBatchItem = ref(null)
const batchSubmitting = ref(false)

// 按 paper_id 分组，只包含已上传答卷的待批阅学生
const buildPaperGroups = async () => {
  const groups = {}
  for (const item of pendingList.value) {
    if (!item.answer_image) continue // 没上传答卷的跳过
    if (!groups[item.paper_id]) {
      groups[item.paper_id] = {
        paper_id: item.paper_id,
        paper_title: item.paper_title,
        subject: item.subject,
        students: [],
        has_answer_key: item.has_answer_key,
      }
    }
    groups[item.paper_id].students.push(item)
  }

  // 检查是否有主观题
  const groupList = Object.values(groups)
  for (const g of groupList) {
    try {
      const detail = await paperApi.getDetail(g.paper_id)
      g.has_subjective = detail.has_subjective || false
      g.total_questions = detail.total_questions || 0
    } catch {
      g.has_subjective = false
    }
  }

  batchPaperGroups.value = groupList
}

const openBatchModal = async () => {
  showBatchModal.value = true
  batchResults.value = []
  batchError.value = ''
  selectedBatchPaperId.value = null
  selectedBatchGroup.value = null
  batchSelectedIds.value = []
  await buildPaperGroups()
}

const selectBatchPaper = (group) => {
  selectedBatchPaperId.value = group.paper_id
  selectedBatchGroup.value = group
  // 默认全选
  batchSelectedIds.value = group.students.map(s => s.student_id)
  batchError.value = ''
}

const allStudentsSelected = computed(() => {
  if (!selectedBatchGroup.value) return false
  return batchSelectedIds.value.length === selectedBatchGroup.value.students.length
})

const toggleSelectAll = (e) => {
  if (e.target.checked) {
    batchSelectedIds.value = selectedBatchGroup.value.students.map(s => s.student_id)
  } else {
    batchSelectedIds.value = []
  }
}

const canStartBatch = computed(() => {
  if (!selectedBatchGroup.value || batchSelectedIds.value.length === 0) return false
  if (!selectedBatchGroup.value.has_answer_key) {
    batchError.value = '该试卷未录入标准答案，请先到试卷管理录入'
    return false
  }
  batchError.value = ''
  return true
})

const batchProgressPercent = computed(() => {
  if (batchTotalCount.value === 0) return 0
  return Math.round((batchDoneCount.value / batchTotalCount.value) * 100)
})

const batchErrorCount = computed(() => batchResults.value.filter(r => r.status === 'error').length)

const startBatchGrade = async () => {
  if (!canStartBatch.value) return

  const paperId = selectedBatchPaperId.value
  const students = selectedBatchGroup.value.students.filter(s =>
    batchSelectedIds.value.includes(s.student_id)
  )

  batchProcessing.value = true
  batchResults.value = []
  batchTotalCount.value = students.length
  batchDoneCount.value = 0
  currentBatchItem.value = null

  for (const student of students) {
    currentBatchItem.value = student
    try {
      const res = await ocrApi.autoGrade(paperId, student.student_id)
      batchResults.value.push({
        student_id: student.student_id,
        name: student.name,
        status: 'done',
        ai_score: res.ai_score ?? '—',
      })
    } catch (e) {
      batchResults.value.push({
        student_id: student.student_id,
        name: student.name,
        status: 'error',
        error: e.message || '批改失败',
      })
    }
    batchDoneCount.value++
  }

  batchProcessing.value = false
  currentBatchItem.value = null
  showToast(`批量批阅完成：${batchDoneCount.value - batchErrorCount.value} 成功，${batchErrorCount.value} 失败`)
}

// 一键提交全部成绩
const batchSubmitAll = async () => {
  const successResults = batchResults.value.filter(r => r.status === 'done')
  if (successResults.length === 0) {
    showToast('没有可提交的成绩', 'error')
    return
  }

  batchSubmitting.value = true
  const paperId = selectedBatchPaperId.value
  let submitDone = 0
  let submitFail = 0

  for (const r of successResults) {
    try {
      // 用 AI 得分作为最终成绩提交
      const score = typeof r.ai_score === 'number' ? r.ai_score : parseFloat(r.ai_score)
      await paperApi.submitScore(paperId, r.student_id, score || 0)
      submitDone++
    } catch {
      submitFail++
    }
  }

  batchSubmitting.value = false
  showToast(`提交完成：${submitDone} 成功，${submitFail} 失败`)
  closeBatchModal()
  await loadPending()
}

const closeBatchModal = () => {
  showBatchModal.value = false
  batchResults.value = []
  batchProcessing.value = false
  selectedBatchPaperId.value = null
  selectedBatchGroup.value = null
  batchSelectedIds.value = []
}

onMounted(() => {
  loadPending()
})
</script>

<style scoped>
.marking-page { padding: 28px; max-width: 1400px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; color: #1e293b; }
.page-subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }

/* Tab 栏 */
.tab-bar {
  display: flex; gap: 4px; margin-bottom: 20px;
  border-bottom: 2px solid #e2e8f0; padding-bottom: 0;
}
.tab-btn {
  padding: 10px 20px; border: none; background: none;
  font-size: 14px; font-weight: 500; color: #64748b; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: all 0.15s; display: flex; align-items: center; gap: 6px;
}
.tab-btn:hover { color: #334155; }
.tab-btn.active { color: #4f46e5; border-bottom-color: #4f46e5; font-weight: 600; }
.tab-badge {
  background: #f59e0b; color: #fff; font-size: 11px; font-weight: 700;
  padding: 1px 7px; border-radius: 10px;
}
.tab-badge.green { background: #22c55e; }

/* 列表卡片 */
.list-card { margin-bottom: 20px; }
.card-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid #f1f5f9;
}
.card-header h3 { font-size: 15px; font-weight: 600; color: #1e293b; }

.ellipsis { max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.empty-state { padding: 60px 20px; text-align: center; color: #94a3b8; }
.empty-state .icon { font-size: 48px; margin-bottom: 12px; }
.empty-hint { font-size: 13px; color: #cbd5e1; margin-top: 8px; }

.loading { padding: 40px; text-align: center; color: #94a3b8; }

.rank-badge {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 11px; font-weight: 700;
  padding: 2px 10px; border-radius: 10px;
}

.text-indigo { color: #4f46e5; }
.text-gray { color: #94a3b8; }
.fw600 { font-weight: 600; }
.error-msg { color: #ef4444; font-size: 13px; padding: 8px 12px; background: #fef2f2; border-radius: 6px; }

/* 弹窗 */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: white; border-radius: 16px; padding: 32px; width: 520px; max-width: 94vw;
  max-height: 90vh; overflow-y: auto;
}
.modal-box-lg { width: 680px; }
.modal-title { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.modal-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }

/* 批量批阅 */
.batch-hint { font-size: 13px; color: #64748b; line-height: 1.6; margin-bottom: 16px; }
.empty-batch { text-align: center; padding: 30px; color: #94a3b8; }
.empty-batch .icon { font-size: 36px; margin-bottom: 8px; }

.paper-select-list { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
.paper-select-card {
  border: 2px solid #e2e8f0; border-radius: 10px; padding: 12px 16px;
  cursor: pointer; transition: all 0.15s;
}
.paper-select-card:hover { border-color: #c7d2fe; background: #f8faff; }
.paper-select-card.selected { border-color: #4f46e5; background: #eef2ff; }
.paper-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.paper-card-title { font-weight: 600; font-size: 14px; color: #1e293b; }
.paper-card-meta { display: flex; gap: 10px; align-items: center; font-size: 12px; color: #64748b; }

.student-select-area { margin-top: 16px; border-top: 1px solid #e2e8f0; padding-top: 12px; }
.student-select-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.checkbox-label { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }
.selected-count { font-size: 12px; color: #4f46e5; font-weight: 600; }
.student-list-mini {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 6px; max-height: 160px; overflow-y: auto; padding: 4px;
}
.student-item {
  display: flex; align-items: center; gap: 6px; padding: 6px 10px;
  border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-size: 13px;
}
.student-item:hover { background: #f8fafc; }
.stu-name { font-weight: 500; }
.stu-id { color: #94a3b8; font-size: 11px; }

/* 进度条 */
.batch-progress-area { padding: 4px 0; }
.progress-bar-container {
  width: 100%; height: 24px; background: #e2e8f0; border-radius: 12px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; background: linear-gradient(90deg, #4f46e5, #818cf8);
  border-radius: 12px; transition: width 0.4s ease;
}
.progress-text {
  display: flex; align-items: center; gap: 8px; margin-top: 8px;
  font-size: 14px; font-weight: 600; color: #1e293b;
}
.progress-status { font-size: 13px; color: #4f46e5; }
.progress-status.done { color: #22c55e; }

.current-item {
  display: flex; align-items: center; gap: 8px; margin-top: 12px;
  font-size: 13px; color: #64748b; padding: 8px 12px; background: #f1f5f9; border-radius: 6px;
}
.spinner-sm {
  width: 14px; height: 14px; border: 2px solid #cbd5e1; border-top-color: #4f46e5;
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 结果列表 */
.batch-result-list { margin-top: 16px; max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.batch-result-row {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  border-radius: 6px; font-size: 13px;
}
.r-success { background: #f0fdf4; }
.r-error { background: #fef2f2; }
.r-icon { font-size: 14px; }
.r-name { font-weight: 500; min-width: 50px; }
.r-id { color: #94a3b8; font-size: 11px; min-width: 80px; }
.r-score { color: #4f46e5; font-weight: 600; margin-left: auto; }
.r-err { color: #ef4444; margin-left: auto; font-size: 12px; }

/* 批量提交 */
.batch-submit-area { margin-top: 16px; border-top: 1px solid #e2e8f0; padding-top: 12px; }
.batch-summary { font-size: 13px; color: #475569; margin-bottom: 12px; }

/* Toast */
.toast {
  position: fixed; bottom: 24px; right: 24px; padding: 12px 20px;
  border-radius: 8px; font-size: 14px; font-weight: 500; z-index: 200;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.toast-success { background: #22c55e; color: #fff; }
.toast-error { background: #ef4444; color: #fff; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.3s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(10px); }
</style>
