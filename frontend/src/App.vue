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

export default {
  name: 'App',
  setup() {
    const route = useRoute()
    const router = useRouter()
    
    // 判断当前是否是登录页
    const isLoginPage = computed(() => route.path === '/login')
    
    // 模拟用户信息（后续会从登录接口获取）
    const user = { username: '张三' }
    
    // 退出登录
    const handleLogout = () => {
      // 调用后端退出接口
      // 然后跳转到登录页
      router.push('/login')
    }
    
    return {
      isLoginPage,
      user,
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