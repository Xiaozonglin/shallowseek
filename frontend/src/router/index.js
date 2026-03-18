import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import axios from 'axios'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/login'  // 首页重定向到登录页
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/student',
      name: 'student',
      component: () => import('../views/StudentView.vue'),
      meta: { requiresAuth: true, role: 'student' }
    },
    {
      path: '/teacher',
      name: 'teacher',
      component: () => import('../views/TeacherView.vue'),
      meta: { requiresAuth: true, role: 'teacher' }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { requiresAuth: false }
    }
  ]
})

// 全局前置守卫：检查登录状态和角色权限
router.beforeEach(async (to, from) => {
  // 如果页面不需要认证，直接放行
  if (!to.meta.requiresAuth) {
    return
  }

  try {
    // 检查用户登录状态
    const response = await axios.get('/api/check-auth')
    
    if (response.data.authenticated) {
      const userRole = response.data.user.role
      
      // 检查角色权限
      if (to.meta.role && to.meta.role !== userRole) {
        // 角色不匹配，重定向到正确的页面
        if (userRole === 'student') {
          return '/student'
        } else if (userRole === 'teacher') {
          return '/teacher'
        } else {
          return '/login'
        }
      }
      // 认证通过，放行
      return
    } else {
      // 未登录，重定向到登录页
      return '/login'
    }
  } catch (error) {
    // 检查认证失败，重定向到登录页
    console.error('认证检查失败:', error)
    return '/login'
  }
})

export default router