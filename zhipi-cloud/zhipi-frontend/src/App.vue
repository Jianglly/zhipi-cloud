<template>
  <router-view />
  <Toast ref="toastRef" />
</template>

<script setup>
import { ref, provide } from 'vue'
import Toast from '@/components/Toast.vue'
import { TOAST_KEY } from '@/composables/useToast'

const toastRef = ref(null)
provide(TOAST_KEY, {
  success: (msg, dur) => toastRef.value?.success(msg, dur),
  error: (msg, dur) => toastRef.value?.error(msg, dur),
  warning: (msg, dur) => toastRef.value?.warning(msg, dur),
  info: (msg, dur) => toastRef.value?.info(msg, dur),
  show: (msg, type, dur) => toastRef.value?.show(msg, type, dur),
})
</script>
