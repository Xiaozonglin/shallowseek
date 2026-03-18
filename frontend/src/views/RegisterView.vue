<template>
  <div class="quantum-register">
    <!-- 深空漩涡背景 -->
    <div class="cosmic-vortex">
      <div class="vortex-ring" v-for="n in 5" :key="n" :style="vortexStyle(n)"></div>
      <div class="gravitational-lens"></div>
    </div>
    
    <!-- 量子身份注册面板 -->
    <div class="identity-creation-panel">
      <!-- 注册进度指示器 -->
      <div class="creation-progress">
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
        <div class="progress-steps">
          <div 
            class="step" 
            v-for="step in 3" 
            :key="step"
            :class="{ active: currentStep >= step, completed: currentStep > step }"
          >
            <div class="step-icon">{{ step === 1 ? '⚛️' : step === 2 ? '🔐' : '👤' }}</div>
            <div class="step-label">{{ ['账户信息', '安全设置', '角色选择'][step-1] }}</div>
          </div>
        </div>
      </div>
      
      <!-- 主注册表单 -->
      <div class="creation-form">
        <!-- 步骤1：基础信息 -->
        <div v-show="currentStep === 1" class="creation-step">
          <h2 class="step-title">
            <span class="title-icon">⚛️</span>
            身份创建
          </h2>
          <p class="step-subtitle">创建您的唯一账户标识</p>
          
          <div class="quantum-input-group">
            <input 
              type="text" 
              v-model="username" 
              required
              class="neural-input"
              :class="{ focused: usernameFocused, error: usernameError }"
              @focus="usernameFocused = true"
              @blur="usernameFocused = false; validateUsername()"
            >
            <span class="input-label">用户名</span>
            <div class="input-underline"></div>
            <div class="particle-stream" v-if="usernameFocused"></div>
            <div v-if="usernameError" class="validation-error">{{ usernameError }}</div>
            <div v-else class="validation-hint">2-20个字符，支持字母、数字和下划线</div>
          </div>
          
          <div class="quantum-input-group">
            <input 
              type="email" 
              v-model="email" 
              required
              class="neural-input"
              :class="{ focused: emailFocused, error: emailError }"
              @focus="emailFocused = true"
              @blur="emailFocused = false; validateEmail()"
            >
            <span class="input-label">邮箱地址</span>
            <div class="input-underline"></div>
            <div class="particle-stream" v-if="emailFocused"></div>
            <div v-if="emailError" class="validation-error">{{ emailError }}</div>
            <div v-else class="validation-hint">用于接收系统通知和验证</div>
          </div>
        </div>
        
        <!-- 步骤2：安全设置 -->
        <div v-show="currentStep === 2" class="creation-step">
          <h2 class="step-title">
            <span class="title-icon">🔐</span>
            安全设置
          </h2>
          <p class="step-subtitle">设置您的账户密码</p>
          
          <div class="password-strength">
            <div class="strength-label">加密强度</div>
            <div class="strength-meter">
              <div 
                class="strength-level" 
                :class="strengthClass"
                :style="{ width: `${passwordStrength}%` }"
              ></div>
            </div>
            <div class="strength-text">{{ strengthText }}</div>
          </div>
          
          <div class="quantum-input-group">
            <input 
              :type="showPassword ? 'text' : 'password'"
              v-model="password" 
              required
              class="neural-input"
              :class="{ focused: passwordFocused, error: passwordError }"
              @focus="passwordFocused = true"
              @blur="passwordFocused = false; validatePassword()"
              @input="calculateStrength"
            >
            <span class="input-label">密码</span>
            <div class="input-underline"></div>
            <button 
              type="button" 
              class="visibility-toggle" 
              @click="showPassword = !showPassword"
            >
              <span class="eye-icon">{{ showPassword ? '👁️' : '👁️‍🗨️' }}</span>
            </button>
            <div v-if="passwordError" class="validation-error">{{ passwordError }}</div>
          </div>
          
          <div class="quantum-input-group">
            <input 
              :type="showConfirmPassword ? 'text' : 'password'"
              v-model="confirmPassword" 
              required
              class="neural-input"
              :class="{ focused: confirmPasswordFocused, error: confirmPasswordError }"
              @focus="confirmPasswordFocused = true"
              @blur="confirmPasswordFocused = false; validateConfirmPassword()"
            >
            <span class="input-label">确认密码</span>
            <div class="input-underline"></div>
            <button 
              type="button" 
              class="visibility-toggle" 
              @click="showConfirmPassword = !showConfirmPassword"
            >
              <span class="eye-icon">{{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}</span>
            </button>
            <div v-if="confirmPasswordError" class="validation-error">{{ confirmPasswordError }}</div>
          </div>
          
          <div class="security-features">
            <div class="security-item">
              <span class="security-icon">🔐</span>
              <span class="security-text">端到端加密</span>
            </div>
            <div class="security-item">
              <span class="security-icon">⚡</span>
              <span class="security-text">零知识证明验证</span>
            </div>
            <div class="security-item">
              <span class="security-icon">🛡️</span>
              <span class="security-text">防暴力破解保护</span>
            </div>
          </div>
        </div>
        
        <!-- 步骤3：角色选择 -->
        <div v-show="currentStep === 3" class="creation-step">
          <h2 class="step-title">
            <span class="title-icon">👤</span>
            选择角色
          </h2>
          <p class="step-subtitle">选择您在学习系统中的身份</p>
          
          <div class="role-hologram-selector">
            <div 
              class="role-hologram student"
              :class="{ selected: role === 'student' }"
              @click="selectRole('student')"
            >
              <div class="hologram-core">
                <div class="core-glow"></div>
                <span class="role-icon">🧑‍🎓</span>
              </div>
              <div class="role-info">
                <h3 class="role-title">学生节点</h3>
                <p class="role-description">进行课程学习、AI问答与师生沟通</p>
                <ul class="role-features">
                  <li>AI智能问答</li>
                  <li>实时导师通讯</li>
                  <li>学习历史记录</li>
                </ul>
              </div>
              <div class="role-selection-indicator" v-if="role === 'student'">
                <div class="selection-pulse"></div>
              </div>
            </div>
            
            <div 
              class="role-hologram teacher"
              :class="{ selected: role === 'teacher' }"
              @click="selectRole('teacher')"
            >
              <div class="hologram-core">
                <div class="core-glow"></div>
                <span class="role-icon">👨‍🏫</span>
              </div>
              <div class="role-info">
                <h3 class="role-title">教师节点</h3>
                <p class="role-description">管理知识网络，监督学习进程</p>
                <ul class="role-features">
                  <li>学生数据分析</li>
                  <li>权威答案管理</li>
                  <li>实时通讯回复</li>
                </ul>
              </div>
              <div class="role-selection-indicator" v-if="role === 'teacher'">
                <div class="selection-pulse"></div>
              </div>
            </div>
          </div>
          
          <!-- 协议确认 -->
          <div class="agreement-check">
            <label class="quantum-checkbox">
              <input 
                type="checkbox" 
                v-model="agreedToTerms"
              >
              <div class="checkbox-visual">
                <div class="checkmark"></div>
              </div>
              <span class="checkbox-text">
                我同意 
                <a href="#" class="quantum-link">《量子服务协议》</a> 
                和 
                <a href="#" class="quantum-link">《隐私保护政策》</a>
              </span>
            </label>
            <div v-if="!agreedToTerms && showAgreementError" class="validation-error">
              请同意协议以继续
            </div>
          </div>
        </div>
        
        <!-- 错误提示 -->
        <div v-if="errorMessage" class="quantum-alert error">
          <div class="alert-icon">⚠️</div>
          <div class="alert-content">
            <div class="alert-title">创建失败</div>
            <div class="alert-message">{{ errorMessage }}</div>
          </div>
          <div class="alert-close" @click="errorMessage = ''">×</div>
        </div>
        
        <!-- 成功提示 -->
        <div v-if="successMessage" class="quantum-alert success">
          <div class="alert-icon">✅</div>
          <div class="alert-content">
            <div class="alert-title">创建成功</div>
            <div class="alert-message">{{ successMessage }}</div>
          </div>
        </div>
        
        <!-- 导航按钮 -->
        <div class="creation-navigation">
          <button 
            v-if="currentStep > 1" 
            class="nav-btn back"
            @click="previousStep"
            :disabled="loading"
          >
            <span class="nav-icon">←</span>
            <span class="nav-text">上一步</span>
          </button>
          
          <button 
            v-if="currentStep < 3" 
            class="nav-btn next"
            @click="nextStep"
            :disabled="!canProceed || loading"
          >
            <span class="nav-text">继续</span>
            <span class="nav-icon">→</span>
            <div class="nav-glow"></div>
          </button>
          
          <button 
            v-if="currentStep === 3" 
            class="nav-btn submit"
            @click="handleRegister"
            :disabled="!canSubmit || loading"
          >
            <span class="nav-text">{{ loading ? '创建中...' : '创建账户' }}</span>
            <div class="nav-particles">
              <div class="particle" v-for="n in 5" :key="n"></div>
            </div>
            <div class="nav-glow"></div>
          </button>
        </div>
        
        <!-- 已有账户 -->
        <div class="existing-account">
          <span class="existing-text">已有身份？</span>
          <a href="#" class="quantum-link login" @click.prevent="goToLogin">
            <span class="link-text">立即登录</span>
            <span class="link-arrow">↗</span>
          </a>
        </div>
      </div>
    </div>
    
    <!-- 创建过程中的量子效应 -->
    <div v-if="loading" class="quantum-creation-effect">
      <div class="creation-ring"></div>
      <div class="creation-particles">
        <div class="particle" v-for="n in 12" :key="n"></div>
      </div>
      <div class="creation-status">正在创建身份...</div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'QuantumRegister',
  setup() {
    const router = useRouter()
    
    // 表单数据
    const username = ref('')
    const email = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const role = ref('student')
    const agreedToTerms = ref(false)
    
    // 状态管理
    const currentStep = ref(1)
    const progress = ref(33)
    const loading = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')
    const showAgreementError = ref(false)
    
    // 输入框状态
    const usernameFocused = ref(false)
    const emailFocused = ref(false)
    const passwordFocused = ref(false)
    const confirmPasswordFocused = ref(false)
    const showPassword = ref(false)
    const showConfirmPassword = ref(false)
    
    // 验证状态
    const usernameError = ref('')
    const emailError = ref('')
    const passwordError = ref('')
    const confirmPasswordError = ref('')
    const passwordStrength = ref(0)
    
    // 进度控制
    const canProceed = computed(() => {
      switch(currentStep.value) {
        case 1:
          return username.value.trim() && email.value.trim() && !usernameError.value && !emailError.value
        case 2:
          return password.value.trim() && confirmPassword.value.trim() && !passwordError.value && !confirmPasswordError.value
        case 3:
          return role.value && agreedToTerms.value
        default:
          return false
      }
    })
    
    const canSubmit = computed(() => {
      return canProceed.value && agreedToTerms.value
    })
    
    // 密码强度计算
    const calculateStrength = () => {
      let strength = 0
      if (password.value.length >= 8) strength += 20
      if (/[A-Z]/.test(password.value)) strength += 20
      if (/[a-z]/.test(password.value)) strength += 20
      if (/[0-9]/.test(password.value)) strength += 20
      if (/[^A-Za-z0-9]/.test(password.value)) strength += 20
      passwordStrength.value = Math.min(strength, 100)
    }
    
    const strengthClass = computed(() => {
      if (passwordStrength.value < 30) return 'weak'
      if (passwordStrength.value < 60) return 'medium'
      if (passwordStrength.value < 80) return 'strong'
      return 'very-strong'
    })
    
    const strengthText = computed(() => {
      if (passwordStrength.value < 30) return '脆弱'
      if (passwordStrength.value < 60) return '一般'
      if (passwordStrength.value < 80) return '良好'
      return '极强'
    })
    
    // 验证方法
    const validateUsername = () => {
      if (!username.value.trim()) {
        usernameError.value = '请输入用户名'
      } else if (username.value.length < 2 || username.value.length > 20) {
        usernameError.value = '名称长度为2-20个字符'
      } else if (!/^[a-zA-Z0-9_]+$/.test(username.value)) {
        usernameError.value = '只能包含字母、数字和下划线'
      } else {
        usernameError.value = ''
      }
    }
    
    const validateEmail = () => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!email.value.trim()) {
        emailError.value = '请输入邮箱地址'
      } else if (!emailRegex.test(email.value)) {
        emailError.value = '邮箱格式不正确'
      } else {
        emailError.value = ''
      }
    }
    
    const validatePassword = () => {
      if (!password.value.trim()) {
        passwordError.value = '请输入密码'
      } else if (password.value.length < 8) {
        passwordError.value = '密码长度至少8个字符'
      } else {
        passwordError.value = ''
      }
    }
    
    const validateConfirmPassword = () => {
      if (!confirmPassword.value.trim()) {
        confirmPasswordError.value = '请确认密码'
      } else if (password.value !== confirmPassword.value) {
        confirmPasswordError.value = '两次输入的密码不一致'
      } else {
        confirmPasswordError.value = ''
      }
    }
    
    // 步骤导航
    const nextStep = () => {
      if (!canProceed.value) return
      currentStep.value++
      progress.value = (currentStep.value / 3) * 100
    }
    
    const previousStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--
        progress.value = (currentStep.value / 3) * 100
      }
    }
    
    const selectRole = (selectedRole) => {
      role.value = selectedRole
    }
    
    // 注册处理
    const handleRegister = async () => {
      if (!canSubmit.value) {
        showAgreementError.value = !agreedToTerms.value
        return
      }
      
      errorMessage.value = ''
      successMessage.value = ''
      loading.value = true
      
      try {
        const response = await axios.post('/api/register', {
          username: username.value,
          email: email.value,
          password: password.value,
          role: role.value
        })
        
        successMessage.value = '身份创建成功！正在建立神经网络连接...'
        console.log('注册成功:', response.data)
        
        // 3秒后跳转到登录页面
        setTimeout(() => {
          router.push('/login')
        }, 3000)
        
      } catch (error) {
        if (error.response) {
          errorMessage.value = error.response.data.error || '身份创建失败'
        } else {
          errorMessage.value = '连接异常，请检查网络'
        }
        console.error('创建错误:', error)
      } finally {
        loading.value = false
      }
    }
    
    const goToLogin = () => {
      router.push('/login')
    }
    
    const vortexStyle = (n) => {
      const size = 200 + n * 100
      const opacity = 0.1 - n * 0.015
      return {
        width: `${size}px`,
        height: `${size}px`,
        opacity: opacity,
        animationDelay: `${n * 0.5}s`
      }
    }
    
    return {
      username,
      email,
      password,
      confirmPassword,
      role,
      agreedToTerms,
      currentStep,
      progress,
      loading,
      errorMessage,
      successMessage,
      showAgreementError,
      usernameFocused,
      emailFocused,
      passwordFocused,
      confirmPasswordFocused,
      showPassword,
      showConfirmPassword,
      usernameError,
      emailError,
      passwordError,
      confirmPasswordError,
      passwordStrength,
      canProceed,
      canSubmit,
      strengthClass,
      strengthText,
      calculateStrength,
      validateUsername,
      validateEmail,
      validatePassword,
      validateConfirmPassword,
      nextStep,
      previousStep,
      selectRole,
      handleRegister,
      goToLogin,
      vortexStyle
    }
  }
}
</script>

<style scoped>
.quantum-register {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 30% 20%, #0a0a1a 0%, #000000 60%),
    radial-gradient(ellipse at 70% 80%, #001a33 0%, transparent 60%);
  position: relative;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.cosmic-vortex {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.vortex-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 150, 255, 0.1);
  border-radius: 50%;
  animation: vortexSpin 20s linear infinite;
}

@keyframes vortexSpin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.gravitational-lens {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(0, 200, 255, 0.1) 0%, transparent 70%);
  filter: blur(20px);
}

.identity-creation-panel {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  background: rgba(10, 10, 20, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.5),
    0 0 100px rgba(0, 150, 255, 0.1);
}

.creation-progress {
  margin-bottom: 40px;
}

.progress-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 20px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ffff, #0088ff);
  border-radius: 2px;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  position: relative;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 2;
}

.step-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  font-size: 18px;
  transition: all 0.3s;
}

.step.active .step-icon {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.3);
  color: #00ffff;
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.step.completed .step-icon {
  background: rgba(0, 255, 128, 0.1);
  border-color: rgba(0, 255, 128, 0.3);
  color: #00ff80;
}

.step-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s;
}

.step.active .step-label {
  color: #00ffff;
  font-weight: 600;
}

.creation-form {
  margin-top: 10px;
}

.creation-step {
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.step-title {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #f8fafc;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.step-subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 30px;
}

.quantum-input-group {
  position: relative;
  margin-bottom: 30px;
}

.neural-input {
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

.neural-input:focus {
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(15, 23, 42, 0.8);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
}

.neural-input.error {
  border-color: rgba(255, 100, 100, 0.5);
  background: rgba(255, 100, 100, 0.05);
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

.neural-input:focus + .input-label,
.neural-input:not(:placeholder-shown) + .input-label {
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

.neural-input:focus ~ .input-underline {
  transform: scaleX(1);
}

.particle-stream {
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent, 
    #00ffff, 
    transparent
  );
  animation: streamFlow 2s infinite;
  filter: blur(1px);
}

@keyframes streamFlow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.validation-error {
  color: #ff6b6b;
  font-size: 12px;
  margin-top: 6px;
  animation: slideIn 0.3s ease-out;
}

.validation-hint {
  color: #64748b;
  font-size: 12px;
  margin-top: 6px;
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

.password-strength {
  margin-bottom: 30px;
}

.strength-label {
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 8px;
}

.strength-meter {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.strength-level {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s, background-color 0.3s;
}

.strength-level.weak {
  background: linear-gradient(90deg, #ff6b6b, #ff8e8e);
}

.strength-level.medium {
  background: linear-gradient(90deg, #ffa726, #ffb74d);
}

.strength-level.strong {
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.strength-level.very-strong {
  background: linear-gradient(90deg, #00c853, #00e676);
}

.strength-text {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
}

.security-features {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  padding: 20px;
  background: rgba(0, 150, 255, 0.05);
  border: 1px solid rgba(0, 150, 255, 0.1);
  border-radius: 12px;
}

.security-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.security-icon {
  font-size: 16px;
}

.security-text {
  color: #94a3b8;
  font-size: 12px;
}

.role-hologram-selector {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 30px;
}

.role-hologram {
  display: flex;
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.role-hologram:hover {
  background: rgba(15, 23, 42, 0.8);
  transform: translateY(-2px);
  border-color: rgba(0, 255, 255, 0.2);
}

.role-hologram.selected {
  background: rgba(0, 150, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.3);
  box-shadow: 0 0 30px rgba(0, 200, 255, 0.3);
}

.role-hologram.student.selected {
  background: rgba(0, 150, 255, 0.1);
  border-color: rgba(0, 200, 255, 0.3);
}

.role-hologram.teacher.selected {
  background: rgba(156, 39, 176, 0.1);
  border-color: rgba(156, 39, 176, 0.3);
}

.hologram-core {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  margin-right: 20px;
  position: relative;
  flex-shrink: 0;
}

.core-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle, rgba(0, 255, 255, 0.2) 0%, transparent 70%);
  filter: blur(10px);
  opacity: 0;
  transition: opacity 0.3s;
}

.role-hologram.selected .core-glow {
  opacity: 1;
}

.role-icon {
  font-size: 28px;
  position: relative;
  z-index: 2;
}

.role-info {
  flex: 1;
}

.role-title {
  color: #f8fafc;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.role-description {
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 12px;
  line-height: 1.5;
}

.role-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.role-features li {
  color: #cbd5e1;
  font-size: 12px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
}

.role-selection-indicator {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  background: #00ffff;
  border-radius: 50%;
  box-shadow: 0 0 10px #00ffff;
}

.selection-pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #00ffff;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.agreement-check {
  margin-bottom: 30px;
}

.quantum-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
}

.quantum-checkbox input {
  display: none;
}

.checkbox-visual {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  position: relative;
  transition: all 0.3s;
  flex-shrink: 0;
}

.quantum-checkbox:hover .checkbox-visual {
  border-color: rgba(0, 255, 255, 0.3);
}

.quantum-checkbox input:checked + .checkbox-visual {
  background: linear-gradient(135deg, #00ffff, #0088ff);
  border-color: transparent;
}

.checkmark {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0);
  color: #0f172a;
  font-size: 12px;
  font-weight: bold;
  transition: transform 0.3s;
}

.quantum-checkbox input:checked + .checkbox-visual .checkmark {
  transform: translate(-50%, -50%) scale(1);
}

.quantum-link {
  color: #00ffff;
  text-decoration: none;
  transition: all 0.3s;
  position: relative;
  padding: 2px 0;
}

.quantum-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 1px;
  background: #00ffff;
  transition: width 0.3s;
}

.quantum-link:hover::after {
  width: 100%;
}

.quantum-alert {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin-bottom: 20px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  animation: slideIn 0.3s ease-out;
}

.quantum-alert.error {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.2);
}

.quantum-alert.success {
  background: rgba(0, 200, 128, 0.1);
  border: 1px solid rgba(0, 200, 128, 0.2);
}

.alert-icon {
  font-size: 20px;
  flex-shrink: 0;
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

.quantum-alert.success .alert-title {
  color: #00ff80;
}

.alert-message {
  color: #fecaca;
  font-size: 11px;
}

.quantum-alert.success .alert-message {
  color: #94f8d1;
}

.alert-close {
  color: #fca5a5;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  transition: color 0.3s;
  flex-shrink: 0;
}

.alert-close:hover {
  color: white;
}

.creation-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 30px;
  margin-bottom: 20px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.nav-btn.back {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.nav-btn.back:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: #f8fafc;
}

.nav-btn.next,
.nav-btn.submit {
  background: linear-gradient(135deg, #00ffff, #0088ff);
  color: #0f172a;
  box-shadow: 0 4px 20px rgba(0, 200, 255, 0.3);
}

.nav-btn.next:hover:not(:disabled),
.nav-btn.submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(0, 200, 255, 0.4);
}

.nav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.nav-glow {
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

.nav-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.nav-particles .particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  animation: floatOut 1s infinite;
}

@keyframes floatOut {
  0% {
    transform: translate(0, 0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(var(--tx), var(--ty)) scale(0);
    opacity: 0;
  }
}

.nav-particles .particle:nth-child(1) { --tx: 20px; --ty: -20px; animation-delay: 0s; }
.nav-particles .particle:nth-child(2) { --tx: -20px; --ty: 20px; animation-delay: 0.2s; }
.nav-particles .particle:nth-child(3) { --tx: 20px; --ty: 20px; animation-delay: 0.4s; }
.nav-particles .particle:nth-child(4) { --tx: -20px; --ty: -20px; animation-delay: 0.6s; }
.nav-particles .particle:nth-child(5) { --tx: 0; --ty: -30px; animation-delay: 0.8s; }

.existing-account {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.existing-text {
  color: #94a3b8;
  font-size: 14px;
  margin-right: 8px;
}

.quantum-link.login {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #00ffff;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s;
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.2);
}

.quantum-link.login:hover {
  background: rgba(0, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}

.link-arrow {
  transition: transform 0.3s;
}

.quantum-link.login:hover .link-arrow {
  transform: translate(2px, -2px);
}

.quantum-creation-effect {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.creation-ring {
  width: 100px;
  height: 100px;
  border: 2px solid rgba(0, 255, 255, 0.3);
  border-top-color: #00ffff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.creation-particles {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 150px;
  height: 150px;
}

.creation-particles .particle {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 6px;
  height: 6px;
  background: #00ffff;
  border-radius: 50%;
  animation: creationOrbit 2s linear infinite;
  box-shadow: 0 0 10px #00ffff;
}

@keyframes creationOrbit {
  from { transform: rotate(0deg) translateX(60px) rotate(0deg); }
  to { transform: rotate(360deg) translateX(60px) rotate(-360deg); }
}

.creation-status {
  color: #00ffff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  animation: pulse 2s infinite;
}
</style>