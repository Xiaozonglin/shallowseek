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
    <!-- 权威答案管理 -->
    <div class="auth-management">
      <h2>📝 权威答案管理</h2>
      <button @click="fetchPendingQuestions" class="refresh-btn">刷新问题列表</button>

      <div v-if="pendingQuestions.length === 0" class="empty">暂无待处理问题。</div>
      <div v-else class="question-list">
        <div v-for="q in pendingQuestions" :key="q.id" class="question-card">
          <h4>来自: {{ q.student_name }}</h4>
          <p><strong>问题:</strong> {{ q.content }}</p>
          <p><strong>AI初步答案:</strong> {{ q.ai_answer }}</p>

          <div v-if="q.authoritative_answer">
            <p><strong>✅ 已设权威答案:</strong> {{ q.authoritative_answer }}</p>
          </div>
          <div v-else class="auth-form">
            <textarea v-model="q.newAuthAnswer" placeholder="在此输入您的权威答案..."></textarea>
            <button @click="submitAuthAnswer(q)">提交为权威答案</button>
          </div>
        </div>
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
    <!-- 在合适位置加入留言管理模块 -->
    <div class="message-management">
      <h2>💬 学生留言与回复</h2>
      <div v-for="msg in messages" :key="msg.id" class="message-card">
        <p><strong>{{ msg.sender }} 留言:</strong> {{ msg.content }}</p>
        <small>{{ msg.timestamp }}</small>

        <div v-if="msg.reply_content">
          <p><strong>您的回复:</strong> {{ msg.reply_content }}</p>
        </div>
        <div v-else>
          <textarea v-model="msg.newReply" placeholder="输入回复内容..."></textarea>
          <button @click="replyToMessage(msg)">发送回复</button>
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
    const pendingQuestions = ref([])
    const messages = ref([])
    const loading = ref(false)
    const error = ref('')

    // 1. 获取数据统计
    const fetchStats = async () => {
      loading.value = true
      error.value = ''
      try {
        const response = await axios.get('/api/questions/stats')
        stats.value = response.data
      } catch (err) {
        console.error('获取数据失败:', err)
        error.value = err.response?.data?.error || '获取数据失败'
      } finally {
        loading.value = false
      }
    }

    // 2. 获取待处理问题
    const fetchPendingQuestions = async () => {
      try {
        const response = await axios.get('/api/questions/pending')
        pendingQuestions.value = response.data.map(q => ({ ...q, newAuthAnswer: '' }))
      } catch (err) {
        console.error('获取问题列表失败:', err)
        alert('获取问题列表失败')
      }
    }

    // 3. 提交权威答案
    const submitAuthAnswer = async (question) => {
      if (!question.newAuthAnswer.trim()) {
        alert('请输入答案内容')
        return
      }
      try {
        await axios.post(`/api/questions/${question.id}/authoritative`, {
          answer: question.newAuthAnswer
        })
        alert('权威答案已提交！')
        question.authoritative_answer = question.newAuthAnswer
        question.newAuthAnswer = ''
      } catch (err) {
        console.error('提交失败:', err)
        alert('提交失败')
      }
    }

    // 4. 获取留言
    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data.map(m => ({ ...m, newReply: '' }))
      } catch (err) {
        console.error('获取留言失败:', err)
      }
    }

    // 5. 回复留言
    const replyToMessage = async (msg) => {
      try {
        await axios.post(`/api/messages/${msg.id}/reply`, {
          reply_content: msg.newReply
        })
        alert('回复成功！')
        msg.reply_content = msg.newReply
        msg.newReply = ''
      } catch (err) {
        console.error('回复失败:', err)
        alert('回复失败')
      }
    }

    // 6. 退出登录
    const logout = async () => {
      try {
        // 发送登出请求到后端
        await axios.post('/api/logout')
        console.log('老师登出成功')
      } catch (error) {
        console.error('老师登出失败:', error)
      } finally {
        // 无论成功失败，都跳转到登录页
        router.push('/login')
      }
    }
    // 页面加载时，一次性获取所有初始数据
    onMounted(() => {
      fetchStats()
      fetchPendingQuestions()
      fetchMessages()
    })

    // 必须返回所有模板中使用的变量和方法
    return {
      stats,
      pendingQuestions,
      messages,
      loading,
      error,
      fetchPendingQuestions,
      submitAuthAnswer,
      fetchMessages,
      replyToMessage,
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