<template>
  <div class="admin-classes">
    <div class="page-header">
      <div>
        <h1 class="page-title">班级管理</h1>
        <p class="page-subtitle">管理班级信息与师生分配</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">+ 新增班级</button>
    </div>

    <div class="card">
      <table class="table" v-if="!loading">
        <thead>
          <tr>
            <th>班级编号</th><th>班级名称</th><th>年级</th><th>院系</th>
            <th>学生数</th><th>教师数</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in list" :key="c.class_id">
            <td>{{ c.class_id }}</td>
            <td>{{ c.class_name }}</td>
            <td>{{ c.grade }}</td>
            <td>{{ c.department || '-' }}</td>
            <td><span class="badge badge-info">{{ c.student_count }}</span></td>
            <td><span class="badge badge-success">{{ c.teacher_count }}</span></td>
            <td>
              <div class="action-btns">
                <button class="btn-sm btn-outline" @click="openEdit(c)">编辑</button>
                <button class="btn-sm btn-danger" @click="handleDelete(c)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="list.length === 0"><td colspan="7" class="empty-row">暂无班级数据</td></tr>
        </tbody>
      </table>
      <div v-else class="loading-state">加载中...</div>
    </div>

    <!-- 弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-box">
        <h3>{{ editMode ? '编辑班级' : '新增班级' }}</h3>
        <div class="modal-form">
          <div class="form-group" v-if="!editMode">
            <label>班级编号</label>
            <input v-model="form.class_id" class="form-input" placeholder="如 2501（入学年份+班级号）" />
          </div>
          <div class="form-group">
            <label>班级名称</label>
            <input v-model="form.class_name" class="form-input" placeholder="如 高三年级6班" />
          </div>
          <div class="form-group">
            <label>年级</label>
            <input v-model="form.grade" class="form-input" placeholder="如 2025" />
          </div>
          <div class="form-group">
            <label>院系</label>
            <input v-model="form.department" class="form-input" placeholder="如 高中部" />
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

const list = ref([])
const loading = ref(false)
const showModal = ref(false)
const editMode = ref(false)
const saving = ref(false)
const form = ref({})

async function loadData() {
  loading.value = true
  try { list.value = await adminApi.getClasses() || [] }
  catch { list.value = [] }
  finally { loading.value = false }
}

function openCreate() {
  editMode.value = false
  form.value = { class_id: '', class_name: '', grade: '', department: '' }
  showModal.value = true
}

function openEdit(c) {
  editMode.value = true
  form.value = { class_id: c.class_id, class_name: c.class_name, grade: c.grade, department: c.department || '' }
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editMode.value) {
      await adminApi.updateClass(form.value.class_id, {
        class_name: form.value.class_name, grade: form.value.grade, department: form.value.department,
      })
    } else {
      await adminApi.createClass(form.value)
    }
    showModal.value = false
    await loadData()
  } catch (e) { alert(e.message) }
  finally { saving.value = false }
}

async function handleDelete(c) {
  if (!confirm(`确认删除班级 ${c.class_name}？`)) return
  try { await adminApi.deleteClass(c.class_id); await loadData() }
  catch (e) { alert(e.message) }
}

onMounted(loadData)
</script>

<style scoped>
.admin-classes { padding: 28px; max-width: 1000px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.loading-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.empty-row { text-align: center; padding: 24px; color: var(--text-secondary); }
.action-btns { display: flex; gap: 6px; }
.btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; background: white; }
.btn-outline { color: var(--primary); border-color: var(--primary); }
.btn-danger { color: #dc2626; border-color: #ef4444; background: #fef2f2; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-box { background: white; border-radius: 16px; padding: 28px; width: 90%; max-width: 420px; }
.modal-box h3 { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
.modal-form { display: flex; flex-direction: column; gap: 14px; }
.modal-form .form-group { display: flex; flex-direction: column; gap: 4px; }
.modal-form label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
</style>
