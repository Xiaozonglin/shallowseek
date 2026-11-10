<template>
  <div v-if="cards.length" class="answer-cards">
    <template v-for="(card, index) in cards" :key="index">
      <source-list-card
        v-if="card.type === 'source_list'"
        :card="card"
        :sources="sources"
        @follow-up="onFollowUp"
      />
      <guide-card
        v-else-if="card.type === 'guide'"
        :card="card"
        :sources="sources"
        @follow-up="onFollowUp"
      />
      <related-chapters-card
        v-else-if="card.type === 'related_chapters'"
        :card="card"
        :chapters="chapters"
        @follow-up="onFollowUp"
      />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SourceListCard from './SourceListCard.vue'
import GuideCard from './GuideCard.vue'
import RelatedChaptersCard from './RelatedChaptersCard.vue'

const props = defineProps({
  ui: { type: Object, default: null },
  sources: { type: Array, default: () => [] },
  chapters: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['follow-up'])

const cards = computed(() => (props.ui && props.ui.version === 1 ? props.ui.cards || [] : []))
const onFollowUp = (prompt) => emit('follow-up', prompt)
</script>

<style scoped>
.answer-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}
</style>
