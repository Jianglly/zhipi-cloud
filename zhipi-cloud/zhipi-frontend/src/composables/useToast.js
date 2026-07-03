/**
 * 全局 Toast 通知 composable
 * 用法：import { useToast } from '@/composables/useToast'
 *      const toast = useToast()
 *      toast.success('操作成功')
 *      toast.error('操作失败：' + message)
 */
import { inject } from 'vue'

export const TOAST_KEY = Symbol('toast')

export function useToast() {
  const toast = inject(TOAST_KEY)
  if (!toast) {
    // 降级：如果 Toast 组件未挂载，回退到 console + alert
    return {
      success: (msg) => console.log('[Toast]', msg),
      error: (msg) => { console.error('[Toast]', msg); alert(msg) },
      warning: (msg) => console.warn('[Toast]', msg),
      info: (msg) => console.info('[Toast]', msg),
      show: (msg) => console.log('[Toast]', msg),
    }
  }
  return toast
}
