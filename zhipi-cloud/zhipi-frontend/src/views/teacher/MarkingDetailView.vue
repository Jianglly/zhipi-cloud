<template>
  <div class="marking-detail-page">
    <!-- 顶部导航栏 -->
    <div class="detail-header">
      <button class="back-btn" @click="goBack">⬅️ 返回批阅列表</button>
      <div class="header-info">
        <span class="student-name">{{ currentItem?.name }}</span>
        <span class="student-id">{{ currentItem?.student_id }}</span>
        <span class="separator">|</span>
        <span class="paper-title">{{ currentItem?.paper_title }}</span>
      </div>
      <div class="header-status">
        <span :class="['badge', currentItem ? getStatusBadge(currentItem.status) : '']">
          {{ currentItem?.status_text }}
        </span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <div class="spinner-large"></div>
      <p>加载阅卷数据...</p>
    </div>

    <!-- 批阅工作区 -->
    <div v-else-if="currentItem" class="workspace">
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
            <button class="tool-btn" title="放大" @click="zoomIn" :disabled="scale >= 5">🔍+</button>
            <button class="tool-btn" title="缩小" @click="zoomOut" :disabled="scale <= 0.1">🔍−</button>
            <button class="tool-btn" title="适应窗口" @click="fitToContainer">☐</button>
            <button class="tool-btn" title="旋转" @click="rotateImage">🔄</button>
            <button class="tool-btn" title="1:1 原始大小" @click="resetImage">1:1</button>
            <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
            <span class="tool-hint">滚轮缩放 · 左键拖拽移动</span>
          </div>
          <div
            class="image-container"
            ref="imageContainer"
            @wheel.prevent="onWheel"
            @mousedown="onMouseDown"
            @mousemove="onMouseMove"
            @mouseup="onMouseUp"
            @mouseleave="onMouseUp"
          >
            <img
              :src="previewUrl || backendUrl(currentItem.answer_image)"
              :style="imageStyle"
              alt="学生答卷"
              ref="previewImage"
              @load="onImageLoad"
              @dragstart.prevent
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

        <!-- AI操作区 -->
        <div class="tool-section">
          <h4 class="section-title">🤖 智能识别</h4>
          <div class="btn-group">
            <label class="btn btn-outline btn-sm upload-label" v-if="!previewUrl && !currentItem.answer_image" @click="triggerUpload">
              <input ref="fileInput2" type="file" accept="image/*" style="display:none" @change="handleUpload($event)" />
              📷 上传
            </label>
            <button class="btn btn-primary btn-sm ai-grade-btn" @click="runAutoGrade" :disabled="gradeLoading || !(previewUrl || currentItem.answer_image)">
              <span v-if="gradeLoading" class="spinner"></span>
              {{ gradeLoading ? '识别中...' : '🤖 选择题识别+批改' }}
            </button>
          </div>
          <div v-if="aiScore > 0" class="ai-badge">
            选择题自动得分：<strong>{{ aiScore }}</strong> 分
            <span v-if="hasTextQuestions" class="ai-badge-hint">（填空题/主观题请手动评分）</span>
          </div>
        </div>

        <!-- 逐题批改区 -->
        <div class="tool-section" v-if="answerKey && Object.keys(answerKey).length > 0">
          <h4 class="section-title">📋 逐题批改</h4>

          <!-- 教师总分输入框 -->
          <div class="manual-total-row">
            <label class="manual-total-label">教师总分：</label>
            <div class="manual-total-input-wrap">
              <input
                v-model.number="manualOverride"
                type="number"
                class="manual-total-input"
                :min="0"
                :max="maxTotal"
                step="0.5"
                placeholder="手动输入"
              />
              <span class="manual-total-suffix">/ {{ maxTotal }}</span>
            </div>
            <button class="btn btn-xs btn-ghost" @click="manualOverride = manualTotal" title="同步自动计算分值">同步</button>
          </div>

          <div class="question-list">
            <div v-for="(correctAns, q) in answerKey" :key="q" class="question-row"
                 :class="{
                   'q-correct': studentAnswers[q]?.manualCorrect === true,
                   'q-wrong': studentAnswers[q]?.manualCorrect === false,
                   'q-subjective': isSubjective(q),
                   'q-fillblank': isFillBlank(q)
                 }">
              <!-- 题头 -->
              <div class="q-header">
                <span class="q-num">{{ q }}</span>
                <span class="q-type-tag q-type-obj" v-if="isObjective(q)">选择题</span>
                <span class="q-type-tag q-type-fb" v-else-if="isFillBlank(q)">填空题</span>
                <span class="q-type-tag" v-else>主观题</span>
                <span class="q-answer-label">{{ isObjective(q) ? '标准答案：' : '参考答案：' }}</span>
                <code class="q-answer" v-if="isObjective(q)">{{ correctAns }}</code>
                <span class="q-max-score" v-else>/{{ correctAns.score }}分</span>
              </div>

              <!-- 选择题：识别填涂 + ✓/✗ + 直接打分 -->
              <template v-if="isObjective(q)">
                <div class="q-body">
                  <div class="q-student-ans">
                    <span class="q-label">学生答案：</span>
                    <span v-if="studentAnswers[q]?.ocrAns" class="bubble-ans">{{ studentAnswers[q].ocrAns }}</span>
                    <span v-else class="text-gray">（待识别）</span>
                  </div>
                  <div class="q-actions">
                    <input
                      v-model.number="studentAnswers[q].manualScore"
                      type="number"
                      class="q-score-input q-score-input-sm"
                      :min="0"
                      :max="maxPerQuestion"
                      step="0.5"
                      placeholder="分数"
                    />
                    <span class="q-max-suffix-sm">/{{ maxPerQuestion }}</span>
                    <button
                      :class="['q-btn', studentAnswers[q]?.manualCorrect === true ? 'q-btn-correct active' : '']"
                      @click="markQuestion(q, true)"
                      title="判对">
                      ✓
                    </button>
                    <button
                      :class="['q-btn', studentAnswers[q]?.manualCorrect === false ? 'q-btn-wrong active' : '']"
                      @click="markQuestion(q, false)"
                      title="判错">
                      ✗
                    </button>
                  </div>
                </div>
              </template>

              <!-- 填空题：提取并显示手写答案 + 教师打分 -->
              <template v-else-if="isFillBlank(q)">
                <div class="q-fillblank-ref">参考答案：{{ correctAns.answer }}</div>
                <div class="q-subj-student">
                  <span class="q-label">📝 手写答案：</span>
                  <span v-if="studentAnswers[q]?.ocrAns" class="q-fillblank-text">{{ studentAnswers[q].ocrAns }}</span>
                  <span v-else class="text-gray">（待识别，请查看左侧答卷图片）</span>
                </div>
                <div class="q-body q-subj-actions">
                  <div class="q-score-input-wrap">
                    <span class="q-label">教师给分：</span>
                    <input
                      v-model.number="studentAnswers[q].manualScore"
                      type="number"
                      class="q-score-input"
                      :min="0"
                      :max="correctAns.score"
                      step="0.5"
                      placeholder="分数"
                    />
                    <span class="q-max-suffix">/ {{ correctAns.score }}</span>
                  </div>
                </div>
              </template>

              <!-- 主观题：参考答案 + 学生答案 + 教师打分（无AI批改） -->
              <template v-else>
                <div class="q-subj-ref">参考答案：{{ correctAns.answer }}</div>
                <div class="q-subj-student">
                  <span class="q-label">学生答案：</span>
                  <span class="q-subj-text">{{ studentAnswers[q]?.ocrAns || '（待识别，请查看左侧答卷图片）' }}</span>
                </div>
                <div class="q-body q-subj-actions">
                  <div class="q-score-input-wrap">
                    <span class="q-label">教师给分：</span>
                    <input
                      v-model.number="studentAnswers[q].manualScore"
                      type="number"
                      class="q-score-input"
                      :min="0"
                      :max="correctAns.score"
                      step="0.5"
                      placeholder="分数"
                    />
                    <span class="q-max-suffix">/ {{ correctAns.score }}</span>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- 总分汇总 -->
          <div class="total-bar">
            <div class="total-info">
              <span>已批题数：<strong>{{ gradedCount }}</strong> / {{ totalQuestions }}</span>
              <span>自动合计：<strong class="text-indigo">{{ manualTotal }}</strong> / {{ maxTotal }}</span>
            </div>
          </div>
        </div>

        <!-- 提交区 -->
        <div class="tool-section">
          <h4 class="section-title">✅ 确认提交</h4>
          <div v-if="!aiScore && !manualOverride && objectiveCount > 0" class="safety-hint">
            ⚠️ 尚未执行选择题识别，建议先点击「选择题识别+批改」获取自动评分参考
          </div>
          <div class="form-group">
            <label class="form-label">评语（可选）</label>
            <textarea v-model="comment" class="form-textarea" rows="2" placeholder="给学生写评语..."></textarea>
          </div>
          <div v-if="submitError" class="error-msg">{{ submitError }}</div>
          <button class="btn btn-primary btn-block submit-btn" @click="confirmSubmit" :disabled="submitting">
            <template v-if="submitting">
              <span class="spinner"></span> 提交中...
            </template>
            <template v-else>
              📤 提交成绩（{{ finalScore }} 分）
            </template>
          </button>
          <p class="submit-note">提交后状态变为"已完成"，不会再出现在待批阅列表中</p>
        </div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else class="error-container">
      <div class="icon">⚠️</div>
      <p>加载失败，请返回重试</p>
      <button class="btn btn-secondary" @click="goBack">返回列表</button>
    </div>

    <!-- ========== 自定义确认弹窗（替代原生 window.confirm）========== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="confirmModal.visible" class="modal-overlay" @click.self="confirmModal.onCancel">
          <div class="modal-dialog">
            <div class="modal-icon">📋</div>
            <h3 class="modal-title">{{ confirmModal.title }}</h3>
            <div class="modal-body">
              <p v-for="(line, i) in confirmModal.lines" :key="i" class="modal-line">{{ line }}</p>
            </div>
            <div class="modal-actions">
              <button class="btn modal-btn-cancel" @click="confirmModal.onCancel">取消</button>
              <button class="btn modal-btn-confirm" @click="confirmModal.onOk">确认提交</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { paperApi, ocrApi } from '@/api'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const route = useRoute()
const router = useRouter()

// ============ 核心数据 ============
const currentItem = ref(null)
const loading = ref(true)

// ============ 图片预览状态 ============
const previewUrl = ref('')
const fileInput = ref(null)
const fileInput2 = ref(null)
const previewImage = ref(null)
const imageContainer = ref(null)
const scale = ref(1)
const rotation = ref(0)
const imageLoaded = ref(false)

// 图片位移（translate，单位 px）
const imgX = ref(0)
const imgY = ref(0)

// 拖拽状态
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartImgX = ref(0)
const dragStartImgY = ref(0)

// ============ OCR / 批改状态 ============
const ocrLoading = ref(false)
const gradeLoading = ref(false)
const ocrResult = ref(null)
const aiScore = ref(0)
const gradeDetail = ref([])

// ============ 答案数据 ============
const answerKey = ref({})
const studentAnswers = reactive({})

// ============ 教师手动总分覆盖 ============
const manualOverride = ref(null)

// ============ 提交 ============
const comment = ref('')
const submitting = ref(false)
const submitError = ref('')

// ============ 自定义确认弹窗 ============
const confirmModal = reactive({
  visible: false,
  title: '',
  lines: [],
  onOk: () => {},
  onCancel: () => {}
})

// ============ 计算属性 ============
const totalQuestions = computed(() => Object.keys(answerKey.value).length)
const hasTextQuestions = computed(() => {
  return Object.values(answerKey.value).some(v => typeof v === 'object')
})
const maxTotal = computed(() => {
  const keys = Object.keys(answerKey.value)
  if (keys.length === 0) return 150
  let textTotal = 0  // 填空题+主观题总分
  let objectiveCount = 0
  for (const q of keys) {
    const v = answerKey.value[q]
    if (v && typeof v === 'object') {
      textTotal += v.score || 0
    } else {
      objectiveCount++
    }
  }
  if (textTotal > 0) {
    return Math.max(textTotal, 150)
  }
  return 150
})
const objectiveScoreTotal = computed(() => {
  // 选择题部分的总分 = 试卷总分 - 填空题/主观题总分
  const keys = Object.keys(answerKey.value)
  let textTotal = 0
  for (const q of keys) {
    const v = answerKey.value[q]
    if (v && typeof v === 'object') {
      textTotal += v.score || 0
    }
  }
  return Math.max(maxTotal.value - textTotal, 0)
})
const objectiveCount = computed(() => {
  return Object.values(answerKey.value).filter(v => typeof v === 'string').length
})
const maxPerQuestion = computed(() => {
  if (objectiveCount.value === 0) return 0
  return Math.round((objectiveScoreTotal.value / objectiveCount.value) * 10) / 10
})

const manualTotal = computed(() => {
  let sum = 0
  for (const q in studentAnswers) {
    const val = parseFloat(studentAnswers[q]?.manualScore)
    if (!isNaN(val)) sum += val
  }
  return Math.round(sum * 10) / 10
})

// 最终提交分数：教师手动输入优先，否则用自动计算值
const finalScore = computed(() => {
  if (manualOverride.value != null && !isNaN(manualOverride.value)) {
    return Math.round(manualOverride.value * 10) / 10
  }
  return manualTotal.value
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

// ============ 图片样式（核心）================
const imageStyle = computed(() => {
  const transitioning = isDragging.value ? 'none' : 'transform 0.12s cubic-bezier(0.16, 1, 0.3, 1)'
  return {
    position: 'absolute',
    transform: 'translate(' + imgX.value + 'px, ' + imgY.value + 'px) scale(' + scale.value + ') rotate(' + rotation.value + 'deg)',
    transformOrigin: '0 0',
    transition: transitioning,
    cursor: isDragging.value ? 'grabbing' : 'grab',
    userSelect: 'none',
    maxWidth: 'none',
    maxHeight: 'none',
  }
})

// ============ 工具函数 ============
const backendUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return '/' + path.replace(/^\/+/, '')
}

const getContainerCursorPos = (e) => {
  const container = imageContainer.value
  if (!container) return { cx: 0, cy: 0 }
  const rect = container.getBoundingClientRect()
  return {
    cx: e.clientX - rect.left,
    cy: e.clientY - rect.top,
  }
}

// ============ 滚轮缩放（跟随光标位置）================
const onWheel = (e) => {
  e.preventDefault()
  const container = imageContainer.value
  if (!container) return

  const { cx, cy } = getContainerCursorPos(e)
  const oldScale = scale.value
  const delta = e.deltaY < 0 ? 0.15 : -0.15
  const newScale = Math.max(0.1, Math.min(5, oldScale + delta))

  // 光标所在位置对应的图片坐标（相对于图片左上角，单位：原始图片 px）
  const imgCoordX = (cx - imgX.value) / oldScale
  const imgCoordY = (cy - imgY.value) / oldScale

  // 缩放后，保持该图片坐标在光标位置不动
  imgX.value = Math.round(cx - imgCoordX * newScale)
  imgY.value = Math.round(cy - imgCoordY * newScale)
  scale.value = newScale
}

// ============ 鼠标拖拽平移 ============
const onMouseDown = (e) => {
  if (e.button !== 0) return
  if (!imageLoaded.value) return
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY
  dragStartImgX.value = imgX.value
  dragStartImgY.value = imgY.value
  e.preventDefault()
}

const onMouseMove = (e) => {
  if (!isDragging.value) return
  imgX.value = dragStartImgX.value + (e.clientX - dragStartX.value)
  imgY.value = dragStartImgY.value + (e.clientY - dragStartY.value)
}

const onMouseUp = () => {
  isDragging.value = false
}

// ============ 图片加载完成 ============
const onImageLoad = () => {
  imageLoaded.value = true
  fitToContainer()
}

// ============ 适应窗口 ============
const fitToContainer = () => {
  const container = imageContainer.value
  const img = previewImage.value
  if (!container || !img) return

  const cw = container.clientWidth
  const ch = container.clientHeight
  const iw = img.naturalWidth
  const ih = img.naturalHeight
  if (!iw || !ih) return

  const fitScale = Math.min(cw / iw, ch / ih, 1)
  scale.value = fitScale
  imgX.value = Math.round((cw - iw * fitScale) / 2)
  imgY.value = Math.round((ch - ih * fitScale) / 2)
  rotation.value = 0
}

// ============ 重置为 1:1 并居中 ============
const resetImage = () => {
  const container = imageContainer.value
  const img = previewImage.value
  if (!container || !img) return

  const cw = container.clientWidth
  const ch = container.clientHeight
  const iw = img.naturalWidth
  const ih = img.naturalHeight

  scale.value = 1
  imgX.value = Math.round((cw - iw) / 2)
  imgY.value = Math.round((ch - ih) / 2)
  rotation.value = 0
}

// ============ 放大（居中缩放）================
const zoomIn = () => {
  const container = imageContainer.value
  if (!container) return
  const cx = container.clientWidth / 2
  const cy = container.clientHeight / 2
  const oldScale = scale.value
  const newScale = Math.min(5, oldScale + 0.25)
  const imgCoordX = (cx - imgX.value) / oldScale
  const imgCoordY = (cy - imgY.value) / oldScale
  imgX.value = Math.round(cx - imgCoordX * newScale)
  imgY.value = Math.round(cy - imgCoordY * newScale)
  scale.value = newScale
}

// ============ 缩小（居中缩放）================
const zoomOut = () => {
  const container = imageContainer.value
  if (!container) return
  const cx = container.clientWidth / 2
  const cy = container.clientHeight / 2
  const oldScale = scale.value
  const newScale = Math.max(0.1, oldScale - 0.25)
  const imgCoordX = (cx - imgX.value) / oldScale
  const imgCoordY = (cy - imgY.value) / oldScale
  imgX.value = Math.round(cx - imgCoordX * newScale)
  imgY.value = Math.round(cy - imgCoordY * newScale)
  scale.value = newScale
}

// ============ 旋转 ============
const rotateImage = () => {
  rotation.value = (rotation.value + 90) % 360
}

// ============ 加载阅卷数据 ============
const loadMarkingData = async () => {
  const { paperId, studentId } = route.params
  if (!paperId || !studentId) {
    toast.error('参数错误')
    router.push('/teacher/marking')
    return
  }

  loading.value = true
  try {
    const [pending, completed] = await Promise.all([
      paperApi.getPending().catch(() => []),
      paperApi.getCompleted().catch(() => [])
    ])

    const allItems = [...pending, ...completed]
    const item = allItems.find(
      i => String(i.paper_id) === String(paperId) && String(i.student_id) === String(studentId)
    )

    if (!item) {
      toast.error('未找到该学生的答卷记录')
      router.push('/teacher/marking')
      return
    }

    currentItem.value = item

    if (item.answer_image) {
      previewUrl.value = backendUrl(item.answer_image)
    }

    if (item.manual_score != null) {
      aiScore.value = item.ai_score || 0
      // 如果已有手工分数，填入手动覆盖字段
      manualOverride.value = item.manual_score
    }
  } catch (e) {
    toast.error('加载失败：' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// ============ 图片上传 ============
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
    toast.success('上传成功')
  } catch (e) {
    toast.error('上传失败：' + (e.message || '未知错误'))
  }
  event.target.value = ''
}

// ============ 自动批改（选择题识别+批改）==============
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
    initStudentAnswers()

    // 填充批改结果到 studentAnswers
    gradeDetail.value.forEach(d => {
      if (studentAnswers[d.question]) {
        studentAnswers[d.question].manualCorrect = d.is_correct
        // 选择题自动填充分数，非选择题不自动填充
        if (d.type === 'objective') {
          studentAnswers[d.question].manualScore = d.score
        }
        studentAnswers[d.question].ocrAns = d.student_answer !== '（未识别）' && d.student_answer !== '（待识别）'
          ? d.student_answer
          : (ocrResult.value[d.question] || '')
      }
    })

    const msg = hasTextQuestions.value
      ? `选择题批改完成！自动得分：${res.ai_score} 分（填空题/主观题请手动评分）`
      : `选择题批改完成！得分：${res.ai_score} 分`
    toast.success(msg)
  } catch (e) {
    toast.error('批改失败：' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    gradeLoading.value = false
  }
}

// ============ 判断题目类型 ============
const isObjective = (q) => {
  const ans = answerKey.value[q]
  return typeof ans === 'string'
}
const isFillBlank = (q) => {
  const ans = answerKey.value[q]
  return ans && typeof ans === 'object' && ans.type === 'fill_blank'
}
const isSubjective = (q) => {
  const ans = answerKey.value[q]
  return ans && typeof ans === 'object' && (ans.type === 'subjective' || !ans.type)
}

// ============ 初始化 studentAnswers ============
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

// ============ 手动批改（通过 ✓/✗ 按钮）==============
const markQuestion = (q, correct) => {
  if (!studentAnswers[q]) return
  studentAnswers[q].manualCorrect = correct
  // 对了给满分，错了给0分
  studentAnswers[q].manualScore = correct ? maxPerQuestion.value : 0
}

// ============ 确认提交（自定义弹窗）============
const confirmSubmit = () => {
  if (!currentItem.value) return
  const score = finalScore.value

  confirmModal.title = '确认提交成绩'
  confirmModal.lines = [
    `学生：${currentItem.value.name}（${currentItem.value.student_id}）`,
    `试卷：${currentItem.value.paper_title}`,
    `提交分数：${score} 分 / ${maxTotal.value} 分`,
    '',
    '提交后将标记为「已完成」，不再出现在待批阅列表中。'
  ]
  confirmModal.onOk = () => {
    confirmModal.visible = false
    submitScore()
  }
  confirmModal.onCancel = () => {
    confirmModal.visible = false
  }
  confirmModal.visible = true
}

const submitScore = async () => {
  const score = finalScore.value
  if (score < 0) {
    submitError.value = '分数不能为负数'
    return
  }
  submitting.value = true
  submitError.value = ''
  try {
    await paperApi.submitScore(
      currentItem.value.paper_id,
      currentItem.value.student_id,
      score
    )
    toast.success('成绩提交成功！')
    router.push('/teacher/marking')
  } catch (e) {
    submitError.value = e.response?.data?.detail || e.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

const getStatusBadge = (status) => {
  return ['badge-gray', 'badge-warning', 'badge-info', 'badge-success'][status] || 'badge-gray'
}

const goBack = () => {
  router.push('/teacher/marking')
}

onMounted(loadMarkingData)
</script>

<style scoped>
/* ============ 布局 ============ */
.marking-detail-page {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
  min-height: calc(100vh - 40px);
}

/* 顶部导航 */
.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.back-btn {
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
  transition: all 0.15s;
  white-space: nowrap;
}
.back-btn:hover { background: #f8fafc; border-color: #cbd5e1; }

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.student-name { font-weight: 600; color: #1e293b; font-size: 15px; }
.student-id { color: #94a3b8; font-size: 13px; }
.separator { color: #cbd5e1; }
.paper-title { color: #475569; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 20px;
  color: #94a3b8;
  font-size: 14px;
  gap: 16px;
}
.spinner-large {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 错误状态 */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 20px;
  color: #94a3b8;
  gap: 16px;
}
.error-container .icon { font-size: 48px; }

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
.tool-hint { font-size: 11px; color: #94a3b8; }

.image-container {
  overflow: hidden;
  height: 600px;
  position: relative;
  background: #f1f5f9;
  cursor: grab;
}
.image-container:active { cursor: grabbing; }
.image-container img {
  max-width: none !important;
  max-height: none !important;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  user-select: none;
  -webkit-user-drag: none;
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

/* AI批改主按钮 */
.ai-grade-btn {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  border: none;
  font-weight: 600;
  padding: 10px 24px;
  font-size: 14px;
}
.ai-grade-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #4f46e5, #4338ca);
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
  transform: translateY(-1px);
}
.upload-label { cursor: pointer; }

.ai-badge {
  margin-top: 12px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border-radius: 10px;
  font-size: 13px;
  color: #4338ca;
  text-align: center;
}

/* ======== 教师总分输入行 ======== */
.manual-total-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  margin-bottom: 12px;
}
.manual-total-label {
  font-size: 12px;
  color: #475569;
  font-weight: 600;
  white-space: nowrap;
}
.manual-total-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}
.manual-total-input {
  width: 72px;
  padding: 5px 8px;
  border: 2px solid #6366f1;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  text-align: center;
  color: #4f46e5;
  background: #fff;
  transition: all 0.15s;
}
.manual-total-input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
  border-color: #4f46e5;
}
.manual-total-input::-webkit-inner-spin-button,
.manual-total-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.manual-total-suffix {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
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

.q-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

/* ======== 分数显示框（只读）======== */
.q-score-display {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 30px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  background: #f1f5f9;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
  transition: all 0.2s;
}
.q-score-display.score-correct {
  background: #dcfce7;
  color: #166534;
  border-color: #86efac;
}
.q-score-display.score-wrong {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fca5a5;
}
.q-score-display.score-empty {
  color: #cbd5e1;
}

.q-btn {
  width: 30px; height: 30px;
  border: 1.5px solid #e2e8f0; border-radius: 8px;
  background: #fff; cursor: pointer;
  font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.q-btn:hover { transform: scale(1.1); }
.q-btn-correct.active {
  background: #22c55e; color: #fff; border-color: #22c55e;
  box-shadow: 0 2px 8px rgba(34,197,94,0.35);
}
.q-btn-wrong.active {
  background: #ef4444; color: #fff; border-color: #ef4444;
  box-shadow: 0 2px 8px rgba(239,68,68,0.35);
}

/* ======== 主观题样式 ======== */
.question-row.q-subjective {
  border-color: #c7d2fe;
  background: #f5f3ff;
}
.q-type-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  background: #ede9fe;
  color: #6d28d9;
}
.q-type-tag.q-type-obj {
  background: #f1f5f9;
  color: #64748b;
}
.q-type-tag.q-type-fb {
  background: #fef3c7;
  color: #92400e;
}
.q-max-score {
  font-size: 11px;
  color: #7c3aed;
  font-weight: 600;
}
.q-subj-ref {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  margin: 4px 0;
  padding: 6px 8px;
  background: rgba(255,255,255,0.6);
  border-radius: 6px;
}
.q-subj-student {
  font-size: 12px;
  margin: 4px 0;
}
.q-subj-text {
  color: #2563eb;
  line-height: 1.5;
}
.q-subj-feedback {
  font-size: 12px;
  margin: 4px 0;
  padding: 6px 8px;
  background: #fef3c7;
  border-radius: 6px;
  border: 1px solid #fde68a;
}
.q-feedback-text {
  color: #92400e;
  line-height: 1.4;
}
.q-subj-actions {
  margin-top: 6px;
}
.q-score-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}
.q-score-input {
  width: 60px;
  padding: 4px 8px;
  border: 2px solid #7c3aed;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  color: #6d28d9;
  background: #fff;
}
.q-score-input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(124,58,237,0.15);
}
.q-max-suffix {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

/* ======== 填空题样式 ======== */
.question-row.q-fillblank {
  border-color: #fde68a;
  background: #fffbeb;
}
.q-fillblank-ref {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  margin: 4px 0;
  padding: 6px 8px;
  background: rgba(255,255,255,0.6);
  border-radius: 6px;
}
.q-fillblank-text {
  color: #92400e;
  font-weight: 500;
  line-height: 1.5;
}

/* ======== 选择题气泡答案 ======== */
.bubble-ans {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px; height: 28px;
  background: #eef2ff;
  border: 2px solid #6366f1;
  border-radius: 50%;
  color: #4f46e5;
  font-weight: 700;
  font-size: 14px;
}

/* ======== 选择题分数输入（小尺寸）======== */
.q-score-input-sm {
  width: 50px;
  padding: 3px 6px;
  border: 2px solid #6366f1;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  color: #4f46e5;
  background: #fff;
}
.q-score-input-sm:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.q-max-suffix-sm {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 500;
}

/* ======== AI 提示 ======== */
.ai-badge-hint {
  font-size: 11px;
  color: #92400e;
  margin-left: 4px;
}

/* ======== LLM 大题批改按钮 ======== */
.btn-llm {
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  border: none;
  font-weight: 600;
  padding: 10px 24px;
  font-size: 14px;
}
.btn-llm:hover:not(:disabled) {
  background: linear-gradient(135deg, #6d28d9, #5b21b6);
  box-shadow: 0 4px 14px rgba(124,58,237,0.35);
  transform: translateY(-1px);
}
.btn-llm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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

.submit-btn {
  padding: 12px 20px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  letter-spacing: 0.5px;
}
.submit-btn:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(79,70,229,0.35);
  transform: translateY(-1px);
}

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
.btn-xs { padding: 4px 10px; font-size: 11px; }
.btn-ghost {
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #64748b;
}
.btn-ghost:hover { background: #f8fafc; color: #6366f1; border-color: #c7d2fe; }

/* ============ 工具类 ============ */
.text-indigo { color: #4f46e5; }

/* 按钮样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.btn-primary {
  background: #4f46e5;
  color: #fff;
  border-color: #4f46e5;
}
.btn-primary:hover:not(:disabled) { background: #4338ca; border-color: #4338ca; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: #fff;
  color: #475569;
  border-color: #e2e8f0;
}
.btn-secondary:hover { background: #f8fafc; border-color: #cbd5e1; }

.btn-outline {
  background: #fff;
  color: #475569;
  border-color: #e2e8f0;
}
.btn-outline:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }

.btn-sm { padding: 6px 12px; font-size: 12px; }

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}
.badge-info { background: #dbeafe; color: #1e40af; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-gray { background: #f1f5f9; color: #64748b; }

.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.6s linear infinite;
  margin-right: 4px; vertical-align: middle;
}

/* ============ 自定义确认弹窗（替代原生 window.confirm）============ */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-dialog {
  background: #fff;
  border-radius: 18px;
  padding: 28px 32px 24px;
  width: 380px;
  max-width: 90vw;
  box-shadow:
    0 24px 60px rgba(0,0,0,0.18),
    0 0 0 1px rgba(255,255,255,0.08) inset;
  animation: modalIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-icon {
  font-size: 36px;
  text-align: center;
  margin-bottom: 12px;
}
.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
  margin: 0 0 16px;
}
.modal-body {
  margin-bottom: 20px;
}
.modal-line {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
  margin: 0;
}
.modal-line:first-child {
  color: #1e293b;
  font-weight: 600;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.modal-btn-cancel {
  padding: 9px 20px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
}
.modal-btn-cancel:hover {
  background: #e2e8f0;
}
.modal-btn-confirm {
  padding: 9px 20px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  color: #fff;
  border: none;
  box-shadow: 0 2px 10px rgba(79,70,229,0.3);
}
.modal-btn-confirm:hover {
  background: linear-gradient(135deg, #4338ca, #4f46e5);
  box-shadow: 0 4px 16px rgba(79,70,229,0.4);
  transform: translateY(-1px);
}

/* 弹窗过渡动画 */
.modal-enter-active { transition: all 0.2s ease-out; }
.modal-leave-active { transition: all 0.15s ease-in; }
.modal-enter-from { opacity: 0; }
.modal-leave-to   { opacity: 0; }
</style>
