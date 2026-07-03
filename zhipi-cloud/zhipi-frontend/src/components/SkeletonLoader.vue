<template>
  <span
    class="skeleton"
    :class="[variant]"
    :style="inlineStyle"
    :aria-hidden="true"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 变体：text | card | avatar | table-row | block */
  variant: {
    type: String,
    default: 'text',
    validator: v => ['text', 'card', 'avatar', 'table-row', 'block'].includes(v),
  },
  /** 自定义宽度 */
  width:    { type: [String, Number], default: '' },
  /** 自定义高度（text/block 生效） */
  height:   { type: [String, Number], default: '' },
  /** 圆角 */
  radius:   { type: [String, Number], default: '' },
})

const inlineStyle = computed(() => {
  const s = {}
  if (props.width)  s.width   = typeof props.width  === 'number' ? `${props.width}px`  : props.width
  if (props.height) s.height  = typeof props.height === 'number' ? `${props.height}px` : props.height
  if (props.radius) s.borderRadius = typeof props.radius === 'number' ? `${props.radius}px` : props.radius
  return s
})
</script>

<style scoped>
.skeleton {
  display: block;
  background: linear-gradient(
    90deg,
    var(--skeleton-base, #e2e8f0) 25%,
    var(--skeleton-shine, #f1f5f9) 50%,
    var(--skeleton-base, #e2e8f0) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite ease-in-out;
  border-radius: var(--radius-sm);
}

.skeleton.text {
  height: 14px;
  border-radius: 7px;
}

.skeleton.card {
  width: 100%;
  min-height: 120px;
  border-radius: var(--radius);
}

.skeleton.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton.table-row {
  width: 100%;
  height: 48px;
  border-radius: 4px;
}

.skeleton.block {
  width: 100%;
  min-height: 200px;
  border-radius: var(--radius);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
