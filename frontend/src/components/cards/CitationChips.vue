<template>
  <div v-if="items.length" class="citation-chips">
    <button
      v-for="item in items"
      :key="item.citation"
      type="button"
      class="citation-chip"
      @click="emitFollowUp(item)"
    >
      <span class="citation-index">[{{ item.citation }}]</span>
      <span class="citation-title">{{ item.title }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  citations: { type: Array, default: () => [] },
  sources: { type: Array, default: () => [] }
})
const emit = defineEmits(['follow-up'])

const items = computed(() => {
  const sourceMap = new Map((props.sources || []).map((source) => [source.citation, source]))
  return [...new Set(props.citations || [])]
    .map((citation) => sourceMap.get(citation))
    .filter(Boolean)
})

const emitFollowUp = (source) => {
  emit('follow-up', `请进一步解释资料「${source.title}」中与当前问题相关的内容。`)
}
</script>

<style scoped>
.citation-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.citation-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.74);
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, color 0.2s ease;
}

.citation-chip:hover {
  border-color: rgba(120, 190, 255, 0.55);
  background: rgba(120, 190, 255, 0.1);
  color: rgba(255, 255, 255, 0.95);
}

.citation-index {
  color: rgba(120, 190, 255, 0.9);
  font-variant-numeric: tabular-nums;
}

.citation-title {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
