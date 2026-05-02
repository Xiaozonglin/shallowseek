<template>
  <section class="auth-shell">
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
    <div class="auth-orb orb-one"></div>
    <div class="auth-orb orb-two"></div>

    <div class="auth-grid">
      <div class="auth-copy">
        <div class="eyebrow">XDwe</div>
        <h1>为每一个XDUer打造的专属智能助手。</h1>
        <p>
          以多模态辅助的Agent为核心。
        </p>

        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-index"></span>
            <div>
              <strong>多模态提问</strong>
              <p>支持文本与图像联合分析，响应更自然。</p>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-index"></span>
            <div>
              <strong>学生与教师双端</strong>
              <p>学习、反馈、答疑在同一系统中闭环完成。</p>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-index"></span>
            <div>
              <strong>自动化学情统计</strong>
              <p>减轻教师教学负担。</p>
            </div>
          </div>
        </div>
      </div>

      <a-card class="surface-card auth-card">
        <template #title>
          <div class="auth-card-title">
            <span>欢迎回来</span>
            <small>登录你的学习空间</small>
          </div>
        </template>

        <div class="auth-role">
          <span class="section-label">身份选择</span>
          <a-radio-group v-model:value="role">
            <a-radio-button value="student">学生端</a-radio-button>
            <a-radio-button value="teacher">教师端</a-radio-button>
          </a-radio-group>
        </div>

        <a-form :model="form" layout="vertical" @submit.prevent="handleLogin">
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
              placeholder="请输入登录密码"
              @pressEnter="submitLoginFromEnter"
              @keydown.enter.prevent="submitLoginFromEnter"
            />
          </a-form-item>

          <a-alert
            v-if="errorMessage"
            type="error"
            message="登录失败"
            :description="errorMessage"
            show-icon
            class="auth-alert"
          />

          <a-form-item class="auth-submit">
            <a-button type="primary" html-type="submit" :loading="loading" block>
              {{ loading ? '登录中...' : '进入系统' }}
            </a-button>
          </a-form-item>

          <div class="auth-footer">
            <span>还没有账号？</span>
            <a href="#" @click.prevent="goToRegister">立即注册</a>
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
  email: '',
  password: ''
})
const role = ref('student')
const errorMessage = ref('')
const loading = ref(false)
const emailInput = ref(null)
const passwordInput = ref(null)

const focusInput = (targetRef) => {
  const target = targetRef.value
  target?.focus?.()
  const input = target?.$el?.querySelector?.('input')
  input?.focus?.()
}

const focusPassword = (event) => {
  event?.preventDefault?.()
  focusInput(passwordInput)
}

const submitLoginFromEnter = (event) => {
  event?.preventDefault?.()
  handleLogin()
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

const handleLogin = async () => {
  if (loading.value) return

  errorMessage.value = ''
  loading.value = true

  try {
    await axios.post('/api/login', {
      email: form.value.email,
      password: form.value.password
    })

    message.success('登录成功')
    router.push(role.value === 'teacher' ? '/teacher' : '/student')
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data.error || '登录失败，请稍后重试'
    } else {
      errorMessage.value = '网络异常，请确认后端服务已启动'
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
.auth-shell {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 24px;
  overflow: hidden;
}

.moon-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.08), transparent 20%),
    radial-gradient(circle at 84% 82%, rgba(255, 255, 255, 0.08), transparent 22%),
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

.auth-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.orb-one {
  top: 10%;
  left: 6%;
  width: 220px;
  height: 220px;
  background: rgba(255, 255, 255, 0.08);
  animation: orbFloatA 11s ease-in-out infinite;
}

.orb-two {
  right: 8%;
  bottom: 12%;
  width: 280px;
  height: 280px;
  background: rgba(255, 255, 255, 0.06);
  animation: orbFloatB 13s ease-in-out infinite;
}

.auth-grid {
  position: relative;
  z-index: 1;
  width: min(1240px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(380px, 460px);
  gap: 40px;
  align-items: center;
}

.auth-copy {
  position: relative;
  padding: 32px 10px 32px 0;
}

.eyebrow {
  display: inline-flex;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  animation: revealUp 0.8s ease both;
}

.auth-copy h1 {
  max-width: 640px;
  margin: 24px 0 18px;
  font-size: clamp(38px, 6vw, 68px);
  line-height: 1.02;
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.96);
  animation: revealUp 0.95s ease both;
  animation-delay: 0.08s;
}

.auth-copy > p {
  max-width: 560px;
  margin: 0;
  font-size: 17px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.6);
  animation: revealUp 1.05s ease both;
  animation-delay: 0.16s;
}

.feature-list {
  margin-top: 42px;
  display: grid;
  gap: 18px;
}

.feature-item {
  display: grid;
  grid-template-columns: 54px 1fr;
  gap: 18px;
  padding: 18px 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.028);
  border: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(16px);
  transition: transform 0.35s ease, border-color 0.35s ease, background 0.35s ease;
  animation: revealUp 0.9s ease both;
}

.feature-item:nth-child(1) {
  animation-delay: 0.24s;
}

.feature-item:nth-child(2) {
  animation-delay: 0.34s;
}

.feature-item:nth-child(3) {
  animation-delay: 0.44s;
}

.feature-item:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
}

.feature-index {
  color: rgba(255, 255, 255, 0.32);
  font-size: 13px;
  letter-spacing: 0.2em;
}

.feature-item strong {
  display: block;
  margin-bottom: 8px;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.94);
}

.feature-item p {
  margin: 0;
  color: rgba(255, 255, 255, 0.56);
  line-height: 1.7;
}

.auth-card {
  transform-origin: center;
  animation: cardIn 0.95s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  animation-delay: 0.22s;
  background: rgba(14, 14, 14, 0.48);
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(24px);
}

.auth-card :deep(.ant-card-head),
.auth-card :deep(.ant-card-body) {
  background: transparent;
}

.auth-card :deep(.ant-card-head) {
  border-bottom-color: rgba(255, 255, 255, 0.09);
}

.auth-card :deep(.ant-input),
.auth-card :deep(.ant-input-password) {
  background: rgba(255, 255, 255, 0.055);
  border-color: rgba(255, 255, 255, 0.13);
  box-shadow: none;
}

.auth-card :deep(.ant-input:focus),
.auth-card :deep(.ant-input-focused),
.auth-card :deep(.ant-input-password-focused),
.auth-card :deep(.ant-input-password:focus-within) {
  border-color: rgba(255, 255, 255, 0.42);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08);
}

.auth-card-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.auth-card-title span {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.96);
}

.auth-card-title small {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.auth-role {
  margin-bottom: 26px;
}

.section-label {
  display: inline-block;
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.58);
  font-size: 13px;
}

.auth-alert {
  margin-bottom: 18px;
}

.auth-submit {
  margin-bottom: 16px;
}

.auth-footer {
  text-align: center;
  color: rgba(255, 255, 255, 0.45);
}

.auth-footer a {
  margin-left: 8px;
  color: rgba(255, 255, 255, 0.92);
  text-decoration: none;
}

.auth-footer a:hover {
  color: #ffffff;
}

@keyframes revealUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(28px) scale(0.98);
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

@keyframes orbFloatA {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(42px, -30px, 0) scale(1.12);
  }
}

@keyframes orbFloatB {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-36px, 28px, 0) scale(1.08);
  }
}

@media (max-width: 980px) {
  .auth-grid {
    grid-template-columns: 1fr;
  }

  .auth-copy {
    padding-right: 0;
  }
}

@media (max-width: 640px) {
  .auth-shell {
    padding: 18px 14px 24px;
  }

  .auth-grid {
    gap: 24px;
  }

  .feature-item {
    grid-template-columns: 1fr;
    gap: 8px;
  }
}
</style>
