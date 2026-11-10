<template>
  <div v-if="hasContent" class="tool-trace" :class="{ compact }">
    <button type="button" class="tool-trace-head" @click="open = !open">
      <span v-if="status" class="tool-trace-status">
        <span class="tool-trace-dot" />
        {{ status }}
      </span>
      <span v-else class="tool-trace-status">
        已完成 {{ trace.length }} 次工具调用
        <template v-if="durationMs"> · {{ durationText }}</template>
      </span>
      <span class="tool-trace-toggle">{{ open ? '收起' : '执行过程' }}</span>
    </button>

    <transition name="trace-fade">
      <ul v-if="open && trace.length" class="tool-trace-list">
        <li v-for="(item, index) in trace" :key="index" class="tool-trace-item" :class="{ failed: item.ok === false }">
          <span class="tool-trace-name">{{ label(item.name) }}</span>
          <span class="tool-trace-args">{{ item.arguments }}</span>
          <span class="tool-trace-ms">{{ item.ms }}ms</span>
        </li>
      </ul>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  trace: { type: Array, default: () => [] },
  durationMs: { type: Number, default: 0 },
  status: { type: String, default: '' },
  compact: { type: Boolean, default: false }
})

const open = ref(false)
const hasContent = computed(() => Boolean(props.status) || props.trace.length > 0)
const durationText = computed(() => `${(props.durationMs / 1000).toFixed(1)}s`)

const TOOL_LABELS = {
  retrieve_knowledge: '检索知识库',
  read_source: '读取资料原文',
  safe_math: '计算校验',
  present_ui: '整理卡片'
}

const label = (name) => TOOL_LABELS[name] || name
</script>

<style scoped>
.tool-trace {
  margin-top: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
  overflow: hidden;
}

.tool-trace.compact {
  margin-top: 10px;
}

.tool-trace-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.tool-trace-head:hover {
  color: rgba(255, 255, 255, 0.8);
}

.tool-trace-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tool-trace-dot {
  width: 6px;
  height: 6px;
  flex: none;
  border-radius: 50%;
  background: rgba(120, 190, 255, 0.9);
  animation: toolTracePulse 1.1s ease-in-out infinite;
}

.tool-trace-toggle {
  flex: none;
  color: rgba(120, 190, 255, 0.75);
}

.tool-trace-list {
  margin: 0;
  padding: 0 14px 12px;
  list-style: none;
}

.tool-trace-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 6px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.tool-trace-name {
  flex: none;
  color: rgba(255, 255, 255, 0.78);
}

.tool-trace-args {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(255, 255, 255, 0.38);
}

.tool-trace-ms {
  flex: none;
  font-variant-numeric: tabular-nums;
}

.tool-trace-item.failed .tool-trace-name {
  color: rgba(255, 140, 140, 0.8);
}

.trace-fade-enter-active,
.trace-fade-leave-active {
  transition: opacity 0.18s ease;
}

.trace-fade-enter-from,
.trace-fade-leave-to {
  opacity: 0;
}

@keyframes toolTracePulse {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}
</style>
