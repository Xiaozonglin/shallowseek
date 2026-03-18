<template>
  <q></q><div class="cosmos-login">
    <!-- 星空背景层 -->
    <div class="starry-bg">
      <div class="star" v-for="n in 50" :key="n" :style="starStyle(n)"></div>
    </div>
    
    <!-- 主登录面板 -->
    <div class="quantum-login-panel">
      <!-- 头部品牌区 -->
      <div class="brand-zone">
        <div class="quantum-logo">
          <div class="logo-core"></div>
          <div class="logo-orbits">
            <div class="orbit" v-for="i in 3" :key="i"></div>
          </div>
        </div>
        <h1 class="neo-title">XDwe<span class="gradient-text">AI</span></h1>
        <p class="subtitle">XDU专用学习系统</p>
      </div>
      
      <!-- 角色选择 - 胶囊式设计 -->
      <div class="capsule-selector">
        <div 
          class="capsule-option"
          :class="{ active: role === 'student' }"
          @click="setRole('student')"
        >
          <div class="capsule-icon">🧑‍🎓</div>
          <span class="capsule-label">学生模式</span>
          <div class="capsule-indicator" v-if="role === 'student'"></div>
        </div>
        <div 
          class="capsule-option"
          :class="{ active: role === 'teacher' }"
          @click="setRole('teacher')"
        >
          <div class="capsule-icon">👨‍🏫</div>
          <span class="capsule-label">教师模式</span>
          <div class="capsule-indicator" v-if="role === 'teacher'"></div>
        </div>
      </div>
      
      <!-- 登录表单 -->
      <form class="cyber-form" @submit.prevent="handleLogin">
        <!-- 动态输入框 -->
        <div class="hologram-input-group">
          <input 
            type="email" 
            v-model="email"
            required
            class="hologram-input"
            :class="{ focused: emailFocused }"
            @focus="emailFocused = true"
            @blur="emailFocused = false"
          >
          <span class="input-label">邮箱</span>
          <div class="input-underline"></div>
          <div class="input-glow" :class="{ active: emailFocused }"></div>
        </div>
        
        <div class="hologram-input-group">
          <input 
            type="password" 
            v-model="password"
            required
            class="hologram-input"
            :class="{ focused: passwordFocused }"
            @focus="passwordFocused = true"
            @blur="passwordFocused = false"
          >
          <span class="input-label">密码</span>
          <div class="input-underline"></div>
          <div class="input-glow" :class="{ active: passwordFocused }"></div>
          <button type="button" class="visibility-toggle" @click="togglePasswordVisibility">
            <span class="eye-icon">{{ showPassword ? '👁️' : '👁️‍🗨️' }}</span>
          </button>
        </div>
        
        <!-- 状态指示器 -->
        <div v-if="loading" class="quantum-loader">
          <div class="quantum-dot"></div>
          <div class="quantum-dot"></div>
          <div class="quantum-dot"></div>
          <span class="loading-text">正在验证身份...</span>
        </div>
        
        <!-- 错误提示 - 全息投影风格 -->
        <div v-if="errorMessage" class="hologram-alert">
          <div class="alert-icon">⚠️</div>
          <div class="alert-content">
            <div class="alert-title">登录失败</div>
            <div class="alert-message">{{ errorMessage }}</div>
          </div>
          <div class="alert-close" @click="errorMessage = ''">×</div>
        </div>
        
        <!-- 登录按钮 - 脉冲效果 -->
        <button 
          type="submit" 
          class="quantum-btn"
          :class="{ loading: loading }"
          :disabled="loading"
        >
          <span class="btn-text">登录验证</span>
          <span class="btn-pulse"></span>
          <span class="btn-glow"></span>
        </button>
        
        <!-- 辅助操作 -->
        <div class="auxiliary-actions">
          <a href="#" class="cyber-link" @click.prevent="goToRegister">
            <span class="link-text">创建新身份</span>
            <span class="link-arrow">→</span>
          </a>
          <div class="divider">|</div>
          <a href="#" class="cyber-link">
            <span class="link-text">密码恢复</span>
            <span class="link-arrow">↻</span>
          </a>
        </div>
      </form>
      
      <!-- 底部状态栏 -->
      <div class="status-bar">
        <div class="status-item">
          <span class="status-icon">🛡️</span>
          <span class="status-text">加密传输</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item">
          <span class="status-icon">⚡</span>
          <span class="status-text">低延迟响应</span>
        </div>
        <div class="status-divider"></div>
        <div class="status-item">
          <span class="status-icon">🌌</span>
          <span class="status-text">分布式部署</span>
        </div>
      </div>
    </div>
    
    <!-- 浮动粒子 -->
    <div class="floating-particles">
      <div class="particle" v-for="n in 20" :key="'p'+n"></div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'CosmosLogin',
  setup() {
    const router = useRouter()
    const email = ref('')
    const password = ref('')
    const role = ref('student')
    const errorMessage = ref('')
    const loading = ref(false)
    const emailFocused = ref(false)
    const passwordFocused = ref(false)
    const showPassword = ref(false)
    
    // 随机星星样式
    const starStyle = (n) => {
      const size = Math.random() * 2 + 1
      return {
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        width: `${size}px`,
        height: `${size}px`,
        animationDelay: `${Math.random() * 5}s`,
        opacity: Math.random() * 0.7 + 0.3
      }
    }
    
    const setRole = (selectedRole) => {
      role.value = selectedRole
    }
    
    const handleLogin = async () => {
      errorMessage.value = ''
      loading.value = true
      
      try {
        const response = await axios.post('/api/login', {
          email: email.value,
          password: password.value
        })
        
        console.log('登录成功:', response.data)
        
        if (role.value === 'student') {
          router.push('/student')
        } else {
          router.push('/teacher')
        }
        
      } catch (error) {
        if (error.response) {
          errorMessage.value = error.response.data.error || '邮箱或密码错误'
        } else {
          errorMessage.value = '网络连接异常'
        }
        console.error('接入错误:', error)
      } finally {
        loading.value = false
      }
    }
    
    const goToRegister = () => {
      router.push('/register')
    }
    
    const togglePasswordVisibility = () => {
      const input = document.querySelector('input[type="password"]')
      if (input) {
        input.type = showPassword.value ? 'password' : 'text'
        showPassword.value = !showPassword.value
      }
    }
    
    return {
      email,
      password,
      role,
      errorMessage,
      loading,
      emailFocused,
      passwordFocused,
      showPassword,
      starStyle,
      setRole,
      handleLogin,
      goToRegister,
      togglePasswordVisibility
    }
  }
}
</script>

<style scoped>
.cosmos-login {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 20% 20%, #0a0a1a 0%, #000000 70%),
    radial-gradient(ellipse at 80% 80%, #001122 0%, transparent 50%);
  position: relative;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.starry-bg {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.star {
  position: absolute;
  background: white;
  border-radius: 50%;
  animation: twinkle 3s infinite;
  box-shadow: 0 0 4px rgba(255, 255, 255, 0.5);
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.quantum-login-panel {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  margin: 0 auto;
  padding: 50px 40px;
  background: rgba(10, 10, 20, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.5),
    0 0 100px rgba(0, 200, 255, 0.1);
}

.brand-zone {
  text-align: center;
  margin-bottom: 40px;
}

.quantum-logo {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.logo-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #00ffff, #0088ff);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(0, 255, 255, 0.4); 
  }
  50% { 
    box-shadow: 0 0 0 20px rgba(0, 255, 255, 0); 
  }
}

.logo-orbits {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.logo-orbits .orbit {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 50%;
  animation: orbit 4s linear infinite;
}

.logo-orbits .orbit:nth-child(1) {
  width: 60px;
  height: 60px;
  animation-delay: 0s;
}

.logo-orbits .orbit:nth-child(2) {
  width: 40px;
  height: 40px;
  animation-delay: -1.33s;
}

.logo-orbits .orbit:nth-child(3) {
  width: 20px;
  height: 20px;
  animation-delay: -2.66s;
}

@keyframes orbit {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.neo-title {
  font-size: 36px;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.5px;
  margin-bottom: 8px;
}

.gradient-text {
  background: linear-gradient(135deg, #00ffff, #8b5cf6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-left: 4px;
}

.subtitle {
  color: #94a3b8;
  font-size: 14px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.capsule-selector {
  display: flex;
  gap: 12px;
  margin-bottom: 40px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 50px;
  padding: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.capsule-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 20px;
  border-radius: 40px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  background: transparent;
  border: 1px solid transparent;
}

.capsule-option.active {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(0, 255, 255, 0.2);
  box-shadow: 0 4px 20px rgba(0, 200, 255, 0.2);
}

.capsule-icon {
  font-size: 24px;
  margin-bottom: 8px;
  transition: transform 0.3s;
}

.capsule-option.active .capsule-icon {
  transform: scale(1.1);
}

.capsule-label {
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
  transition: color 0.3s;
}

.capsule-option.active .capsule-label {
  color: #00ffff;
  font-weight: 600;
}

.capsule-indicator {
  position: absolute;
  top: -2px;
  right: 12px;
  width: 8px;
  height: 8px;
  background: #00ffff;
  border-radius: 50%;
  box-shadow: 0 0 10px #00ffff;
  animation: blink 2s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.cyber-form {
  margin-bottom: 40px;
}

.hologram-input-group {
  position: relative;
  margin-bottom: 28px;
}

.hologram-input {
  width: 100%;
  padding: 20px 20px 10px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  font-size: 16px;
  color: #f8fafc;
  transition: all 0.3s;
  outline: none;
}

.hologram-input:focus {
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(15, 23, 42, 0.8);
}

.input-label {
  position: absolute;
  top: 12px;
  left: 20px;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.3s;
  pointer-events: none;
}

.hologram-input:focus + .input-label,
.hologram-input:not(:placeholder-shown) + .input-label {
  top: 8px;
  font-size: 10px;
  color: #00ffff;
}

.input-underline {
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.5), transparent);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.hologram-input:focus ~ .input-underline {
  transform: scaleX(1);
}

.visibility-toggle {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  transition: color 0.3s;
}

.visibility-toggle:hover {
  color: #00ffff;
}

.quantum-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 20px 0;
  padding: 16px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.quantum-dot {
  width: 8px;
  height: 8px;
  background: #00ffff;
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}

.quantum-dot:nth-child(1) { animation-delay: -0.32s; }
.quantum-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.loading-text {
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 1px;
}

.hologram-alert {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin: 20px 0;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.alert-icon {
  font-size: 20px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  color: #fca5a5;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 2px;
}

.alert-message {
  color: #fecaca;
  font-size: 11px;
}

.alert-close {
  color: #fca5a5;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  transition: color 0.3s;
}

.alert-close:hover {
  color: white;
}

.quantum-btn {
  position: relative;
  width: 100%;
  padding: 20px;
  background: linear-gradient(135deg, #00ffff, #0088ff);
  border: none;
  border-radius: 12px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  margin: 20px 0;
}

.quantum-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 
    0 10px 25px rgba(0, 200, 255, 0.4),
    0 0 50px rgba(0, 255, 255, 0.2);
}

.quantum-btn:active:not(:disabled) {
  transform: translateY(0);
}

.quantum-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  transform: translate(-50%, -50%);
  opacity: 0;
}

.quantum-btn:hover .btn-pulse:not(:disabled) {
  animation: pulseOut 0.6s;
}

@keyframes pulseOut {
  0% {
    width: 0;
    height: 0;
    opacity: 0.6;
  }
  100% {
    width: 200px;
    height: 200px;
    opacity: 0;
  }
}

.btn-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(255, 255, 255, 0.2), 
    transparent
  );
  transform: translateX(-100%);
  animation: slideGlow 2s infinite;
}

@keyframes slideGlow {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
  100% { transform: translateX(100%); }
}

.auxiliary-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 30px;
}

.cyber-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 13px;
  transition: all 0.3s;
  position: relative;
  padding: 4px 8px;
  border-radius: 6px;
}

.cyber-link:hover {
  color: #00ffff;
  background: rgba(0, 255, 255, 0.1);
}

.link-arrow {
  transition: transform 0.3s;
}

.cyber-link:hover .link-arrow {
  transform: translateX(3px);
}

.divider {
  color: #475569;
  font-size: 12px;
}

.status-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  margin-top: 40px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
}

.status-icon {
  font-size: 12px;
}

.status-text {
  color: #94a3b8;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.status-divider {
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.1);
}

.floating-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 1;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgba(0, 255, 255, 0.5);
  border-radius: 50%;
  animation: float 20s infinite linear;
}

@keyframes float {
  0% {
    transform: translateY(100vh) translateX(0);
  }
  100% {
    transform: translateY(-100px) translateX(100px);
  }
}
</style>