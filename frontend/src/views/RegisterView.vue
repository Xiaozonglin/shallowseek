<template>
  <div class="register-container">
    <a-card title="注册新账户" class="register-card">
      <a-form :model="form" @submit.prevent="handleRegister" layout="vertical">
        <a-form-item label="用户名" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="form.username" placeholder="请输入用户名" />
        </a-form-item>
        
        <a-form-item label="邮箱" :rules="[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效的邮箱地址' }]">
          <a-input v-model:value="form.email" placeholder="请输入邮箱地址" />
        </a-form-item>
        
        <a-form-item label="密码" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" />
        </a-form-item>
        
        <a-form-item label="确认密码" :rules="[{ required: true, message: '请再次输入密码' }]">
          <a-input-password v-model:value="form.confirmPassword" placeholder="请再次输入密码" />
        </a-form-item>
        
        <a-form-item label="注册身份" :rules="[{ required: true, message: '请选择角色' }]">
          <div class="role-selector">
            <a-radio-group v-model:value="form.role">
              <a-radio-button value="student">学生</a-radio-button>
              <a-radio-button value="teacher">老师</a-radio-button>
            </a-radio-group>
          </div>
        </a-form-item>
        
        <!-- 错误信息显示 -->
        <a-alert v-if="errorMessage" type="error" message="注册失败" :description="errorMessage" show-icon style="margin-bottom: 16px;" />
        
        <!-- 成功信息显示 -->
        <a-alert v-if="successMessage" type="success" message="注册成功" :description="successMessage" show-icon style="margin-bottom: 16px;" />
        
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block size="large">
            {{ loading ? '注册中...' : '注册' }}
          </a-button>
        </a-form-item>
        
        <a-form-item>
          <div class="login-link">
            已有账号？<a href="#" @click="goToLogin">立即登录</a>
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
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'student'
})
const errorMessage = ref('')
const successMessage = ref('')
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

const handleRegister = async () => {
  if (form.value.password !== form.value.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }
  
  errorMessage.value = ''
  successMessage.value = ''
  loading.value = true
  
  try {
    const response = await axios.post('/api/register', {
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
      role: form.value.role
    })
    
    successMessage.value = '注册成功！正在跳转到登录页面...'
    message.success('注册成功')
    
    setTimeout(() => {
      router.push('/login')
    }, 2000)
    
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data.error || '注册失败'
    } else {
      errorMessage.value = '网络错误，请检查后端是否运行'
    }
    console.error('注册错误:', error)
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #0a0a0a;
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 420px;
  border-radius: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.register-card :deep(.ant-card-head) {
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.register-card :deep(.ant-card-head-title) {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}

.register-card :deep(.ant-card-body) {
  color: #e0e0e0;
}

.register-card :deep(.ant-form-item-label > label) {
  color: #a0a0a0;
  font-size: 14px;
}

.register-card :deep(.ant-input),
.register-card :deep(.ant-input-password .ant-input),
.register-card :deep(.ant-input-affix-wrapper) {
  background: #1a1a1a !important;
  border: 2px solid rgba(255, 255, 255, 0.3) !important;
  color: #fff !important;
  border-radius: 8px;
  font-size: 15px;
  -webkit-text-fill-color: #fff !important;
  -webkit-box-shadow: 0 0 0 1000px #1a1a1a inset !important;
  box-shadow: 0 0 0 1000px #1a1a1a inset !important;
}

.register-card :deep(.ant-input::placeholder),
.register-card :deep(.ant-input-password .ant-input::placeholder) {
  color: #666 !important;
}

.register-card :deep(.ant-input:focus),
.register-card :deep(.ant-input-focused),
.register-card :deep(.ant-input-affix-wrapper:focus),
.register-card :deep(.ant-input-affix-wrapper-focused) {
  background: #1a1a1a !important;
  border-color: #fff !important;
  box-shadow: 0 0 0 1000px #1a1a1a inset !important;
}

.register-card :deep(.ant-input-affix-wrapper:hover),
.register-card :deep(.ant-input:hover) {
  border-color: rgba(255, 255, 255, 0.5) !important;
}

.register-card :deep(.ant-input-password-icon) {
  color: #888;
}

.register-card :deep(.ant-input-password-icon:hover) {
  color: #fff;
}

.register-card :deep(.ant-btn-primary) {
  background: #fff;
  border: 2px solid #fff;
  color: #0a0a0a;
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  height: 44px;
}

.register-card :deep(.ant-btn-primary:hover),
.register-card :deep(.ant-btn-primary:focus) {
  background: #e0e0e0;
  border-color: #e0e0e0;
  color: #0a0a0a;
}

.register-card :deep(.ant-btn-primary:disabled) {
  background: #333;
  border-color: #333;
  color: #666;
}

.role-selector {
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

.register-card :deep(.ant-alert-error) {
  background: rgba(255, 77, 79, 0.15);
  border: 1px solid rgba(255, 77, 79, 0.4);
}

.register-card :deep(.ant-alert-error .ant-alert-message) {
  color: #ff7875;
}

.register-card :deep(.ant-alert-error .ant-alert-description) {
  color: #ffa39e;
}

.register-card :deep(.ant-alert-error .ant-alert-icon) {
  color: #ff7875;
}

.register-card :deep(.ant-alert-success) {
  background: rgba(82, 196, 26, 0.15);
  border: 1px solid rgba(82, 196, 26, 0.4);
}

.register-card :deep(.ant-alert-success .ant-alert-message) {
  color: #73d13d;
}

.register-card :deep(.ant-alert-success .ant-alert-description) {
  color: #95de64;
}

.register-card :deep(.ant-alert-success .ant-alert-icon) {
  color: #73d13d;
}

.login-link {
  text-align: center;
  margin-top: 16px;
  color: #888;
}

.login-link a {
  color: #fff;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.login-link a:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .register-container {
    padding: 16px;
  }
  
  .register-card {
    border-radius: 12px;
  }
}
</style>
