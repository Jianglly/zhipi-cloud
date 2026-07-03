<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
        @click="dismiss(toast.id)"
      >
        <span class="toast-icon">{{ icons[toast.type] }}</span>
        <span class="toast-message">{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' }
const toasts = ref([])
let idCounter = 0

function show(message, type = 'info', duration = 3000) {
  const id = ++idCounter
  toasts.value.push({ id, message, type })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
}

function dismiss(id) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx !== -1) toasts.value.splice(idx, 1)
}

function success(msg, dur) { show(msg, 'success', dur) }
function error(msg, dur)   { show(msg, 'error', dur || 5000) }
function warning(msg, dur) { show(msg, 'warning', dur) }
function info(msg, dur)    { show(msg, 'info', dur) }

defineExpose({ success, error, warning, info, show })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  background: #fff;
  box-shadow: 0 4px 24px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.06);
  cursor: pointer;
  pointer-events: all;
  min-width: 280px;
  max-width: 420px;
  border-left: 4px solid transparent;
}

.toast-success { border-left-color: #22c55e; }
.toast-error   { border-left-color: #ef4444; }
.toast-warning { border-left-color: #f59e0b; }
.toast-info    { border-left-color: #6366f1; }

.toast-icon {
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}
.toast-success .toast-icon { color: #22c55e; }
.toast-error   .toast-icon { color: #ef4444; }
.toast-warning .toast-icon { color: #f59e0b; }
.toast-info    .toast-icon { color: #6366f1; }

.toast-message { flex: 1; line-height: 1.4; }

/* Transition */
.toast-enter-active { transition: all 0.3s ease-out; }
.toast-leave-active { transition: all 0.2s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to   { opacity: 0; transform: translateX(40px); }
</style>
