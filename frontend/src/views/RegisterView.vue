<template>
  <section class="register-shell">
    <div class="register-orb register-orb-left"></div>
    <div class="register-orb register-orb-right"></div>

    <div class="register-wrap">
      <div class="register-copy">
        <div class="copy-badge">Create Account</div>
        <h1>创建一个更纯粹的学习入口。</h1>
        <p>
          注册后即可使用智能问答、教师留言与学习记录管理。
        </p>
      </div>

      <a-card class="surface-card register-card">
        <template #title>
          <div class="register-card-title">
            <span>注册账号</span>
            <small>填写基础信息后即可开始使用</small>
          </div>
        </template>

        <a-form :model="form" layout="vertical" @submit.prevent="handleRegister">
          <a-form-item label="用户名">
            <a-input v-model:value="form.username" placeholder="请输入用户名" />
          </a-form-item>

          <a-form-item label="邮箱">
            <a-input v-model:value="form.email" placeholder="请输入邮箱地址" />
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password v-model:value="form.password" placeholder="请输入密码" />
          </a-form-item>

          <a-form-item label="确认密码">
            <a-input-password v-model:value="form.confirmPassword" placeholder="请再次输入密码" />
          </a-form-item>

          <a-form-item label="注册身份">
            <a-radio-group v-model:value="form.role">
              <a-radio-button value="student">学生端</a-radio-button>
              <a-radio-button value="teacher">教师端</a-radio-button>
            </a-radio-group>
          </a-form-item>

          <a-alert
            v-if="errorMessage"
            type="error"
            message="注册失败"
            :description="errorMessage"
            show-icon
            class="register-alert"
          />

          <a-alert
            v-if="successMessage"
            type="success"
            message="注册成功"
            :description="successMessage"
            show-icon
            class="register-alert"
          />

          <a-form-item class="register-submit">
            <a-button type="primary" html-type="submit" :loading="loading" block>
              {{ loading ? '注册中...' : '完成注册' }}
            </a-button>
          </a-form-item>

          <div class="register-footer">
            <span>已有账号？</span>
            <a href="#" @click.prevent="goToLogin">返回登录</a>
          </div>
        </a-form>
      </a-card>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { message } from 'ant-design-vue'

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
      router.push(userRole === 'teacher' ? '/teacher' : '/student')
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
    successMessage.value = ''
    return
  }

  errorMessage.value = ''
  successMessage.value = ''
  loading.value = true

  try {
    await axios.post('/api/register', {
      username: form.value.username,
      email: form.value.email,
      password: form.value.password,
      role: form.value.role
    })

    successMessage.value = '注册成功，正在跳转到登录页面...'
    message.success('注册成功')

    setTimeout(() => {
      router.push('/login')
    }, 1800)
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data.error || '注册失败，请稍后再试'
    } else {
      errorMessage.value = '网络异常，请确认后端服务已启动'
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
.register-shell {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  overflow: hidden;
}

.register-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.register-orb-left {
  top: 12%;
  left: 10%;
  width: 220px;
  height: 220px;
  background: rgba(255, 255, 255, 0.1);
  animation: regFloatA 12s ease-in-out infinite;
}

.register-orb-right {
  right: 10%;
  bottom: 10%;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.07);
  animation: regFloatB 14s ease-in-out infinite;
}

.register-wrap {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(400px, 500px);
  gap: 36px;
  align-items: center;
}

.register-copy {
  padding-right: 20px;
}

.copy-badge {
  display: inline-flex;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  animation: revealUp 0.82s ease both;
}

.register-copy h1 {
  margin: 26px 0 18px;
  font-size: clamp(34px, 5.6vw, 58px);
  line-height: 1.06;
  letter-spacing: -0.04em;
  animation: revealUp 0.94s ease both;
  animation-delay: 0.1s;
}

.register-copy p {
  max-width: 500px;
  margin: 0;
  color: rgba(255, 255, 255, 0.58);
  font-size: 16px;
  line-height: 1.9;
  animation: revealUp 1.04s ease both;
  animation-delay: 0.18s;
}

.register-card {
  animation: registerCardIn 0.95s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  animation-delay: 0.24s;
}

.register-card-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.register-card-title span {
  font-size: 24px;
}

.register-card-title small {
  color: rgba(255, 255, 255, 0.44);
}

.register-alert {
  margin-bottom: 18px;
}

.register-submit {
  margin-bottom: 14px;
}

.register-footer {
  text-align: center;
  color: rgba(255, 255, 255, 0.45);
}

.register-footer a {
  margin-left: 8px;
  color: rgba(255, 255, 255, 0.92);
  text-decoration: none;
}

@keyframes revealUp {
  from {
    opacity: 0;
    transform: translateY(22px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes registerCardIn {
  from {
    opacity: 0;
    transform: translateY(28px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes regFloatA {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(36px, -26px, 0) scale(1.08);
  }
}

@keyframes regFloatB {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-44px, 24px, 0) scale(1.1);
  }
}

@media (max-width: 980px) {
  .register-wrap {
    grid-template-columns: 1fr;
  }

  .register-copy {
    padding-right: 0;
  }
}

@media (max-width: 640px) {
  .register-shell {
    padding: 18px 14px 24px;
  }
}
</style>
