<template>
  <aside class="student-sidebar" :class="{ 'is-open': open }">
    <div class="sidebar-head">
      <a-button class="new-question-btn" block @click="$emit('new-question')">
        <template #icon><plus-outlined /></template>
        新的提问
      </a-button>
    </div>

    <nav class="sidebar-nav">
      <button
        type="button"
        class="nav-item"
        :class="{ active: panel === 'workspace' }"
        @click="$emit('open-workspace')"
      >
        <message-outlined />
        <span>提问工作区</span>
      </button>
    </nav>

    <div class="sidebar-scroll">
      <section class="history-section">
        <button type="button" class="history-head" @click="toggleHistory">
          <span class="history-label">提问历史</span>
          <span class="history-count">{{ history.length }}</span>
          <down-outlined class="history-chevron" :class="{ collapsed: historyCollapsed }" />
        </button>

        <div v-show="!historyCollapsed" class="history-list">
          <p v-if="history.length === 0" class="history-empty">还没有历史记录</p>

          <div
            v-for="item in history"
            :key="item.id"
            class="history-item"
            :class="{ active: item.id === activeId }"
            @click="handleSelect(item)"
          >
            <a-input
              v-if="editingId === item.id"
              v-model:value="draftTitle"
              class="rename-input"
              size="small"
              :maxlength="24"
              @click.stop
              @keyup.enter.stop="commitRename"
              @keyup.esc.stop="cancelRename"
              @blur="commitRename"
            />
            <template v-else>
              <span class="history-title" :title="displayTitle(item)">{{ displayTitle(item) }}</span>
              <span v-if="item.shared" class="history-shared">已提交</span>
              <span v-if="item.authoritative_answer" class="history-replied">已回复</span>
              <span class="history-actions">
                <button
                  type="button"
                  class="item-action"
                  title="重命名标题"
                  @click.stop="startRename(item)"
                >
                  <edit-outlined />
                </button>
                <a-popconfirm
                  title="确定删除这条提问记录吗？"
                  ok-text="删除"
                  cancel-text="取消"
                  @confirm="$emit('delete', item)"
                >
                  <button type="button" class="item-action item-action-danger" title="删除记录" @click.stop>
                    <delete-outlined />
                  </button>
                </a-popconfirm>
              </span>
            </template>
          </div>
        </div>
      </section>
    </div>

    <div class="sidebar-foot">
      <button
        type="button"
        class="plugin-entry"
        :class="{ active: panel === 'plugin' }"
        @click="$emit('open-plugins')"
      >
        <span class="plugin-icon"><appstore-outlined /></span>
        <span class="plugin-text">
          <strong>学生插件</strong>
        </span>
        <span class="plugin-arrow"><right-outlined /></span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import {
  AppstoreOutlined,
  DeleteOutlined,
  DownOutlined,
  EditOutlined,
  MessageOutlined,
  PlusOutlined,
  RightOutlined
} from '@ant-design/icons-vue'

defineProps({
  history: { type: Array, default: () => [] },
  activeId: { type: [Number, String], default: null },
  panel: { type: String, default: 'workspace' },
  open: { type: Boolean, default: false }
})

const emit = defineEmits(['new-question', 'open-workspace', 'open-plugins', 'select', 'rename', 'delete'])

const COLLAPSE_KEY = 'student-history-collapsed'
const historyCollapsed = ref(false)
const editingId = ref(null)
const draftTitle = ref('')

onMounted(() => {
  try {
    historyCollapsed.value = window.localStorage.getItem(COLLAPSE_KEY) === '1'
  } catch {
    historyCollapsed.value = false
  }
})

const toggleHistory = () => {
  historyCollapsed.value = !historyCollapsed.value
  try {
    window.localStorage.setItem(COLLAPSE_KEY, historyCollapsed.value ? '1' : '0')
  } catch {
    // localStorage 不可用时忽略
  }
}

const fallbackTitle = (item) => {
  const raw = (item.question || '')
    .replace(/^\[\s*(图像|文件)\s*\]\s*/, '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!raw) return '未命名提问'
  return raw.length > 22 ? `${raw.slice(0, 22)}…` : raw
}

const displayTitle = (item) => (item.title || '').trim() || fallbackTitle(item)

const handleSelect = (item) => {
  if (editingId.value === item.id) return
  emit('select', item)
}

const startRename = async (item) => {
  editingId.value = item.id
  draftTitle.value = displayTitle(item)
  await nextTick()
  // a-input 没有包裹层时类名直接落在 input 上，两种结构都兼容
  const root = document.querySelector('.history-item .rename-input')
  const input = root?.tagName === 'INPUT' ? root : root?.querySelector('input')
  input?.focus()
  input?.select()
}

const cancelRename = () => {
  editingId.value = null
  draftTitle.value = ''
}

const commitRename = () => {
  if (editingId.value === null) return
  const id = editingId.value
  const title = draftTitle.value.trim()
  editingId.value = null
  draftTitle.value = ''
  if (!title) return
  emit('rename', id, title)
}
</script>

<style scoped>
.student-sidebar {
  position: fixed;
  top: 76px;
  bottom: 0;
  left: 0;
  z-index: 18;
  display: flex;
  flex-direction: column;
  width: 280px;
  padding: 18px 14px 14px;
  gap: 14px;
  background: linear-gradient(180deg, rgba(13, 13, 14, 0.97), rgba(6, 6, 7, 0.98));
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
}

.sidebar-head,
.sidebar-nav,
.sidebar-foot {
  flex: none;
}

.new-question-btn.ant-btn {
  height: 42px;
  border-radius: 12px !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  background: rgba(255, 255, 255, 0.06) !important;
  color: rgba(255, 255, 255, 0.92) !important;
  font-weight: 600;
}

.new-question-btn.ant-btn:hover,
.new-question-btn.ant-btn:focus {
  background: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  transform: none !important;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 255, 255, 0.9);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.09);
  color: #ffffff;
}

.sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 0 -6px;
  padding: 0 6px 8px;
}

.sidebar-scroll::-webkit-scrollbar {
  width: 6px;
}

.sidebar-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.history-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px 6px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.42);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  cursor: pointer;
}

.history-head:hover {
  color: rgba(255, 255, 255, 0.62);
}

.history-label {
  flex: 1;
  text-align: left;
}

.history-count {
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  font-size: 10px;
  letter-spacing: 0;
  line-height: 18px;
}

.history-chevron {
  font-size: 10px;
  transition: transform 0.2s ease;
}

.history-chevron.collapsed {
  transform: rotate(-90deg);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 2px;
}

.history-empty {
  margin: 6px 10px 10px;
  color: rgba(255, 255, 255, 0.34);
  font-size: 12px;
  line-height: 1.6;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 34px;
  padding: 6px 8px 6px 12px;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 255, 255, 0.9);
}

.history-item.active {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.history-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.5;
}

.history-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.history-item:hover .history-actions,
.history-item:focus-within .history-actions,
.history-item.active .history-actions {
  opacity: 1;
}

.item-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.item-action:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.item-action-danger:hover {
  color: #ff8b8b;
}

.rename-input.ant-input {
  flex: 1;
  height: 28px;
  border-radius: 8px !important;
  font-size: 13px;
}

.sidebar-foot {
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.plugin-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
  color: rgba(255, 255, 255, 0.8);
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.plugin-entry:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.16);
  transform: translateY(-1px);
}

.plugin-entry.active {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.22);
}

.plugin-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.06));
  color: #0b0b0b;
  font-size: 15px;
}

.plugin-text {
  flex: 1;
  min-width: 0;
}

.plugin-text strong {
  font-size: 13px;
  font-weight: 600;
}

.plugin-arrow {
  color: rgba(255, 255, 255, 0.35);
  font-size: 11px;
}

@media (max-width: 1024px) {
  .student-sidebar {
    z-index: 30;
    top: 76px;
    transform: translateX(-100%);
    transition: transform 0.28s ease;
    box-shadow: 24px 0 60px rgba(0, 0, 0, 0.45);
  }

  .student-sidebar.is-open {
    transform: translateX(0);
  }
}

@media (max-width: 768px) {
  .student-sidebar {
    top: 72px;
    width: min(300px, 86vw);
  }
}
.history-shared {
  flex: none;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1.6;
  color: rgba(140, 220, 160, 0.9);
  border: 1px solid rgba(140, 220, 160, 0.35);
  background: rgba(140, 220, 160, 0.08);
}
.history-replied {
  flex: none;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1.6;
  color: rgba(160, 210, 255, 0.9);
  border: 1px solid rgba(120, 190, 255, 0.35);
  background: rgba(120, 190, 255, 0.08);
}
</style>
