<template>
  <div class="marking-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">批阅管理</h1>
        <p class="page-subtitle">查看学生答卷，使用智能工具辅助批改</p>
      </div>
    </div>

    <!-- 待批阅列表 -->
    <div class="card list-card">
      <div class="card-header">
        <h3>待批阅列表</h3>
        <button class="btn btn-secondary btn-sm" @click="loadPending">🔄 刷新</button>
      </div>
      <div v-if="loading" class="loading">加载中...</div>
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
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pendingList" :key="item.score_id"
              :class="{ 'row-active': currentItem?.score_id === item.score_id }">
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
            <td><span :class="['badge', getStatusBadge(item.status)]">{{ item.status_text }}</span></td>
            <td>
              <button class="btn btn-primary btn-sm" @click="selectStudent(item)">
                {{ currentItem?.score_id === item.score_id ? '已选中' : '批阅' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ============ 批阅工作区（选中学生后显示） ============ -->
    <div v-if="currentItem" class="workspace">
      <!-- 左侧：答卷图片 -->
      <div class="panel panel-image">
        <div class="panel-header">
          <h3>📄 学生答卷</h3>
          <span class="panel-subtitle">
            {{ currentItem.name }}（{{ currentItem.student_id }}）
          </span>
        </div>

        <!-- 无图片时显示上传区 -->
        <div v-if="!previewUrl && !currentItem.answer_image" class="upload-zone" @click="triggerUpload">
          <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="handleUpload($event)" />
          <div class="upload-icon">📷</div>
          <p>点击上传学生答卷图片</p>
          <p class="upload-hint">支持 JPG/PNG，建议清晰拍照</p>
        </div>

        <!-- 有图片时显示 -->
        <div v-else class="image-viewer">
          <div class="image-toolbar">
            <button class="tool-btn" title="放大" @click="zoomIn" :disabled="scale >= 3">🔍+</button>
            <button class="tool-btn" title="缩小" @click="zoomOut" :disabled="scale <= 0.3">🔍−</button>
            <button class="tool-btn" title="旋转" @click="rotateImage">🔄</button>
            <button class="tool-btn" title="重置" @click="resetImage">↺</button>
            <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
          </div>
          <div class="image-container" @wheel="handleWheel" ref="imageContainer">
            <img
              :src="previewUrl || backendUrl(currentItem.answer_image)"
              :style="imageStyle"
              alt="学生答卷"
              ref="previewImage"
            />
          </div>
        </div>
      </div>

      <!-- 右侧：批改工具面板 -->
      <div class="panel panel-tools">
        <div class="panel-header">
          <h3>🛠️ 批改工具</h3>
          <span class="panel-subtitle">
            试卷：{{ currentItem.paper_title }}
          </span>
        </div>

        <!-- OCR操作区 -->
        <div class="tool-section">
          <h4 class="section-title">🤖 智能识别</h4>
          <div class="btn-group">
            <label class="btn btn-outline btn-sm" style="cursor:pointer" @click="triggerUpload" v-if="!previewUrl && !currentItem.answer_image">
              <input ref="fileInput2" type="file" accept="image/*" style="display:none" @change="handleUpload($event)" />
              📷 上传
            </label>
            <button class="btn btn-outline btn-sm" @click="runOCR" :disabled="ocrLoading || !(previewUrl || currentItem.answer_image)">
              <span v-if="ocrLoading" class="spinner"></span>
              {{ ocrLoading ? '识别中...' : '📝 OCR识别' }}
            </button>
            <button class="btn btn-outline btn-sm" @click="runAutoGrade" :disabled="gradeLoading">
              <span v-if="gradeLoading" class="spinner"></span>
              {{ gradeLoading ? '批改中...' : '🤖 自动批改' }}
            </button>
          </div>
          <div v-if="aiScore > 0" class="ai-badge">
            AI 评分：<strong>{{ aiScore }}</strong> 分
          </div>
        </div>

        <!-- 逐题批改区 -->
        <div class="tool-section" v-if="answerKey && Object.keys(answerKey).length > 0">
          <h4 class="section-title">📋 逐题批改</h4>
          <div class="question-list">
            <div v-for="(correctAns, q) in answerKey" :key="q" class="question-row"
                 :class="{ 'q-correct': studentAnswers[q]?.manualCorrect === true, 'q-wrong': studentAnswers[q]?.manualCorrect === false }">
              <div class="q-header">
                <span class="q-num">{{ q }}</span>
                <span class="q-answer-label">标准答案：</span>
                <code class="q-answer">{{ correctAns }}</code>
              </div>
              <div class="q-body">
                <div class="q-student-ans">
                  <span class="q-label">学生答案：</span>
                  <span :class="studentAnswers[q]?.ocrAns ? 'text-blue' : 'text-gray'">
                    {{ studentAnswers[q]?.ocrAns || '（待识别）' }}
                  </span>
                </div>
                <div class="q-actions">
                  <input
                    v-model="studentAnswers[q].manualScore"
                    type="number"
                    class="q-score-input"
                    :min="0"
                    :max="maxPerQuestion"
                    :step="0.5"
                    placeholder="分数"
                    @input="recalcTotal"
                  />
                  <button
                    :class="['q-btn', studentAnswers[q]?.manualCorrect === true ? 'q-btn-correct active' : '']"
                    @click="markQuestion(q, true)">
                    ✓
                  </button>
                  <button
                    :class="['q-btn', studentAnswers[q]?.manualCorrect === false ? 'q-btn-wrong active' : '']"
                    @click="markQuestion(q, false)">
                    ✗
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 总分汇总 -->
          <div class="total-bar">
            <div class="total-info">
              <span>已批题数：<strong>{{ gradedCount }}</strong> / {{ totalQuestions }}</span>
              <span>总分：<strong class="text-indigo">{{ manualTotal }}</strong> / {{ maxTotal }}</span>
            </div>
          </div>
        </div>

        <!-- 提交区 -->
        <div class="tool-section">
          <h4 class="section-title">✅ 确认提交</h4>
          <div v-if="!aiScore" class="safety-hint">
            ⚠️ 尚未执行OCR自动批改，提交前建议先点击"自动批改"获取AI评分参考
          </div>
          <div class="form-group">
            <label class="form-label">评语（可选）</label>
            <textarea v-model="comment" class="form-textarea" rows="2" placeholder="给学生写评语..."></textarea>
          </div>
          <div v-if="submitError" class="error-msg">{{ submitError }}</div>
          <button class="btn btn-primary btn-block" @click="confirmSubmit" :disabled="submitting">
            {{ submitting ? '提交中...' : `提交成绩（${manualTotal}分）` }}
          </button>
          <p class="submit-note">提交后状态变为"已完成"，不会再出现在待批阅列表中</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { paperApi, ocrApi } from '@/api'

// 列表数据
const pendingList = ref([])
const loading = ref(false)

// 当前选中学生
const currentItem = ref(null)

// 图片预览
const previewUrl = ref('')
const fileInput = ref(null)
const fileInput2 = ref(null)
const previewImage = ref(null)
const scale = ref(1)
const rotation = ref(0)

// OCR / 批改状态
const ocrLoading = ref(false)
const gradeLoading = ref(false)
const ocrResult = ref(null)
const aiScore = ref(0)
const gradeDetail = ref([])

// 答案数据
const answerKey = ref({})       // { q1: 'A', q2: 'B', ... }
const studentAnswers = reactive({})  // { q1: { ocrAns: 'A', manualCorrect: true, manualScore: 3 } }

// 提交
const comment = ref('')
const submitting = ref(false)
const submitError = ref('')

// 计算属性
const totalQuestions = computed(() => Object.keys(answerKey.value).length)
const maxTotal = computed(() => 150)
const maxPerQuestion = computed(() => {
  if (totalQuestions.value === 0) return 0
  return Math.round(maxTotal.value / totalQuestions.value)
})

const manualTotal = computed(() => {
  let sum = 0
  for (const q in studentAnswers) {
    const val = parseFloat(studentAnswers[q]?.manualScore)
    if (!isNaN(val)) sum += val
  }
  return Math.round(sum * 10) / 10
})

const gradedCount = computed(() => {
  let count = 0
  for (const q in studentAnswers) {
    if (studentAnswers[q]?.manualScore != null && studentAnswers[q]?.manualScore !== '') {
      count++
    }
  }
  return count
})

const imageStyle = computed(() => ({
  transform: `scale(${scale.value}) rotate(${rotation.value}deg)`,
  transition: 'transform 0.2s ease'
}))

// 获取完整URL
const backendUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  return base.replace('/api', '') + '/' + path
}

// ======== 列表操作 ========
const loadPending = async () => {
  loading.value = true
  try {
    pendingList.value = await paperApi.getPending() || []
  } catch (e) {
    pendingList.value = []
  } finally {
    loading.value = false
  }
}

const selectStudent = (item) => {
  currentItem.value = item
  // 切换学生时重置批改状态
  previewUrl.value = ''
  ocrResult.value = null
  aiScore.value = 0
  gradeDetail.value = []
  answerKey.value = {}
  Object.keys(studentAnswers).forEach(k => delete studentAnswers[k])
  comment.value = ''
  submitError.value = ''
  scale.value = 1
  rotation.value = 0

  // 如果已有上传的图片，加载预览
  if (item.answer_image) {
    previewUrl.value = backendUrl(item.answer_image)
  }
}

// ======== 图片操作 ========
const triggerUpload = () => {
  if (fileInput.value) fileInput.value.click()
  else if (fileInput2.value) fileInput2.value.click()
}

const handleUpload = async (event) => {
  const file = event.target.files[0]
  if (!file || !currentItem.value) return
  try {
    const res = await ocrApi.uploadImage(
      currentItem.value.paper_id,
      currentItem.value.student_id,
      file
    )
    previewUrl.value = res.url
    currentItem.value.answer_image = res.file_path
  } catch (e) {
    alert('上传失败：' + (e.message || '未知错误'))
  }
  event.target.value = ''
}

const zoomIn = () => { scale.value = Math.min(3, scale.value + 0.25) }
const zoomOut = () => { scale.value = Math.max(0.3, scale.value - 0.25) }
const rotateImage = () => { rotation.value = (rotation.value + 90) % 360 }
const resetImage = () => { scale.value = 1; rotation.value = 0 }

const handleWheel = (e) => {
  e.preventDefault()
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

// ======== OCR 识别 ========
const runOCR = async () => {
  if (!currentItem.value) return
  ocrLoading.value = true
  try {
    const res = await ocrApi.recognize(
      currentItem.value.paper_id,
      currentItem.value.student_id
    )
    ocrResult.value = res.ocr_result || {}
    answerKey.value = res.answer_key || {}

    // 初始化 studentAnswers
    initStudentAnswers()

    alert(`OCR识别完成！识别率：${res.parse_rate || 'N/A'}`)
  } catch (e) {
    alert('OCR识别失败：' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    ocrLoading.value = false
  }
}

// ======== 自动批改 ========
const runAutoGrade = async () => {
  if (!currentItem.value) return
  gradeLoading.value = true
  try {
    const res = await ocrApi.autoGrade(
      currentItem.value.paper_id,
      currentItem.value.student_id
    )
    aiScore.value = res.ai_score || 0
    gradeDetail.value = res.detail || []
    ocrResult.value = res.ocr_result || {}
    answerKey.value = res.answer_key || {}

    // 初始化 studentAnswers
    initStudentAnswers()

    // 从 detail 中填充每题的批改状态
    gradeDetail.value.forEach(d => {
      if (studentAnswers[d.question]) {
        studentAnswers[d.question].manualCorrect = d.is_correct
        studentAnswers[d.question].manualScore = d.score
        studentAnswers[d.question].ocrAns = d.student_answer
      }
    })

    alert(`自动批改完成！AI得分：${res.ai_score} 分`)
  } catch (e) {
    alert('批改失败：' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    gradeLoading.value = false
  }
}

// 初始化 studentAnswers
const initStudentAnswers = () => {
  for (const q in answerKey.value) {
    if (!studentAnswers[q]) {
      studentAnswers[q] = {
        ocrAns: ocrResult.value[q] || '',
        manualCorrect: null,
        manualScore: null
      }
    } else {
      studentAnswers[q].ocrAns = ocrResult.value[q] || studentAnswers[q].ocrAns || ''
    }
  }
}

// ======== 手动批改 ========
const markQuestion = (q, correct) => {
  if (!studentAnswers[q]) return
  studentAnswers[q].manualCorrect = correct
  if (studentAnswers[q].manualScore == null || studentAnswers[q].manualScore === '') {
    studentAnswers[q].manualScore = correct ? maxPerQuestion.value : 0
  }
  recalcTotal()
}

const recalcTotal = () => {
  // 触发 manualTotal 重新计算
}

// ======== 提交成绩（带确认） ========
const confirmSubmit = () => {
  if (!currentItem.value) return
  const ok = window.confirm(
    `确认提交 "${currentItem.value.name}" 的批改成绩吗？\n\n` +
    `总分：${manualTotal.value} 分\n` +
    `提交后将标记为"已完成"，不再出现在待批阅列表中。`
  )
  if (ok) submitScore()
}

const submitScore = async () => {
  if (manualTotal.value < 0) {
    submitError.value = '分数不能为负数'
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    await paperApi.submitScore(
      currentItem.value.paper_id,
      currentItem.value.student_id,
      manualTotal.value
    )
    // 从列表中移除
    currentItem.value = null
    await loadPending()
  } catch (e) {
    submitError.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

const getStatusBadge = (status) => {
  return ['badge-gray', 'badge-warning', 'badge-info', 'badge-success'][status] || 'badge-gray'
}

onMounted(loadPending)
</script>

<style scoped>
/* ============ 布局 ============ */
.marking-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1e293b; }
.page-subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }

/* 列表卡片 */
.list-card { margin-bottom: 20px; }
.row-active { background: #eef2ff !important; }

/* ============ 工作区（左右分栏） ============ */
.workspace {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 1024px) {
  .workspace { grid-template-columns: 1fr; }
}

/* ============ 面板通用 ============ */
.panel {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 20px rgba(0,0,0,0.04);
  overflow: hidden;
}
.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-header h3 { font-size: 15px; font-weight: 600; color: #1e293b; }
.panel-subtitle { font-size: 12px; color: #94a3b8; }

/* ============ 图片面板 ============ */
.panel-image { min-height: 400px; }

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  margin: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.upload-zone:hover { border-color: #6366f1; background: #f8fafc; }
.upload-icon { font-size: 48px; margin-bottom: 12px; }
.upload-zone p { color: #475569; font-size: 14px; }
.upload-hint { color: #94a3b8 !important; font-size: 12px !important; margin-top: 4px; }

.image-viewer { padding: 0; }
.image-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}
.tool-btn {
  width: 32px; height: 32px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.tool-btn:hover:not(:disabled) { background: #f1f5f9; border-color: #cbd5e1; }
.tool-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.zoom-label { margin-left: auto; font-size: 12px; color: #64748b; font-weight: 500; }

.image-container {
  overflow: auto;
  max-height: 600px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px;
  background: #f1f5f9;
}
.image-container img {
  max-width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  cursor: zoom-in;
}

/* ============ 工具面板 ============ */
.panel-tools { position: sticky; top: 16px; }

.tool-section {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
}
.tool-section:last-child { border-bottom: none; }
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ai-badge {
  margin-top: 12px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border-radius: 10px;
  font-size: 13px;
  color: #4338ca;
  text-align: center;
}

/* 逐题批改 */
.question-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}
.question-row {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  transition: all 0.15s;
}
.question-row.q-correct { border-color: #86efac; background: #f0fdf4; }
.question-row.q-wrong { border-color: #fca5a5; background: #fef2f2; }

.q-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.q-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  background: #6366f1; color: #fff;
  border-radius: 6px; font-size: 11px; font-weight: 700;
  flex-shrink: 0;
}
.q-answer-label { font-size: 11px; color: #94a3b8; }
.q-answer {
  background: #f1f5f9; padding: 2px 8px; border-radius: 4px;
  font-size: 12px; color: #334155; font-weight: 600;
}

.q-body { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.q-student-ans { font-size: 12px; flex: 1; min-width: 0; }
.q-label { color: #94a3b8; }
.text-blue { color: #2563eb; font-weight: 500; }
.text-gray { color: #94a3b8; font-style: italic; }

.q-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.q-score-input {
  width: 56px; padding: 4px 6px; border: 1px solid #e2e8f0;
  border-radius: 6px; font-size: 12px; text-align: center;
}
.q-score-input:focus { outline: none; border-color: #6366f1; }

.q-btn {
  width: 28px; height: 28px;
  border: 1px solid #e2e8f0; border-radius: 6px;
  background: #fff; cursor: pointer;
  font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.q-btn:hover { background: #f8fafc; }
.q-btn-correct.active { background: #22c55e; color: #fff; border-color: #22c55e; }
.q-btn-wrong.active { background: #ef4444; color: #fff; border-color: #ef4444; }

.total-bar {
  margin-top: 12px; padding: 12px;
  background: #f8fafc; border-radius: 10px;
}
.total-info { display: flex; justify-content: space-between; font-size: 13px; color: #475569; }

/* 提交区 */
.form-group { margin-bottom: 12px; }
.form-label { font-size: 13px; color: #64748b; margin-bottom: 6px; display: block; }
.form-textarea {
  width: 100%; padding: 10px 12px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  font-size: 13px; resize: vertical;
  font-family: inherit;
}
.form-textarea:focus { outline: none; border-color: #6366f1; }

.error-msg {
  padding: 8px 12px; background: #fef2f2; color: #dc2626;
  border-radius: 8px; font-size: 12px; margin-bottom: 12px;
}

.safety-hint {
  padding: 8px 12px; background: #fffbeb; color: #b45309;
  border: 1px solid #fde68a; border-radius: 8px;
  font-size: 12px; margin-bottom: 12px;
}

.submit-note {
  font-size: 11px; color: #94a3b8; text-align: center; margin-top: 8px;
}

.btn-block { width: 100%; }
.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid #e2e8f0; border-top-color: #6366f1;
  border-radius: 50%; animation: spin 0.6s linear infinite;
  margin-right: 4px; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ============ 工具类 ============ */
.text-indigo { color: #4f46e5; }
.fw600 { font-weight: 600; }
.ellipsis { max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
