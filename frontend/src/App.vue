<template>
  <a-layout class="app-layout">
    <!-- 导航栏 -->
    <a-layout-header v-if="!isLoginPage" class="app-header">
      <div class="container">
        <a-space size="middle" style="width: 100%; display: flex; justify-content: space-between; align-items: center;">
          <a href="#" class="logo">
            学习助手
          </a>
          <a-space v-if="user" size="middle" class="user-info">
            <span>欢迎，{{ user.username }}</span>
            <a-button class="logout-btn" @click="handleLogout">
              退出
            </a-button>
          </a-space>
        </a-space>
      </div>
    </a-layout-header>
    
    <!-- 页面内容 -->
    <a-layout-content class="app-content">
      <div class="container">
        <router-view />
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { Layout, Menu, Button, Space } from 'ant-design-vue'

const { Header, Content, Footer, Sider } = Layout
const route = useRoute()
const router = useRouter()

const isLoginPage = computed(() => route.path === '/login' || route.path === '/register')
const user = ref(null)

const fetchUserInfo = async () => {
  try {
    const response = await axios.get('/api/check-auth')
    if (response.data.authenticated) {
      user.value = response.data.user
    } else {
      user.value = null
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    user.value = null
  }
}

onMounted(() => {
  fetchUserInfo()
})

// 监听路由变化，自动获取用户信息
watch(() => route.path, () => {
  if (!isLoginPage.value) {
    fetchUserInfo()
  }
}, { immediate: false })

const handleLogout = async () => {
  try {
    const response = await axios.post('/api/logout')
    if (response.status === 200 && response.data.message === 'Logout successful') {
      console.log('登出成功')
      user.value = null
      router.push('/login')
    } else {
      console.error('登出响应异常:', response.data)
      user.value = null
      router.push('/login')
    }
  } catch (error) {
    console.error('登出失败:', error)
    user.value = null
    router.push('/login')
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #0a0a0a;
  color: #e0e0e0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
  width: 100%;
}

.app-layout {
  min-height: 100vh;
  background: #0a0a0a;
}

.app-header {
  background: #0a0a0a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  height: 64px;
  line-height: 64px;
  padding: 0;
}

.logo {
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.user-info {
  color: #a0a0a0;
}

.user-info span {
  color: #a0a0a0;
  font-size: 14px;
}

.logout-btn {
  background: transparent;
  border: 2px solid rgba(255, 255, 255, 0.5);
  color: #fff;
  border-radius: 6px;
  padding: 6px 20px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #fff;
  color: #fff;
}

.app-content {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #0a0a0a;
}

/* Ant Design Vue 暗色主题覆盖 */
.ant-card {
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}

.ant-card-head {
  background: transparent;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

.ant-card-head-title {
  color: #fff;
}

.ant-card-body {
  color: #e0e0e0;
}

.ant-input,
.ant-input-password,
.ant-textarea {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  border-radius: 8px;
}

.ant-input:focus,
.ant-input-focused,
.ant-textarea:focus,
.ant-textarea-focused {
  background: #1a1a1a;
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
}

.ant-input::placeholder,
.ant-textarea::placeholder {
  color: #666;
}

.ant-btn-primary {
  background: #fff;
  border-color: #fff;
  color: #0a0a0a;
  border-radius: 8px;
  font-weight: 500;
}

.ant-btn-primary:hover,
.ant-btn-primary:focus {
  background: #e0e0e0;
  border-color: #e0e0e0;
  color: #0a0a0a;
}

.ant-btn-primary:disabled {
  background: #333;
  border-color: #333;
  color: #666;
}

.ant-btn {
  border-radius: 8px;
}

.ant-btn-dangerous {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #ff4d4f;
}

.ant-btn-dangerous:hover {
  background: rgba(255, 77, 79, 0.1);
  border-color: #ff4d4f;
}

.ant-form-item-label > label {
  color: #a0a0a0;
}

.ant-divider {
  border-color: rgba(255, 255, 255, 0.1);
}

.ant-divider-inner-text {
  color: #a0a0a0;
}

.ant-list-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.ant-list-item-meta-title {
  color: #fff !important;
}

.ant-list-item-meta-description {
  color: #888 !important;
}

.ant-list-item-meta-content {
  color: #e0e0e0;
}

.ant-list-item-meta-avatar {
  color: #888;
}

.ant-list-item-action {
  color: #888;
}

.ant-list-item-action > li {
  color: #888;
}

.ant-collapse {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.ant-collapse-item {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.ant-collapse-header {
  background: #141414 !important;
  color: #fff !important;
}

.ant-collapse-content {
  background: #0f0f0f !important;
  color: #e0e0e0 !important;
}

.ant-collapse-arrow {
  color: #888;
}

.ant-empty-description {
  color: #666;
}

.ant-alert {
  border-radius: 8px;
}

.ant-alert-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid rgba(82, 196, 26, 0.3);
}

.ant-alert-error {
  background: rgba(255, 77, 79, 0.1);
  border: 1px solid rgba(255, 77, 79, 0.3);
}

.ant-spin-text {
  color: #888;
}

.ant-statistic-title {
  color: #888 !important;
}

.ant-statistic-content {
  color: #fff !important;
}

.ant-statistic-content-value {
  color: #fff !important;
}

.ant-tag {
  border-radius: 4px;
}

.ant-radio-button-wrapper {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #a0a0a0;
}

.ant-radio-button-wrapper:hover {
  color: #fff;
}

.ant-radio-button-wrapper-checked {
  background: #fff;
  border-color: #fff;
  color: #0a0a0a;
}

.ant-radio-button-wrapper:first-child {
  border-radius: 8px 0 0 8px;
}

.ant-radio-button-wrapper:last-child {
  border-radius: 0 8px 8px 0;
}

.ant-page-header {
  color: #fff;
}

.ant-page-header-heading-title {
  color: #fff;
}

.ant-page-header-heading-sub-title {
  color: #888;
}

.ant-layout-header {
  background: #0a0a0a !important;
}

.ant-layout-content {
  background: #0a0a0a !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: 0 16px;
  }
  
  .logo {
    font-size: 18px;
  }
  
  .app-content {
    padding: 16px;
  }
}
</style>
