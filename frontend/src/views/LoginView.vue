<template>
  <div class="login-container">
    <a-card title="学习助手系统登录" class="login-card">
      <!-- 角色选择 -->
      <div class="role-selector">
        <a-radio-group v-model:value="role">
          <a-radio-button value="student">学生</a-radio-button>
          <a-radio-button value="teacher">老师</a-radio-button>
        </a-radio-group>
      </div>
      
      <!-- 登录表单 -->
      <a-form :model="form" @submit.prevent="handleLogin" layout="vertical">
        <a-form-item label="邮箱">
          <a-input v-model:value="form.email" placeholder="请输入邮箱地址" />
        </a-form-item>
        
        <a-form-item label="密码">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" />
        </a-form-item>
        
        <!-- 错误信息显示 -->
        <a-alert v-if="errorMessage" type="error" message="登录失败" :description="errorMessage" show-icon />
        
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block size="large">
            {{ loading ? '登录中...' : '登录' }}
          </a-button>
        </a-form-item>
        
        <a-form-item>
          <div class="register-link">
            还没有账号？<a href="#" @click="goToRegister">立即注册</a>
          </div>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { Card, Form, Input, Button, Radio, Alert, Space, message } from 'ant-design-vue'

const router = useRouter()
const form = ref({
  email: '',
  password: ''
})
const role = ref('student')
const errorMessage = ref('')
const loading = ref(false)

const checkAuth = async () => {
  try {
    const response = await axios.get('/api/check-auth')
    if (response.data.authenticated) {
      const userRole = response.data.user.role
      if (userRole === 'student') {
        router.push('/student')
      } else if (userRole === 'teacher') {
        router.push('/teacher')
      }
    }
  } catch (error) {
    console.error('检查登录状态失败:', error)
  }
}

onMounted(() => {
  checkAuth()
})

const handleLogin = async () => {
  errorMessage.value = ''
  loading.value = true
  
  try {
    const response = await axios.post('/api/login', {
      email: form.value.email,
      password: form.value.password
    })
    
    message.success('登录成功')
    
    if (role.value === 'student') {
      router.push('/student')
    } else {
      router.push('/teacher')
    }
    
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data.error || '登录失败'
    } else {
      errorMessage.value = '网络错误，请检查后端是否运行'
    }
    console.error('登录错误:', error)
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #0a0a0a;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  border-radius: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.login-card :deep(.ant-card-head) {
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.login-card :deep(.ant-card-head-title) {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}

.login-card :deep(.ant-card-body) {
  color: #e0e0e0;
}

.login-card :deep(.ant-form-item-label > label) {
  color: #a0a0a0;
  font-size: 14px;
}

.login-card :deep(.ant-input),
.login-card :deep(.ant-input-password .ant-input),
.login-card :deep(.ant-input-affix-wrapper) {
  background: #1a1a1a !important;
  border: 2px solid rgba(255, 255, 255, 0.3) !important;
  color: #fff !important;
  border-radius: 8px;
  font-size: 15px;
  -webkit-text-fill-color: #fff !important;
  -webkit-box-shadow: 0 0 0 1000px #1a1a1a inset !important;
  box-shadow: 0 0 0 1000px #1a1a1a inset !important;
}

.login-card :deep(.ant-input::placeholder),
.login-card :deep(.ant-input-password .ant-input::placeholder) {
  color: #666 !important;
}

.login-card :deep(.ant-input:focus),
.login-card :deep(.ant-input-focused),
.login-card :deep(.ant-input-affix-wrapper:focus),
.login-card :deep(.ant-input-affix-wrapper-focused) {
  background: #1a1a1a !important;
  border-color: #fff !important;
  box-shadow: 0 0 0 1000px #1a1a1a inset !important;
}

.login-card :deep(.ant-input-affix-wrapper:hover),
.login-card :deep(.ant-input:hover) {
  border-color: rgba(255, 255, 255, 0.5) !important;
}

.login-card :deep(.ant-input-password-icon) {
  color: #888;
}

.login-card :deep(.ant-input-password-icon:hover) {
  color: #fff;
}

.login-card :deep(.ant-btn-primary) {
  background: #fff;
  border: 2px solid #fff;
  color: #0a0a0a;
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  height: 44px;
}

.login-card :deep(.ant-btn-primary:hover),
.login-card :deep(.ant-btn-primary:focus) {
  background: #e0e0e0;
  border-color: #e0e0e0;
  color: #0a0a0a;
}

.login-card :deep(.ant-btn-primary:disabled) {
  background: #333;
  border-color: #333;
  color: #666;
}

.role-selector {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.role-selector :deep(.ant-radio-group) {
  display: flex;
  gap: 16px;
}

.role-selector :deep(.ant-radio-button-wrapper) {
  flex: 1;
  text-align: center;
  padding: 12px 24px;
  height: auto;
  background: transparent;
  border: 2px solid rgba(255, 255, 255, 0.3);
  color: #a0a0a0;
  border-radius: 8px;
}

.role-selector :deep(.ant-radio-button-wrapper:first-child),
.role-selector :deep(.ant-radio-button-wrapper:last-child) {
  border-radius: 8px;
}

.role-selector :deep(.ant-radio-button-wrapper:hover) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.5);
}

.role-selector :deep(.ant-radio-button-wrapper-checked) {
  background: #fff;
  border-color: #fff;
  color: #0a0a0a;
}

.login-card :deep(.ant-alert-error) {
  background: rgba(255, 77, 79, 0.15);
  border: 1px solid rgba(255, 77, 79, 0.4);
  margin-bottom: 16px;
}

.login-card :deep(.ant-alert-error .ant-alert-message) {
  color: #ff7875;
}

.login-card :deep(.ant-alert-error .ant-alert-description) {
  color: #ffa39e;
}

.login-card :deep(.ant-alert-error .ant-alert-icon) {
  color: #ff7875;
}

.register-link {
  text-align: center;
  margin-top: 16px;
  color: #888;
}

.register-link a {
  color: #fff;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.register-link a:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .login-container {
    padding: 16px;
  }
  
  .login-card {
    border-radius: 12px;
  }
}
</style>
