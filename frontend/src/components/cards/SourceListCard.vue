<template>
  <section class="ui-card">
    <header class="ui-card-head">
      <div>
        <span class="ui-card-eyebrow">参考资料</span>
        <h4 class="ui-card-title">本轮实际使用的资料</h4>
      </div>
      <span class="ui-card-count">{{ items.length }} 份</span>
    </header>

    <a-input
      v-model:value="keyword"
      size="small"
      allow-clear
      placeholder="按标题筛选资料"
      class="ui-card-filter"
    />

    <ul v-if="items.length" class="ui-list">
      <li v-for="source in items" :key="source.citation" class="ui-list-item">
        <div class="ui-list-title">
          <span class="ui-list-index">[{{ source.citation }}]</span>
          <span>{{ source.title }}</span>
        </div>
        <a-button size="small" type="link" @click="askAbout(source)">追问这份资料</a-button>
      </li>
    </ul>
    <a-empty v-else description="没有匹配的资料" />
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  card: { type: Object, required: true },
  sources: { type: Array, default: () => [] }
})
const emit = defineEmits(['follow-up'])

const keyword = ref('')

const items = computed(() => {
  const allowed = new Set(props.card?.citations || [])
  const text = keyword.value.trim().toLowerCase()
  return (props.sources || []).filter(
    (source) => allowed.has(source.citation) && (!text || String(source.title).toLowerCase().includes(text))
  )
})

const askAbout = (source) => {
  emit('follow-up', `请进一步解释资料「${source.title}」与当前问题相关的内容。`)
}
</script>

<style scoped>
.ui-card {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.035);
  padding: 18px;
}

.ui-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.ui-card-eyebrow {
  display: block;
  margin-bottom: 4px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(120, 190, 255, 0.8);
}

.ui-card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
}

.ui-card-count {
  flex: none;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.ui-card-filter {
  margin-bottom: 10px;
}

.ui-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.ui-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.ui-list-item:first-child {
  border-top: none;
}

.ui-list-title {
  display: flex;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.82);
}

.ui-list-index {
  color: rgba(120, 190, 255, 0.9);
  font-variant-numeric: tabular-nums;
  flex: none;
}
</style>
