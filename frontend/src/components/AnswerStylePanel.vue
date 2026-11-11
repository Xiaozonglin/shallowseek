<template>
  <div class="answer-style">
    <button type="button" class="style-trigger" @click="open = !open">
      <span class="style-trigger-label">回答效果</span>
      <span class="style-trigger-value">
        {{ mode === 'fast' ? '直接回答' : activeTemplate.label }} · {{ activeStyle.label }}
      </span>
      <down-outlined class="style-trigger-arrow" :class="{ open }" />
    </button>

    <transition name="style-fade">
      <div v-if="open" class="style-panel">
        <section class="style-section">
          <header class="style-section-head">
            <span>回答模板</span>
            <small v-if="mode === 'fast'" class="style-fast-hint">快答模式直接回答，不套用模板</small>
            <small v-else>可选，默认自由回答</small>
          </header>
          <div class="style-options">
            <button
              v-for="item in templates"
              :key="item.id"
              type="button"
              class="style-option"
              :class="{ active: item.id === template, disabled: mode === 'fast' }"
              :disabled="mode === 'fast'"
              @click="$emit('update:template', item.id)"
            >
              <span class="option-label">{{ item.label }}</span>
              <span class="option-desc">{{ item.description }}</span>
            </button>
          </div>
        </section>

        <section class="style-section">
          <header class="style-section-head">
            <span>交流方式</span>
            <small>决定这一轮说多少、是否引导你回答</small>
          </header>
          <div class="style-options style-options-row">
            <button
              v-for="item in styles"
              :key="item.id"
              type="button"
              class="style-option"
              :class="{ active: item.id === style }"
              @click="$emit('update:style', item.id)"
            >
              <span class="option-label">{{ item.label }}</span>
              <span class="option-desc">{{ item.description }}</span>
            </button>
          </div>
        </section>

        <footer class="style-panel-foot">
          <span>选择随本次提问生效，会记住你的偏好</span>
          <a-button type="link" size="small" @click="open = false">收起</a-button>
        </footer>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { DownOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  template: { type: String, default: 'free' },
  style: { type: String, default: 'long_form' },
  mode: { type: String, default: 'deep' },
  templates: { type: Array, default: () => [] },
  styles: { type: Array, default: () => [] }
})
defineEmits(['update:template', 'update:style'])

const open = ref(false)

const activeTemplate = computed(
  () => props.templates.find((item) => item.id === props.template) || props.templates[0] || { label: '自由回答' }
)
const activeStyle = computed(
  () => props.styles.find((item) => item.id === props.style) || props.styles[0] || { label: '长对话' }
)
</script>

<style scoped>
.answer-style {
  margin-bottom: 14px;
}

.style-trigger {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.style-trigger:hover {
  border-color: rgba(120, 190, 255, 0.45);
  background: rgba(120, 190, 255, 0.06);
}

.style-trigger-label {
  color: rgba(255, 255, 255, 0.42);
}

.style-trigger-value {
  color: rgba(160, 210, 255, 0.95);
}

.style-trigger-arrow {
  font-size: 10px;
  transition: transform 0.2s ease;
}

.style-trigger-arrow.open {
  transform: rotate(180deg);
}

.style-panel {
  margin-top: 12px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.035);
}

.style-section + .style-section {
  margin-top: 16px;
}

.style-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 13px;
  font-weight: 600;
}

.style-section-head small {
  font-size: 11px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.38);
}

.style-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.style-options-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.style-option {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  text-align: left;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.02);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.style-option:hover {
  border-color: rgba(255, 255, 255, 0.22);
}

.style-option.active {
  border-color: rgba(120, 190, 255, 0.6);
  background: rgba(120, 190, 255, 0.1);
}

.option-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.option-desc {
  font-size: 11px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.48);
}

.style-panel-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  color: rgba(255, 255, 255, 0.36);
  font-size: 11px;
}

.style-fade-enter-active,
.style-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.style-fade-enter-from,
.style-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 640px) {
  .style-options,
  .style-options-row {
    grid-template-columns: 1fr;
  }
}
.style-option.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.style-fast-hint {
  color: rgba(255, 200, 120, 0.75) !important;
}
</style>
