<template>
  <div class="admin-users">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理教师和学生账号</p>
      </div>
    </div>

    <!-- 角色切换 -->
    <div class="role-tabs">
      <button :class="['role-tab', tab === 'teacher' ? 'active' : '']" @click="tab = 'teacher'; loadData()">👨‍🏫 教师管理</button>
      <button :class="['role-tab', tab === 'student' ? 'active' : '']" @click="tab = 'student'; loadData()">👨‍🎓 学生管理</button>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <input v-model="keyword" class="form-input search-input" placeholder="搜索姓名或编号..." @keyup.enter="loadData" />
      <select v-if="tab === 'student'" v-model="filterClass" class="form-select" @change="loadData">
        <option value="">全部班级</option>
        <option v-for="c in classes" :key="c.class_id" :value="c.class_id">{{ c.class_name }}</option>
      </select>
      <button class="btn btn-primary" @click="openCreate">+ 新增{{ tab === 'teacher' ? '教师' : '学生' }}</button>
    </div>

    <!-- 列表 -->
    <div class="card">
      <table class="table" v-if="!loading">
        <thead>
          <tr v-if="tab === 'teacher'">
            <th>教师编号</th><th>姓名</th><th>班级</th><th>科目</th><th>批阅任务</th><th>电话</th><th>操作</th>
          </tr>
          <tr v-else>
            <th>学号</th><th>姓名</th><th>班级</th><th>电话</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in list" :key="item.teacher_id || item.student_id">
            <template v-if="tab === 'teacher'">
              <td>{{ item.teacher_id }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.class_id }}</td>
              <td><span class="badge badge-info">{{ item.subject }}</span></td>
              <td>{{ item.task }}</td>
              <td>{{ item.phone || '-' }}</td>
            </template>
            <template v-else>
              <td>{{ item.student_id }}</td>
              <td>{{ item.name }}</td>
              <td>{{ item.class_id }}</td>
              <td>{{ item.phone || '-' }}</td>
            </template>
            <td>
              <div class="action-btns">
                <button class="btn-sm btn-outline" @click="openEdit(item)">编辑</button>
                <button class="btn-sm btn-warning" @click="handleReset(item)">重置密码</button>
                <button class="btn-sm btn-danger" @click="handleDelete(item)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="list.length === 0">
            <td :colspan="tab === 'teacher' ? 7 : 5" class="empty-row">暂无数据</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="loading-state">加载中...</div>
    </div>

    <!-- 编辑/新增弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-box">
        <h3>{{ editMode ? '编辑' : '新增' }}{{ tab === 'teacher' ? '教师' : '学生' }}</h3>
        <div class="modal-form">
          <div class="form-group" v-if="!editMode">
            <label>{{ tab === 'teacher' ? '教师编号' : '学号' }}</label>
            <input v-model="form.user_id" class="form-input" :placeholder="tab === 'teacher' ? '如 T012' : '如 S062'" />
          </div>
          <div class="form-group">
            <label>姓名</label>
            <input v-model="form.name" class="form-input" />
          </div>
          <div class="form-group">
            <label>班级</label>
            <select v-model="form.class_id" class="form-select">
              <option value="">请选择班级</option>
              <option v-for="c in classes" :key="c.class_id" :value="c.class_id">{{ c.class_name }}</option>
            </select>
          </div>
          <div class="form-group" v-if="tab === 'teacher' && !editMode">
            <label>科目</label>
            <input v-model="form.subject" class="form-input" placeholder="如 数学" />
          </div>
          <div class="form-group" v-if="tab === 'teacher' && editMode">
            <label>科目</label>
            <input v-model="form.subject" class="form-input" />
          </div>
          <div class="form-group">
            <label>电话</label>
            <input v-model="form.phone" class="form-input" />
          </div>
          <div class="form-group" v-if="!editMode">
            <label>初始密码</label>
            <input v-model="form.password" class="form-input" placeholder="默认 123456" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="handleSave" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api'

const tab = ref('teacher')
const keyword = ref('')
const filterClass = ref('')
const list = ref([])
const classes = ref([])
const loading = ref(false)
const showModal = ref(false)
const editMode = ref(false)
const saving = ref(false)
const form = ref({})

async function loadClasses() {
  try { classes.value = await adminApi.getClasses() } catch {}
}

async function loadData() {
  loading.value = true
  try {
    if (tab.value === 'teacher') {
      list.value = await adminApi.getTeachers(keyword.value) || []
    } else {
      list.value = await adminApi.getStudents(filterClass.value, keyword.value) || []
    }
  } catch { list.value = [] }
  finally { loading.value = false }
}

function openCreate() {
  editMode.value = false
  form.value = { password: '123456', subject: '', phone: '' }
  showModal.value = true
}

function openEdit(item) {
  editMode.value = true
  if (tab.value === 'teacher') {
    form.value = { teacher_id: item.teacher_id, name: item.name, class_id: item.class_id, subject: item.subject, phone: item.phone || '' }
  } else {
    form.value = { student_id: item.student_id, name: item.name, class_id: item.class_id, phone: item.phone || '' }
  }
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (tab.value === 'teacher') {
      if (editMode.value) {
        await adminApi.updateTeacher(form.value.teacher_id, {
          name: form.value.name, class_id: form.value.class_id,
          subject: form.value.subject, phone: form.value.phone,
        })
      } else {
        await adminApi.createTeacher(form.value)
      }
    } else {
      if (editMode.value) {
        await adminApi.updateStudent(form.value.student_id, {
          name: form.value.name, class_id: form.value.class_id, phone: form.value.phone,
        })
      } else {
        await adminApi.createStudent(form.value)
      }
    }
    showModal.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '保存失败')
  } finally { saving.value = false }
}

async function handleReset(item) {
  const id = item.teacher_id || item.student_id
  if (!confirm(`确认重置 ${item.name} 的密码为 123456？`)) return
  try {
    if (tab.value === 'teacher') {
      await adminApi.resetTeacherPassword(id, '123456')
    } else {
      await adminApi.resetStudentPassword(id, '123456')
    }
    alert('密码已重置为 123456')
  } catch (e) { alert(e.message) }
}

async function handleDelete(item) {
  const id = item.teacher_id || item.student_id
  if (!confirm(`确认删除 ${item.name}？此操作不可撤销！`)) return
  try {
    if (tab.value === 'teacher') await adminApi.deleteTeacher(id)
    else await adminApi.deleteStudent(id)
    await loadData()
  } catch (e) { alert(e.message) }
}

onMounted(async () => {
  await loadClasses()
  await loadData()
})
</script>

<style scoped>
.admin-users { padding: 28px; max-width: 1200px; }
.page-header { margin-bottom: 20px; }
.role-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.role-tab {
  padding: 8px 20px; border: 1px solid var(--border); background: white;
  border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500;
  transition: all 0.2s; color: var(--text-secondary);
}
.role-tab.active { background: #0F6E56; color: white; border-color: #0F6E56; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.search-input { flex: 1; min-width: 200px; }
.toolbar .form-select { width: 160px; }
.loading-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.empty-row { text-align: center; padding: 24px; color: var(--text-secondary); }
.action-btns { display: flex; gap: 6px; }
.btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; background: white; transition: all 0.15s; }
.btn-sm:hover { opacity: 0.85; }
.btn-outline { color: var(--primary); border-color: var(--primary); }
.btn-warning { color: #92400e; border-color: #fbbf24; background: #fffbeb; }
.btn-danger { color: #dc2626; border-color: #ef4444; background: #fef2f2; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-box { background: white; border-radius: 16px; padding: 28px; width: 90%; max-width: 460px; }
.modal-box h3 { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
.modal-form { display: flex; flex-direction: column; gap: 14px; }
.modal-form .form-group { display: flex; flex-direction: column; gap: 4px; }
.modal-form label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
</style>
