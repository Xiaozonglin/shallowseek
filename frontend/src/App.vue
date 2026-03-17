<template>
  <div id="app">
    <!-- 导航栏 -->
    <nav v-if="!isLoginPage">
      <div class="nav-container">
        <div class="nav-brand">学习助手</div>
        <div class="nav-user" v-if="user">
          欢迎，{{ user.username }}
          <button @click="handleLogout" class="logout-btn">退出</button>
        </div>
      </div>
    </nav>
    
    <!-- 页面内容 -->
    <router-view />
  </div>
</template>

<script>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'App',
  setup() {
    const route = useRoute()
    const router = useRouter()
    
    // 判断当前是否是登录页
    const isLoginPage = computed(() => route.path === '/login')
    
    // 退出登录
    const handleLogout = async () => {
      try {
        // 发送登出请求到后端
        const response = await axios.post('/api/logout')
        
        if (response.status === 200 && response.data.message === 'Logout successful') {
          console.log('登出成功')
          // 清除前端的用户状态（如果有的话）
          // 例如：localStorage.removeItem('user')
          
          // 跳转到登录页
          router.push('/login')
        } else {
          console.error('登出响应异常:', response.data)
          // 即使响应异常，也跳转到登录页
          router.push('/login')
        }
      } catch (error) {
        console.error('登出失败:', error)
        // 即使请求失败，也跳转到登录页（保证用户可以重新登录）
        router.push('/login')
      }
    }
    
    return {
      isLoginPage,
      handleLogout
    }
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
  -moz-osx-font-smoasing: grayscale;
}

nav {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
}

.nav-brand {
  font-size: 24px;
  font-weight: bold;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logout-btn {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 5px 15px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>