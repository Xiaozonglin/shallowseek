<template>
  <div class="login-container">
    <div class="login-box">
      <h2>学习助手系统登录</h2>
      
      <!-- 角色选择 -->
      <div class="role-selector">
        <button 
          @click="setRole('student')" 
          :class="{ active: role === 'student' }"
        >
          学生
        </button>
        <button 
          @click="setRole('teacher')" 
          :class="{ active: role === 'teacher' }"
        >
          老师
        </button>
      </div>
      
      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>邮箱</label>
          <input 
            type="email" 
            v-model="email" 
            placeholder="请输入邮箱地址"
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
        
        <!-- 错误信息显示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        
        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        
        <p class="register-link">
          还没有账号？<a href="#" @click="goToRegister">立即注册</a>
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
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const email = ref('')
    const password = ref('')
    const role = ref('student') // 默认学生角色
    const errorMessage = ref('')
    const loading = ref(false)
    
    // 设置角色
    const setRole = (selectedRole) => {
      role.value = selectedRole
    }
    
    // 处理登录
    const handleLogin = async () => {
      errorMessage.value = ''
      loading.value = true
      
      try {
        // 调用后端登录接口
        const response = await axios.post('/api/login', {
          email: email.value,
          password: password.value
        })
        
        // 登录成功
        console.log('登录成功:', response.data)
        
        // 根据角色跳转到不同页面
        if (role.value === 'student') {
          router.push('/student')
        } else {
          router.push('/teacher')
        }
        
      } catch (error) {
        // 处理错误
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
    
    // 跳转到注册页面
    const goToRegister = () => {
      router.push('/register')
    }
    
    return {
      email,
      password,
      role,
      errorMessage,
      loading,
      setRole,
      handleLogin,
      goToRegister
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-box {
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

.role-selector {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
}

.role-selector button {
  flex: 1;
  padding: 12px;
  border: 2px solid #ddd;
  background: white;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.role-selector button.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
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

.error-message {
  color: #e74c3c;
  background: #ffeaea;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: #666;
}

.register-link a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>