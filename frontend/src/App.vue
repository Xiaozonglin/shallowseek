<template>
  <a-layout class="app-layout">
    <a-layout-header v-if="!isAuthPage" class="app-header">
      <div class="container header-inner">
        <router-link to="/" class="brand-mark">
          <span class="brand-dot"></span>
          <div>
            <div class="brand-title">ShallowSeek</div>
            <div class="brand-subtitle">AI Learning Console</div>
          </div>
        </router-link>

        <a-space v-if="user" size="middle" class="user-panel">
          <div class="user-badge">
            <span class="user-label">当前账号</span>
            <span class="user-name">{{ user.username }}</span>
          </div>
          <a-button class="ghost-button" @click="handleLogout">
            退出登录
          </a-button>
        </a-space>
      </div>
    </a-layout-header>

    <a-layout-content class="app-content" :class="{ 'app-content-auth': isAuthPage }">
      <div class="ambient ambient-left"></div>
      <div class="ambient ambient-right"></div>
      <div class="ambient ambient-center"></div>
      <div class="noise-grid"></div>

      <router-view v-slot="{ Component }">
        <transition name="route-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const user = ref(null)

const isAuthPage = computed(() => route.path === '/login' || route.path === '/register')

const fetchUserInfo = async () => {
  try {
    const response = await axios.get('/api/check-auth')
    user.value = response.data.authenticated ? response.data.user : null
  } catch (error) {
    console.error('获取用户信息失败:', error)
    user.value = null
  }
}

onMounted(() => {
  fetchUserInfo()
})

watch(
  () => route.path,
  () => {
    if (!isAuthPage.value) {
      fetchUserInfo()
    }
  }
)

const handleLogout = async () => {
  try {
    await axios.post('/api/logout')
  } catch (error) {
    console.error('退出登录失败:', error)
  } finally {
    user.value = null
    router.push('/login')
  }
}
</script>

<style>
:root {
  color-scheme: dark;
  --bg-primary: #050505;
  --bg-secondary: #0c0c0d;
  --bg-elevated: rgba(19, 19, 20, 0.84);
  --bg-soft: rgba(255, 255, 255, 0.04);
  --border-strong: rgba(255, 255, 255, 0.12);
  --border-soft: rgba(255, 255, 255, 0.08);
  --text-primary: rgba(255, 255, 255, 0.96);
  --text-secondary: rgba(255, 255, 255, 0.66);
  --text-tertiary: rgba(255, 255, 255, 0.42);
  --accent: #f5f5f5;
  --shadow-lg: 0 24px 80px rgba(0, 0, 0, 0.45);
  --shadow-md: 0 14px 40px rgba(0, 0, 0, 0.3);
  --radius-xl: 28px;
  --radius-lg: 20px;
  --radius-md: 14px;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.08), transparent 28%),
    radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.06), transparent 22%),
    linear-gradient(180deg, #090909 0%, #050505 55%, #040404 100%);
  color: var(--text-primary);
}

a {
  color: inherit;
}

.container {
  width: min(1280px, calc(100% - 48px));
  margin: 0 auto;
}

.app-layout {
  min-height: 100vh;
  background: transparent;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  height: 76px;
  line-height: normal;
  padding: 0;
  background: rgba(5, 5, 5, 0.76) !important;
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border-soft);
  animation: headerIn 0.8s ease-out;
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
}

.brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #ffffff 0%, rgba(255, 255, 255, 0.4) 100%);
  box-shadow: 0 0 28px rgba(255, 255, 255, 0.5);
  animation: pulseGlow 4.2s ease-in-out infinite;
}

.brand-title {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.user-panel {
  display: flex;
  align-items: center;
}

.user-badge {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-soft);
  animation: fadeUp 0.8s ease both;
}

.user-label {
  margin-right: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.user-name {
  font-size: 14px;
  color: var(--text-primary);
}

.ghost-button.ant-btn {
  height: 40px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: var(--text-primary);
  transition: transform 0.28s ease, border-color 0.28s ease, background 0.28s ease;
}

.ghost-button.ant-btn:hover,
.ghost-button.ant-btn:focus {
  border-color: rgba(255, 255, 255, 0.26);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.app-content {
  position: relative;
  min-height: calc(100vh - 76px);
  padding: 32px 0 40px;
  overflow: hidden;
}

.app-content-auth {
  min-height: 100vh;
  padding: 0;
}

.ambient {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.28;
}

.ambient-left {
  top: 8%;
  left: -120px;
  width: 340px;
  height: 340px;
  background: rgba(255, 255, 255, 0.12);
  animation: driftA 16s ease-in-out infinite;
}

.ambient-right {
  right: -120px;
  bottom: 4%;
  width: 430px;
  height: 430px;
  background: rgba(255, 255, 255, 0.08);
  animation: driftB 18s ease-in-out infinite;
}

.ambient-center {
  top: 24%;
  left: 42%;
  width: 280px;
  height: 280px;
  background: rgba(255, 255, 255, 0.06);
  animation: driftC 15s ease-in-out infinite;
}

.noise-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.7), transparent 86%);
  opacity: 0.18;
  animation: gridShift 24s linear infinite;
}

.surface-card.ant-card {
  position: relative;
  overflow: hidden;
  background: var(--bg-elevated);
  border: 1px solid var(--border-soft);
  box-shadow: var(--shadow-md);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(18px);
  transition: transform 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
}

.surface-card.ant-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    120deg,
    transparent 10%,
    rgba(255, 255, 255, 0.06) 30%,
    transparent 55%
  );
  transform: translateX(-120%);
  animation: sheen 9s ease-in-out infinite;
  pointer-events: none;
}

.surface-card.ant-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.14);
  box-shadow: var(--shadow-lg);
}

.surface-card .ant-card-head {
  border-bottom: 1px solid var(--border-soft);
  min-height: 68px;
}

.surface-card .ant-card-head-title {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.surface-card .ant-card-body {
  color: var(--text-secondary);
}

.ant-input,
.ant-input-affix-wrapper,
.ant-input-password,
.ant-input-textarea textarea,
.ant-select-selector {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: var(--text-primary) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
  transition: border-color 0.25s ease, transform 0.25s ease, background 0.25s ease !important;
}

.ant-input::placeholder,
.ant-input-textarea textarea::placeholder {
  color: var(--text-tertiary) !important;
}

.ant-input-affix-wrapper:hover,
.ant-input:hover,
.ant-input-textarea textarea:hover,
.ant-select-selector:hover {
  border-color: rgba(255, 255, 255, 0.18) !important;
}

.ant-input-affix-wrapper-focused,
.ant-input-focused,
.ant-input-textarea textarea:focus,
.ant-select-focused .ant-select-selector {
  border-color: rgba(255, 255, 255, 0.28) !important;
  transform: translateY(-1px);
}

.ant-form-item-label > label,
.ant-radio-wrapper,
.ant-upload {
  color: var(--text-secondary) !important;
}

.ant-btn-primary {
  height: 44px;
  border: none !important;
  border-radius: 999px !important;
  background: linear-gradient(180deg, #ffffff 0%, #d9d9d9 100%) !important;
  color: #050505 !important;
  font-weight: 600;
  box-shadow: 0 10px 30px rgba(255, 255, 255, 0.15);
  transition: transform 0.28s ease, box-shadow 0.28s ease, filter 0.28s ease !important;
}

.ant-btn-primary:hover,
.ant-btn-primary:focus {
  filter: brightness(1.03);
  transform: translateY(-1px);
  box-shadow: 0 14px 36px rgba(255, 255, 255, 0.18);
}

.ant-btn-default,
.ant-btn-dashed {
  height: 42px;
  border-radius: 999px !important;
  background: rgba(255, 255, 255, 0.03) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  color: var(--text-primary) !important;
  transition: transform 0.28s ease, border-color 0.28s ease, background 0.28s ease !important;
}

.ant-btn-default:hover,
.ant-btn-dashed:hover {
  border-color: rgba(255, 255, 255, 0.22) !important;
  background: rgba(255, 255, 255, 0.07) !important;
  transform: translateY(-1px);
}

.ant-radio-group {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.ant-radio-button-wrapper {
  height: 44px;
  line-height: 42px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 999px !important;
  color: var(--text-secondary) !important;
  transition: transform 0.28s ease, background 0.28s ease, color 0.28s ease !important;
}

.ant-radio-button-wrapper::before {
  display: none !important;
}

.ant-radio-button-wrapper:hover {
  transform: translateY(-1px);
}

.ant-radio-button-wrapper-checked {
  background: rgba(255, 255, 255, 0.92) !important;
  color: #050505 !important;
  border-color: transparent !important;
}

.ant-divider {
  border-color: var(--border-soft);
}

.ant-divider-inner-text {
  color: var(--text-secondary);
}

.ant-alert {
  border-radius: 14px;
  border: 1px solid var(--border-soft);
}

.ant-alert-success {
  background: rgba(109, 211, 160, 0.08);
}

.ant-alert-error {
  background: rgba(255, 139, 139, 0.08);
}

.ant-list-item {
  border-block-end: 1px solid var(--border-soft) !important;
}

.ant-empty-description,
.ant-statistic-title,
.ant-spin-text,
.ant-form-item-explain-error {
  color: var(--text-tertiary) !important;
}

.ant-statistic-content,
.ant-statistic-content-value,
.ant-page-header-heading-title {
  color: var(--text-primary) !important;
}

.ant-tag {
  border-radius: 999px;
  border: 1px solid transparent;
}

.ant-collapse {
  background: transparent !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-md) !important;
}

.ant-collapse > .ant-collapse-item {
  border-bottom: 1px solid var(--border-soft) !important;
}

.ant-collapse > .ant-collapse-item:last-child {
  border-bottom: none !important;
}

.ant-collapse-header {
  color: var(--text-primary) !important;
  background: rgba(255, 255, 255, 0.02) !important;
  transition: background 0.25s ease !important;
}

.ant-collapse-header:hover {
  background: rgba(255, 255, 255, 0.04) !important;
}

.ant-collapse-content {
  background: rgba(255, 255, 255, 0.015) !important;
  border-top: 1px solid var(--border-soft) !important;
}

.route-fade-enter-active,
.route-fade-leave-active {
  transition: opacity 0.36s ease, transform 0.36s ease, filter 0.36s ease;
}

.route-fade-enter-from,
.route-fade-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.995);
  filter: blur(8px);
}

@keyframes headerIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulseGlow {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 0 28px rgba(255, 255, 255, 0.45);
  }
  50% {
    transform: scale(1.12);
    box-shadow: 0 0 40px rgba(255, 255, 255, 0.62);
  }
}

@keyframes sheen {
  0%,
  72%,
  100% {
    transform: translateX(-120%);
  }
  84% {
    transform: translateX(120%);
  }
}

@keyframes driftA {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(48px, -28px, 0) scale(1.08);
  }
}

@keyframes driftB {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-52px, 36px, 0) scale(1.1);
  }
}

@keyframes driftC {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(20px, 30px, 0) scale(1.16);
  }
}

@keyframes gridShift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(32px, 24px, 0);
  }
}

@media (max-width: 768px) {
  .container {
    width: min(100%, calc(100% - 28px));
  }

  .app-header {
    height: 72px;
  }

  .header-inner {
    gap: 12px;
  }

  .brand-subtitle,
  .user-label {
    display: none;
  }

  .app-content {
    padding-top: 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
}
</style>
