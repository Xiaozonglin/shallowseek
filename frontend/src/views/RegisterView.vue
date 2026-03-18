<template>
  <div class="register-container">
    <div class="register-box">
      <h2>注册新账户</h2>
      
      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label>用户名</label>
          <input 
            type="text" 
            v-model="username" 
            placeholder="请输入用户名"
            required
          >
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="password" 
            placeholder="请输入密码"
            required
          >
        </div>
        
        <div class="form-group">
          <label>确认密码</label>
          <input 
            type="password" 
            v-model="confirmPassword" 
            placeholder="请再次输入密码"
            required
          >
        </div>

        <div class="form-group">
          <label>邮箱</label>
          <input 
            type="email"
            v-model="email"
            placeholder="请输入邮箱地址"
            required
          >
        </div>
        
        <div class="role-selector">
          <label>注册身份</label>
          <div class="role-options">
            <label>
              <input 
                type="radio" 
                v-model="role" 
                value="student"
                checked
              > 学生
            </label>
            <label>
              <input 
                type="radio" 
                v-model="role" 
                value="teacher"
              > 老师
            </label>
          </div>
        </div>
        
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>
        
        <button type="submit" class="register-btn" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
        
        <p class="login-link">
          已有账号？<a href="#" @click="goToLogin">立即登录</a>
        </p>
      </form>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'RegisterView',
  setup() {
    const router = useRouter()
    const username = ref('')
    const email = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const role = ref('student')
    const errorMessage = ref('')
    const successMessage = ref('')
    const loading = ref(false)
    
    // 处理注册
    const handleRegister = async () => {
      // 验证密码
      if (password.value !== confirmPassword.value) {
        errorMessage.value = '两次输入的密码不一致'
        return
      }
      
      errorMessage.value = ''
      successMessage.value = ''
      loading.value = true
      
      try {
        // 调用后端注册接口
        const response = await axios.post('/api/register', {
          username: username.value,
          email: email.value,
          password: password.value,
          role: role.value
        })
        
        // 注册成功
        successMessage.value = '注册成功！正在跳转到登录页面...'
        console.log('注册成功:', response.data)
        
        // 2秒后跳转到登录页面
        setTimeout(() => {
          router.push('/login')
        }, 2000)
        
      } catch (error) {
        // 处理错误
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
    
    // 跳转到登录页面
    const goToLogin = () => {
      router.push('/login')
    }
    
    return {
      username,
      email,
      password,
      confirmPassword,
      role,
      errorMessage,
      successMessage,
      loading,
      handleRegister,
      goToLogin
    }
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-box {
  background: white;
  padding: 40px;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px 15px;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.3s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.role-selector {
  margin-bottom: 20px;
}

.role-selector label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

.role-options {
  display: flex;
  gap: 20px;
}

.role-options label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.error-message {
  color: #e74c3c;
  background: #ffeaea;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
  font-size: 14px;
}

.success-message {
  color: #28a745;
  background: #e8f5e9;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
  font-size: 14px;
}

.register-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.register-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.register-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-link {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.login-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>