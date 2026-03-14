<template>
  <div class="teacher-container">
    <h1>教师工作台</h1>
    <p class="subtitle">查看学生的学习情况与AI分析总结</p>

    <!-- 数据概览卡片 -->
    <div class="stats-overview">
      <div class="stat-card total">
        <h3>总提问数</h3>
        <div class="stat-number">{{ stats.total_questions || 0 }}</div>
      </div>
      <div class="stat-card students">
        <h3>活跃学生数</h3>
        <div class="stat-number">{{ Object.keys(stats.questions_by_student || {}).length }}</div>
      </div>
    </div>

    <!-- AI总结报告 -->
    <div class="summary-section" v-if="stats.summary">
      <h2>📊 AI 学习情况总结</h2>
      <div class="summary-content">
        {{ stats.summary }}
      </div>
    </div>

    <!-- 学生提问详情 -->
    <div class="details-section">
      <h2>👨‍🎓 学生提问详情</h2>
      <div v-if="!stats.questions_by_student || Object.keys(stats.questions_by_student).length === 0" class="empty-state">
        暂无学生提问数据
      </div>
      <div v-else class="students-list">
        <div v-for="(questions, studentName) in stats.questions_by_student" :key="studentName" class="student-card">
          <h3>{{ studentName }}</h3>
          <div class="question-count">提问次数：{{ questions.length }}</div>
          <div class="questions-list">
            <div v-for="(q, index) in questions" :key="index" class="question-item">
              <strong>Q{{ index + 1 }}:</strong> {{ q }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载和错误状态 -->
    <div v-if="loading" class="loading">数据加载中...</div>
    <div v-if="error" class="error-message">{{ error }}</div>

    <button @click="logout" class="logout-btn">退出登录</button>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'TeacherView',
  setup() {
    const router = useRouter()
    const stats = ref({})
    const loading = ref(false)
    const error = ref('')

    // 获取统计数据
    const fetchStats = async () => {
      loading.value = true
      error.value = ''
      try {
        const response = await axios.get('/api/questions/stats')
        stats.value = response.data
        console.log('获取统计数据成功:', stats.value)
      } catch (err) {
        console.error('获取数据失败:', err)
        error.value = err.response?.data?.error || '获取数据失败，请检查网络连接'
      } finally {
        loading.value = false
      }
    }

    // 退出登录
    const logout = () => {
      // 可以在这里调用后端的 /api/logout
      router.push('/login')
    }

    // 页面加载时获取数据
    onMounted(() => {
      fetchStats()
    })

    return {
      stats,
      loading,
      error,
      logout
    }
  }
}
</script>

<style scoped>
.teacher-container {
  padding: 30px;
  max-width: 1000px;
  margin: 0 auto;
}

h1 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.subtitle {
  color: #7f8c8d;
  margin-bottom: 30px;
}

.stats-overview {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  flex: 1;
  background: white;
  padding: 25px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.stat-card.total {
  border-top: 4px solid #3498db;
}

.stat-card.students {
  border-top: 4px solid #2ecc71;
}

.stat-card h3 {
  color: #555;
  margin-bottom: 10px;
  font-size: 16px;
}

.stat-number {
  font-size: 36px;
  font-weight: bold;
  color: #2c3e50;
}

.summary-section, .details-section {
  background: white;
  padding: 25px;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 30px;
}

.summary-section h2, .details-section h2 {
  color: #2c3e50;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #eee;
}

.summary-content {
  line-height: 1.6;
  color: #333;
  font-size: 16px;
  white-space: pre-wrap; /* 保留AI总结的格式 */
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #95a5a6;
  font-style: italic;
}

.students-list {
  display: grid;
  gap: 20px;
}

.student-card {
  padding: 20px;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  background: #f8f9fa;
}

.student-card h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.question-count {
  color: #e67e22;
  font-weight: 500;
  margin-bottom: 15px;
}

.questions-list {
  margin-left: 10px;
}

.question-item {
  padding: 8px 0;
  border-bottom: 1px dashed #eee;
  color: #555;
  line-height: 1.5;
}

.question-item:last-child {
  border-bottom: none;
}

.loading, .error-message {
  text-align: center;
  padding: 20px;
  margin: 20px 0;
  border-radius: 8px;
}

.loading {
  background: #e3f2fd;
  color: #1976d2;
}

.error-message {
  background: #ffebee;
  color: #c62828;
}

.logout-btn {
  display: block;
  margin: 30px auto 0;
  padding: 10px 25px;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.2s;
}

.logout-btn:hover {
  transform: translateY(-2px);
}
</style>