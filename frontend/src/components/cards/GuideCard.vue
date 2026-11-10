<template>
  <section class="ui-card">
    <header class="ui-card-head">
      <div>
        <span class="ui-card-eyebrow">解题步骤</span>
        <h4 class="ui-card-title">{{ card.title }}</h4>
      </div>
      <span class="ui-card-count">{{ steps.length }} 步</span>
    </header>

    <div class="guide-steps">
      <article v-for="(step, index) in steps" :key="index" class="guide-step">
        <div class="guide-step-head">
          <a-checkbox
            :checked="checked.includes(index)"
            class="guide-step-check"
            @change="toggleChecked(index)"
          />
          <button type="button" class="guide-step-toggle" @click="toggleOpen(index)">
            <span class="guide-step-index">{{ index + 1 }}</span>
            <span class="guide-step-title">{{ step.title }}</span>
            <span class="guide-step-chevron">{{ open.includes(index) ? '−' : '+' }}</span>
          </button>
        </div>

        <transition name="step-fade">
          <div v-if="open.includes(index)" class="guide-step-body">
            <p class="guide-step-detail">{{ step.detail }}</p>
            <div class="guide-step-footer">
              <citation-chips
                :citations="step.citations"
                :sources="sources"
                @follow-up="(prompt) => $emit('follow-up', prompt)"
              />
              <a-button size="small" type="link" @click="askStep(step)">追问这一步</a-button>
            </div>
          </div>
        </transition>
      </article>
    </div>

    <p class="guide-note">勾选仅记录本页进度，不会提交到任何系统。</p>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import CitationChips from './CitationChips.vue'

const props = defineProps({
  card: { type: Object, required: true },
  sources: { type: Array, default: () => [] }
})
const emit = defineEmits(['follow-up'])

const steps = computed(() => props.card?.steps || [])
const open = ref([0])
const checked = ref([])

const toggleOpen = (index) => {
  open.value = open.value.includes(index)
    ? open.value.filter((item) => item !== index)
    : [...open.value, index]
}

const toggleChecked = (index) => {
  checked.value = checked.value.includes(index)
    ? checked.value.filter((item) => item !== index)
    : [...checked.value, index]
}

const askStep = (step) => {
  emit('follow-up', `请详细解释「${props.card?.title || '这道题'}」中的这一步：${step.title}。`)
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

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.guide-step {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.2s ease;
}

.guide-step:hover {
  border-color: rgba(255, 255, 255, 0.14);
}

.guide-step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
}

.guide-step-check {
  flex: none;
}

.guide-step-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.guide-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(120, 190, 255, 0.14);
  color: rgba(160, 210, 255, 0.95);
  font-size: 11px;
}

.guide-step-title {
  flex: 1;
  min-width: 0;
}

.guide-step-chevron {
  flex: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
}

.guide-step-body {
  padding: 0 12px 12px 38px;
}

.guide-step-detail {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.7);
  white-space: pre-wrap;
}

.guide-step-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.guide-note {
  margin: 12px 0 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.36);
}

.step-fade-enter-active,
.step-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.step-fade-enter-from,
.step-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
