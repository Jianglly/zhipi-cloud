<template>
  <div class="admin-logs">
    <div class="page-header">
      <div>
        <h1 class="page-title">操作日志</h1>
        <p class="page-subtitle">系统审计追踪记录</p>
      </div>
    </div>

    <div class="toolbar">
      <input v-model="filterUserId" class="form-input search-input" placeholder="按用户ID筛选..." @keyup.enter="loadData" />
      <input v-model="filterModule" class="form-input" placeholder="按模块筛选..." @keyup.enter="loadData" />
      <button class="btn btn-primary" @click="loadData">查询</button>
    </div>

    <div class="card">
      <table class="table" v-if="!loading">
        <thead>
          <tr>
            <th>日志ID</th><th>用户ID</th><th>用户类型</th>
            <th>操作行为</th><th>模块</th><th>IP地址</th><th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in list" :key="log.log_id">
            <td>{{ log.log_id }}</td>
            <td>{{ log.user_id }}</td>
            <td><span class="badge badge-info">{{ log.user_type_text }}</span></td>
            <td>{{ log.action }}</td>
            <td>{{ log.module }}</td>
            <td>{{ log.ip_address || '-' }}</td>
            <td class="time-cell">{{ formatTime(log.created_at) }}</td>
          </tr>
          <tr v-if="list.length === 0"><td colspan="7" class="empty-row">暂无日志记录</td></tr>
        </tbody>
      </table>
      <div v-else class="loading-state">加载中...</div>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button class="btn-sm btn-outline" :disabled="page <= 1" @click="page--; loadData()">上一页</button>
      <span class="page-info">第 {{ page }} 页 / 共 {{ totalPages }} 页 ({{ total }} 条)</span>
      <button class="btn-sm btn-outline" :disabled="page >= totalPages" @click="page++; loadData()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '@/api'

const filterUserId = ref('')
const filterModule = ref('')
const list = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function loadData() {
  loading.value = true
  try {
    const res = await adminApi.getLogs(filterUserId.value, filterModule.value, page.value, pageSize)
    list.value = res.items || []
    total.value = res.total || 0
  } catch { list.value = [] }
  finally { loading.value = false }
}

function formatTime(ts) {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

onMounted(loadData)
</script>

<style scoped>
.admin-logs { padding: 28px; max-width: 1200px; }
.page-header { margin-bottom: 20px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.search-input { flex: 1; min-width: 160px; }
.loading-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.empty-row { text-align: center; padding: 24px; color: var(--text-secondary); }
.time-cell { font-size: 12px; white-space: nowrap; color: var(--text-secondary); }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 20px; }
.page-info { font-size: 13px; color: var(--text-secondary); }
.btn-sm { padding: 6px 12px; font-size: 13px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer; background: white; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { color: var(--primary); border-color: var(--primary); }
</style>
