<template>
  <section class="register-shell">
    <div class="moon-scene" aria-hidden="true">
      <div class="star-field"></div>
      <div class="moon-disc">
        <span class="moon-crater crater-one"></span>
        <span class="moon-crater crater-two"></span>
        <span class="moon-crater crater-three"></span>
        <span class="moon-crater crater-four"></span>
      </div>
      <div class="moon-horizon"></div>
    </div>
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
            <a-input
              ref="usernameInput"
              v-model:value="form.username"
              placeholder="请输入用户名"
              @pressEnter="focusEmail"
              @keydown.enter.prevent="focusEmail"
            />
          </a-form-item>

          <a-form-item label="邮箱">
            <a-input
              ref="emailInput"
              v-model:value="form.email"
              placeholder="请输入邮箱地址"
              @pressEnter="focusPassword"
              @keydown.enter.prevent="focusPassword"
            />
          </a-form-item>

          <a-form-item label="密码">
            <a-input-password
              ref="passwordInput"
              v-model:value="form.password"
              placeholder="请输入密码"
              @pressEnter="focusConfirmPassword"
              @keydown.enter.prevent="focusConfirmPassword"
            />
          </a-form-item>

          <a-form-item label="确认密码">
            <a-input-password
              ref="confirmPasswordInput"
              v-model:value="form.confirmPassword"
              placeholder="请再次输入密码"
              @pressEnter="submitRegisterFromEnter"
              @keydown.enter.prevent="submitRegisterFromEnter"
            />
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
const usernameInput = ref(null)
const emailInput = ref(null)
const passwordInput = ref(null)
const confirmPasswordInput = ref(null)

const focusInput = (targetRef) => {
  const target = targetRef.value
  target?.focus?.()
  const input = target?.$el?.querySelector?.('input')
  input?.focus?.()
}

const focusEmail = (event) => {
  event?.preventDefault?.()
  focusInput(emailInput)
}

const focusPassword = (event) => {
  event?.preventDefault?.()
  focusInput(passwordInput)
}

const focusConfirmPassword = (event) => {
  event?.preventDefault?.()
  focusInput(confirmPasswordInput)
}

const submitRegisterFromEnter = (event) => {
  event?.preventDefault?.()
  handleRegister()
}

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
  if (loading.value) return

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

.moon-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  background:
    radial-gradient(circle at 20% 16%, rgba(255, 255, 255, 0.08), transparent 20%),
    radial-gradient(circle at 82% 82%, rgba(255, 255, 255, 0.08), transparent 22%),
    linear-gradient(135deg, #050505 0%, #101010 52%, #030303 100%);
}

.star-field,
.star-field::before,
.star-field::after {
  position: absolute;
  inset: 0;
  content: "";
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.72) 0 1px, transparent 1.5px),
    radial-gradient(circle, rgba(255, 255, 255, 0.5) 0 1px, transparent 1.6px);
  background-position: 10% 18%, 70% 30%;
  background-size: 180px 160px, 260px 220px;
  opacity: 0.26;
}

.star-field::before {
  transform: translate3d(38px, -24px, 0);
  opacity: 0.18;
  animation: starsDrift 18s linear infinite;
}

.star-field::after {
  transform: translate3d(-80px, 60px, 0);
  opacity: 0.16;
  animation: starsDrift 24s linear infinite reverse;
}

.moon-disc {
  position: absolute;
  right: clamp(-170px, -5vw, -40px);
  top: clamp(70px, 13vh, 140px);
  width: clamp(520px, 43vw, 820px);
  aspect-ratio: 1;
  border-radius: 50%;
  opacity: 0.72;
  filter: saturate(0) contrast(1.12);
  background:
    radial-gradient(circle at 35% 24%, rgba(255, 255, 255, 0.95), rgba(215, 215, 215, 0.72) 19%, transparent 20%),
    radial-gradient(circle at 62% 36%, rgba(30, 30, 30, 0.52), transparent 12%),
    radial-gradient(circle at 42% 56%, rgba(20, 20, 20, 0.56), transparent 9%),
    radial-gradient(circle at 72% 62%, rgba(255, 255, 255, 0.32), transparent 11%),
    radial-gradient(circle at 50% 50%, #dedede 0%, #a6a6a6 36%, #575757 63%, #151515 82%, transparent 83%);
  box-shadow:
    0 0 70px rgba(255, 255, 255, 0.2),
    inset -70px -90px 120px rgba(0, 0, 0, 0.86),
    inset 42px 34px 70px rgba(255, 255, 255, 0.28);
  animation: moonFloat 16s ease-in-out infinite;
}

.moon-disc::before {
  position: absolute;
  inset: 10%;
  content: "";
  border-radius: inherit;
  background:
    radial-gradient(circle at 22% 42%, rgba(10, 10, 10, 0.45) 0 3%, transparent 3.6%),
    radial-gradient(circle at 34% 72%, rgba(20, 20, 20, 0.45) 0 4%, transparent 4.6%),
    radial-gradient(circle at 58% 25%, rgba(20, 20, 20, 0.34) 0 2.5%, transparent 3%),
    radial-gradient(circle at 72% 46%, rgba(255, 255, 255, 0.18) 0 2%, transparent 2.6%);
  opacity: 0.82;
}

.moon-crater {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.24), rgba(0, 0, 0, 0.52) 58%, rgba(255, 255, 255, 0.1));
  box-shadow: inset 9px 8px 16px rgba(0, 0, 0, 0.44);
}

.crater-one {
  left: 21%;
  top: 36%;
  width: 14%;
  height: 10%;
}

.crater-two {
  left: 55%;
  top: 52%;
  width: 18%;
  height: 13%;
}

.crater-three {
  left: 42%;
  top: 22%;
  width: 9%;
  height: 7%;
}

.crater-four {
  left: 28%;
  top: 64%;
  width: 8%;
  height: 8%;
}

.moon-horizon {
  position: absolute;
  left: -8%;
  right: -8%;
  bottom: -34%;
  height: 48%;
  border-radius: 50% 50% 0 0;
  background:
    radial-gradient(ellipse at 34% 8%, rgba(255, 255, 255, 0.2), transparent 24%),
    linear-gradient(180deg, rgba(155, 155, 155, 0.22), rgba(5, 5, 5, 0.96) 52%);
  filter: blur(1px);
  opacity: 0.5;
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
  background: rgba(255, 255, 255, 0.08);
  animation: regFloatA 12s ease-in-out infinite;
}

.register-orb-right {
  right: 10%;
  bottom: 10%;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.06);
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
  background: rgba(14, 14, 14, 0.48);
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(24px);
}

.register-card :deep(.ant-card-head),
.register-card :deep(.ant-card-body) {
  background: transparent;
}

.register-card :deep(.ant-card-head) {
  border-bottom-color: rgba(255, 255, 255, 0.09);
}

.register-card :deep(.ant-input),
.register-card :deep(.ant-input-password) {
  background: rgba(255, 255, 255, 0.055);
  border-color: rgba(255, 255, 255, 0.13);
  box-shadow: none;
}

.register-card :deep(.ant-input:focus),
.register-card :deep(.ant-input-focused),
.register-card :deep(.ant-input-password-focused),
.register-card :deep(.ant-input-password:focus-within) {
  border-color: rgba(255, 255, 255, 0.42);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08);
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

@keyframes moonFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(-4deg) scale(1);
  }
  50% {
    transform: translate3d(-18px, 12px, 0) rotate(-2deg) scale(1.018);
  }
}

@keyframes starsDrift {
  from {
    background-position: 10% 18%, 70% 30%;
  }
  to {
    background-position: 16% 21%, 64% 34%;
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
