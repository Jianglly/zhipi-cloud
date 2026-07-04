<template>
  <div class="papers-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">试卷管理</h1>
        <p class="page-subtitle">创建和管理考试试卷，录入标准答案</p>
      </div>
      <button class="btn btn-primary" @click="openCreateModal">+ 新建试卷</button>
    </div>

    <div class="card">
      <div v-if="loading" class="skeleton-table-body">
        <SkeletonLoader v-for="i in 5" :key="i" variant="table-row" />
      </div>
      <div v-else-if="validPapers.length === 0" class="empty-state">
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
            <th>标准答案</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in validPapers" :key="p.paper_id">
            <td style="font-weight:500">{{ p.title }}</td>
            <td><span class="badge badge-info">{{ p.subject }}</span></td>
            <td>{{ p.class_name || p.class_id }}</td>
            <td>{{ p.total_score }}</td>
            <td>{{ p.exam_date }}</td>
            <td>
              <span v-if="p.has_answer_key" class="badge badge-success">已录入</span>
              <span v-else class="badge badge-warning">未录入</span>
            </td>
            <td>
              <span :class="['badge', statusBadge[p.status]]">{{ p.status_text }}</span>
            </td>
            <td>
              <div class="action-btns">
                <button class="btn btn-outline btn-sm" @click="openAnswerKeyModal(p)" title="录入/编辑标准答案">
                  答案
                </button>
                <button class="btn btn-outline btn-sm btn-danger-outline" @click="confirmDelete(p)" title="删除试卷">
                  删除
                </button>
              </div>
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
            <label class="label">总分</label>
            <input v-model.number="newPaper.total_score" type="number" class="form-input" placeholder="默认150" min="1" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">适用班级 *</label>
            <select v-model="newPaper.class_id" class="form-select" :disabled="classListLoading">
              <option value="" disabled>请选择班级</option>
              <option v-for="c in classList" :key="c.class_id" :value="c.class_id">
                {{ c.class_name }} ({{ c.class_id }})
              </option>
            </select>
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
          <button class="btn btn-primary" @click="createPaper" :disabled="creating || !isFormValid">
            {{ creating ? '创建中...' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 标准答案录入弹窗 -->
    <div v-if="showAnswerKeyModal" class="modal-overlay" @click.self="closeAnswerKeyModal">
      <div class="modal-box modal-box-lg">
        <h3 class="modal-title">录入标准答案</h3>
        <div v-if="answerKeyLoading" class="loading-text">加载中...</div>
        <template v-else>
          <!-- 试卷信息 -->
          <div class="paper-info-bar">
            <span class="info-tag">{{ answerKeyPaper.title }}</span>
            <span class="info-tag">{{ answerKeyPaper.subject }}</span>
            <span class="info-tag">总分 {{ answerKeyPaper.total_score }}</span>
            <span v-if="answerKeyPaper.total_questions" class="info-tag">已录入 {{ answerKeyPaper.total_questions }} 题</span>
          </div>

          <!-- 题目列表 -->
          <div class="answer-key-list">
            <div v-for="(item, idx) in answerKeyItems" :key="idx" class="ak-row"
                 :class="{ 'ak-subjective': item.type === 'subjective', 'ak-fillblank': item.type === 'fill_blank' }">
              <div class="ak-row-left">
                <input v-model="item.q" class="ak-q-input" placeholder="题号" />
                <select v-model="item.type" class="ak-type-select" @change="onTypeChange(item)">
                  <option value="objective">选择题</option>
                  <option value="fill_blank">填空题</option>
                  <option value="subjective">主观题</option>
                </select>
              </div>
              <div class="ak-row-right">
                <template v-if="item.type === 'objective'">
                  <input v-model="item.answer" class="ak-ans-input" placeholder="正确答案（如 A、B、AB）" />
                </template>
                <template v-else>
                  <input v-model="item.answer" class="ak-ans-input ak-ans-long" :placeholder="item.type === 'fill_blank' ? '参考答案' : '参考答案'" />
                  <input v-model.number="item.score" type="number" class="ak-score-input" placeholder="分值" min="0" />
                  <input v-if="item.type === 'subjective'" v-model="item.keywords" class="ak-kw-input" placeholder="关键词（逗号分隔）" />
                </template>
                <button class="ak-del-btn" @click="removeAnswerItem(idx)" title="删除此题">✕</button>
              </div>
            </div>
          </div>

          <button class="btn btn-outline btn-sm add-q-btn" @click="addAnswerItem">+ 添加题目</button>

          <!-- 批量输入区 -->
          <div class="bulk-input-area">
            <details>
              <summary class="bulk-toggle">批量输入（展开后可快速粘贴多题答案）</summary>
              <div class="bulk-hint">
                格式：每行一题<br>
                选择题：<code>q1=A</code><br>
                填空题：<code>q3=参考答案|分值|fill</code><br>
                主观题：<code>q5=参考答案|分值|关键词1,关键词2</code>
              </div>
              <textarea v-model="bulkText" class="form-input bulk-textarea" rows="5"
                placeholder="q1=A&#10;q2=B&#10;q3=C&#10;q4=D&#10;q5=ACID特性包括原子性、一致性、隔离性、持久性|20|原子性,一致性,隔离性,持久性"></textarea>
              <button class="btn btn-outline btn-sm" @click="parseBulkText">解析并填充</button>
            </details>
          </div>

          <div v-if="answerKeyError" class="error-msg">{{ answerKeyError }}</div>
          <div v-if="answerKeySuccess" class="success-msg">{{ answerKeySuccess }}</div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click="closeAnswerKeyModal">关闭</button>
            <button class="btn btn-primary" @click="saveAnswerKey" :disabled="savingAnswerKey">
              {{ savingAnswerKey ? '保存中...' : '保存标准答案' }}
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal-box">
        <h3 class="modal-title">确认删除</h3>
        <p class="delete-warn">
          确定要删除试卷 <strong>「{{ deleteTarget.title }}」</strong> 吗？
        </p>
        <p class="delete-warn-sub">
          删除后，该试卷关联的所有学生成绩记录也将被删除，此操作不可撤销。
        </p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showDeleteModal = false">取消</button>
          <button class="btn btn-danger" @click="doDelete" :disabled="deleting">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <transition name="toast-fade">
      <div v-if="toast.show" :class="['toast', `toast-${toast.type}`]">{{ toast.msg }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { paperApi } from '@/api'
import { ALL_SUBJECTS, DEFAULT_SUBJECT } from '@/constants'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const papers = ref([])
const loading = ref(false)
const showCreateModal = ref(false)
const allSubjects = ALL_SUBJECTS
const creating = ref(false)
const createError = ref('')

// 班级下拉数据
const classList = ref([])
const classListLoading = ref(false)

const statusBadge = { 0: 'badge-gray', 1: 'badge-info', 2: 'badge-warning', 3: 'badge-success' }

// 过滤掉无效的空行数据（title 为空的记录不显示）
const validPapers = computed(() =>
  papers.value.filter(p => p && p.title && p.title.trim())
)

const newPaper = ref({
  title: '',
  subject: DEFAULT_SUBJECT,
  class_id: '',
  total_score: 150,
  exam_date: '',
  description: '',
})

// 表单校验
const isFormValid = computed(() =>
  newPaper.value.title?.trim() &&
  newPaper.value.class_id &&
  newPaper.value.exam_date
)

// 获取今天的日期字符串 YYYY-MM-DD
const todayStr = () => {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

// ============ Toast ============
const toast = reactive({ show: false, msg: '', type: 'success' })
const showToast = (msg, type = 'success') => {
  toast.msg = msg
  toast.type = type
  toast.show = true
  setTimeout(() => { toast.show = false }, 3000)
}

// ============ 加载数据 ============
const loadPapers = async () => {
  loading.value = true
  try {
    papers.value = await paperApi.getList() || []
  } catch (e) {
    console.error('[PapersView] 加载失败:', e)
    papers.value = []
  } finally {
    loading.value = false
  }
}

const loadClassList = async () => {
  classListLoading.value = true
  try {
    classList.value = await paperApi.getClasses() || []
  } catch (e) {
    console.error('[PapersView] 获取班级列表失败:', e)
    classList.value = []
  } finally {
    classListLoading.value = false
  }
}

// ============ 创建试卷 ============
const openCreateModal = async () => {
  createError.value = ''
  newPaper.value = {
    title: '',
    subject: DEFAULT_SUBJECT,
    class_id: '',
    total_score: 150,
    exam_date: todayStr(),
    description: '',
  }
  showCreateModal.value = true
  if (classList.value.length === 0) await loadClassList()
}

const createPaper = async () => {
  if (!isFormValid.value) {
    createError.value = '请填写必填项：试卷标题、适用班级、考试日期'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    await paperApi.create(newPaper.value)
    showCreateModal.value = false
    newPaper.value = { title: '', subject: DEFAULT_SUBJECT, class_id: '', total_score: 150, exam_date: todayStr(), description: '' }
    await loadPapers()
    showToast('试卷创建成功')
  } catch (e) {
    createError.value = e.message || '创建失败'
  } finally {
    creating.value = false
  }
}

// ============ 标准答案录入 ============
const showAnswerKeyModal = ref(false)
const answerKeyLoading = ref(false)
const answerKeyPaper = ref({})
const answerKeyItems = ref([])
const bulkText = ref('')
const answerKeyError = ref('')
const answerKeySuccess = ref('')
const savingAnswerKey = ref(false)

const openAnswerKeyModal = async (paper) => {
  showAnswerKeyModal.value = true
  answerKeyLoading.value = true
  answerKeyError.value = ''
  answerKeySuccess.value = ''
  answerKeyItems.value = []
  bulkText.value = ''
  try {
    const detail = await paperApi.getDetail(paper.paper_id)
    answerKeyPaper.value = detail
    // 如果已有 answer_key，填充到列表
    if (detail.answer_key && typeof detail.answer_key === 'object') {
      for (const [q, val] of Object.entries(detail.answer_key)) {
        if (typeof val === 'string') {
          answerKeyItems.value.push({ q, type: 'objective', answer: val, score: null, keywords: '' })
        } else if (typeof val === 'object' && val.type === 'fill_blank') {
          answerKeyItems.value.push({
            q,
            type: 'fill_blank',
            answer: val.answer || '',
            score: val.score || null,
            keywords: '',
          })
        } else if (typeof val === 'object' && (val.type === 'subjective' || !val.type)) {
          answerKeyItems.value.push({
            q,
            type: 'subjective',
            answer: val.answer || '',
            score: val.score || null,
            keywords: (val.keywords || []).join(','),
          })
        }
      }
    }
    // 如果没有题目，预填一行
    if (answerKeyItems.value.length === 0) {
      addAnswerItem()
    }
  } catch (e) {
    answerKeyError.value = '加载试卷详情失败：' + (e.message || '未知错误')
  } finally {
    answerKeyLoading.value = false
  }
}

const closeAnswerKeyModal = () => {
  showAnswerKeyModal.value = false
  answerKeyItems.value = []
  bulkText.value = ''
  answerKeyError.value = ''
  answerKeySuccess.value = ''
}

const addAnswerItem = () => {
  const nextNum = answerKeyItems.value.length + 1
  answerKeyItems.value.push({
    q: `q${nextNum}`,
    type: 'objective',
    answer: '',
    score: null,
    keywords: '',
  })
}

const removeAnswerItem = (idx) => {
  answerKeyItems.value.splice(idx, 1)
}

const onTypeChange = (item) => {
  if (item.type === 'objective') {
    item.score = null
    item.keywords = ''
  } else {
    if (!item.score) item.score = 10
    if (item.type === 'fill_blank') {
      item.keywords = ''
    }
  }
}

// 批量文本解析
const parseBulkText = () => {
  const lines = bulkText.value.trim().split('\n').filter(l => l.trim())
  if (lines.length === 0) {
    answerKeyError.value = '请输入内容后再解析'
    return
  }
  answerKeyError.value = ''
  const newItems = []
  for (const line of lines) {
    const eqIdx = line.indexOf('=')
    if (eqIdx === -1) {
      answerKeyError.value = `格式错误，缺少"="：${line}`
      return
    }
    const q = line.substring(0, eqIdx).trim()
    const rest = line.substring(eqIdx + 1).trim()
    // 检查是否有 | 分隔（填空题/主观题）
    if (rest.includes('|')) {
      const parts = rest.split('|')
      const lastPart = (parts[parts.length - 1] || '').trim().toLowerCase()
      if (lastPart === 'fill') {
        // 填空题格式：q3=参考答案|分值|fill
        newItems.push({
          q,
          type: 'fill_blank',
          answer: (parts[0] || '').trim(),
          score: parts[1] ? Number(parts[1].trim()) : 5,
          keywords: '',
        })
      } else {
        // 主观题格式：q5=参考答案|分值|关键词1,关键词2
        newItems.push({
          q,
          type: 'subjective',
          answer: (parts[0] || '').trim(),
          score: parts[1] ? Number(parts[1].trim()) : 10,
          keywords: (parts[2] || '').trim(),
        })
      }
    } else {
      newItems.push({
        q,
        type: 'objective',
        answer: rest,
        score: null,
        keywords: '',
      })
    }
  }
  answerKeyItems.value = newItems
  showToast(`已解析 ${newItems.length} 道题目`)
}

// 保存标准答案
const saveAnswerKey = async () => {
  answerKeyError.value = ''
  answerKeySuccess.value = ''

  // 过滤掉空行
  const validItems = answerKeyItems.value.filter(item => item.q.trim() && item.answer.trim())
  if (validItems.length === 0) {
    answerKeyError.value = '请至少录入一道题的答案'
    return
  }

  // 构建 answer_key JSON
  const answerKey = {}
  for (const item of validItems) {
    if (item.type === 'fill_blank') {
      answerKey[item.q.trim()] = {
        type: 'fill_blank',
        answer: item.answer.trim(),
        score: item.score || 5,
      }
    } else if (item.type === 'subjective') {
      answerKey[item.q.trim()] = {
        type: 'subjective',
        answer: item.answer.trim(),
        score: item.score || 10,
        keywords: item.keywords ? item.keywords.split(',').map(k => k.trim()).filter(Boolean) : [],
      }
    } else {
      answerKey[item.q.trim()] = item.answer.trim()
    }
  }

  savingAnswerKey.value = true
  try {
    await paperApi.update(answerKeyPaper.value.paper_id, { answer_key: answerKey })
    answerKeySuccess.value = '标准答案保存成功！'
    showToast('标准答案保存成功')
    await loadPapers()
    // 刷新详情
    const detail = await paperApi.getDetail(answerKeyPaper.value.paper_id)
    answerKeyPaper.value = detail
  } catch (e) {
    answerKeyError.value = '保存失败：' + (e.message || '未知错误')
  } finally {
    savingAnswerKey.value = false
  }
}

// ============ 删除试卷 ============
const showDeleteModal = ref(false)
const deleteTarget = ref({})
const deleting = ref(false)

const confirmDelete = (paper) => {
  deleteTarget.value = paper
  showDeleteModal.value = true
}

const doDelete = async () => {
  deleting.value = true
  try {
    await paperApi.delete(deleteTarget.value.paper_id)
    showDeleteModal.value = false
    showToast('试卷已删除')
    await loadPapers()
  } catch (e) {
    showToast('删除失败：' + (e.message || '未知错误'), 'error')
  } finally {
    deleting.value = false
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
  max-height: 90vh; overflow-y: auto;
}
.modal-box-lg { width: 700px; }
.modal-title { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.modal-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }

/* 表单标签统一样式 */
.label { font-weight: 500; color: var(--text); font-size: 14px; margin-bottom: 6px; display: block; }

/* 操作按钮 */
.action-btns { display: flex; gap: 6px; }
.btn-danger-outline { color: #ef4444; border-color: #fca5a5; }
.btn-danger-outline:hover { background: #fef2f2; }
.btn-danger { background: #ef4444; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 500; }
.btn-danger:hover { background: #dc2626; }

/* 答案录入弹窗 */
.loading-text { text-align: center; padding: 40px; color: #94a3b8; }
.paper-info-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.info-tag {
  background: #f1f5f9; color: #475569; font-size: 12px; font-weight: 500;
  padding: 4px 10px; border-radius: 6px;
}

.answer-key-list { display: flex; flex-direction: column; gap: 8px; max-height: 350px; overflow-y: auto; padding: 4px; }
.ak-row {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc;
}
.ak-subjective { border-color: #c7d2fe; background: #eef2ff; }
.ak-fillblank { border-color: #fde68a; background: #fffbeb; }
.ak-row-left { display: flex; gap: 6px; flex-shrink: 0; }
.ak-row-right { display: flex; gap: 6px; flex: 1; align-items: center; }
.ak-q-input { width: 60px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.ak-type-select { padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; background: #fff; }
.ak-ans-input { flex: 1; min-width: 80px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.ak-ans-long { min-width: 150px; }
.ak-score-input { width: 60px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.ak-kw-input { flex: 1; min-width: 100px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.ak-del-btn {
  width: 28px; height: 28px; border: none; background: #fee2e2; color: #ef4444;
  border-radius: 6px; cursor: pointer; font-size: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.ak-del-btn:hover { background: #fecaca; }

.add-q-btn { margin-top: 10px; }

/* 批量输入区 */
.bulk-input-area { margin-top: 16px; border-top: 1px solid #e2e8f0; padding-top: 12px; }
.bulk-toggle { cursor: pointer; font-size: 13px; color: #4f46e5; font-weight: 500; }
.bulk-hint { font-size: 12px; color: #64748b; margin: 8px 0; line-height: 1.6; }
.bulk-hint code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 11px; }
.bulk-textarea { font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; }

.error-msg { color: #ef4444; font-size: 13px; margin-top: 8px; }
.success-msg { color: #22c55e; font-size: 13px; margin-top: 8px; }

.delete-warn { font-size: 15px; color: #1e293b; margin-bottom: 8px; }
.delete-warn-sub { font-size: 13px; color: #64748b; }

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
