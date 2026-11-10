<template>
  <section class="ui-card">
    <header class="ui-card-head">
      <div>
        <span class="ui-card-eyebrow">相关章节</span>
        <h4 class="ui-card-title">继续学习的方向</h4>
      </div>
      <span class="ui-card-count">{{ items.length }} 个</span>
    </header>

    <div class="chapter-chips">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="chapter-chip"
        @click="askChapter(item)"
      >
        <span class="chapter-title">{{ item.title }}</span>
        <span class="chapter-id">{{ item.id }}</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: { type: Object, required: true },
  chapters: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['follow-up'])

const items = computed(() =>
  (props.card?.chapterIds || []).map((id) => ({
    id,
    title: props.chapters?.[id] || id
  }))
)

const askChapter = (chapter) => {
  emit('follow-up', `请结合知识库讲解「${chapter.title}」这个章节的核心知识点和学习顺序。`)
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

.chapter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chapter-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.chapter-chip:hover {
  border-color: rgba(120, 190, 255, 0.5);
  background: rgba(120, 190, 255, 0.08);
}

.chapter-id {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}
</style>
