<template>
  <div class="quantum-control-center">
    <!-- 神经连接状态栏 -->
    <div class="neural-status-bar">
      <div class="status-left">
        <div class="data-stream">
          <div class="stream-dot" v-for="n in 5" :key="n" :style="streamStyle(n)"></div>
        </div>
        <span class="status-text">神经网络控制中心</span>
        <div class="live-indicator">
          <span class="indicator-dot"></span>
          <span class="indicator-text">实时数据流</span>
        </div>
      </div>
      <div class="status-right">
        <div class="data-refresh">
          <button class="refresh-btn" @click="fetchAllData">
            <span class="refresh-icon">🔄</span>
            <span class="refresh-text">同步数据</span>
            <div class="refresh-wave"></div>
          </button>
        </div>
        <div class="user-node">
          <div class="node-avatar">
            <div class="avatar-core"></div>
            <div class="avatar-rings">
              <div class="ring" v-for="i in 3" :key="i"></div>
            </div>
          </div>
          <div class="node-info">
            <span class="node-name">导师</span>
            <span class="node-role">管理员节点</span>
          </div>
        </div>
        <button class="disconnect-btn" @click="logout">
          <span class="btn-label">断开连接</span>
          <div class="disconnect-wave"></div>
        </button>
      </div>
    </div>

    <!-- 主控制区 -->
    <div class="control-grid">
      <!-- 左侧：量子统计仪表 -->
      <div class="left-panel">
        <!-- 数据概览 -->
        <div class="quantum-stats">
          <h2 class="panel-title">
            <span class="title-icon">📊</span>
            量子数据概览
          </h2>
          <div class="stats-grid">
            <div class="stat-card quantum">
              <div class="stat-icon">⚛️</div>
              <div class="stat-content">
                <div class="stat-value">{{ stats.total_questions || 0 }}</div>
                <div class="stat-label">总提问数</div>
              </div>
              <div class="stat-trend">+{{ Math.floor(Math.random() * 20) + 5 }}%</div>
              <div class="stat-wave"></div>
            </div>
            
            <div class="stat-card neural">
              <div class="stat-icon">🧠</div>
              <div class="stat-content">
                <div class="stat-value">{{ Object.keys(stats.questions_by_student || {}).length }}</div>
                <div class="stat-label">活跃节点</div>
              </div>
              <div class="stat-trend positive">+{{ Math.floor(Math.random() * 15) + 3 }}%</div>
              <div class="stat-wave"></div>
            </div>
            
            <div class="stat-card knowledge">
              <div class="stat-icon">📚</div>
              <div class="stat-content">
                <div class="stat-value">{{ pendingQuestions.length }}</div>
                <div class="stat-label">待处理问题</div>
              </div>
              <div class="stat-wave alert" v-if="pendingQuestions.length > 0"></div>
            </div>
          </div>
        </div>

        <!-- AI神经网络总结 -->
        <div class="neural-summary" v-if="stats.summary">
          <div class="summary-header">
            <h3 class="summary-title">
              <span class="title-icon">🤖</span>
              AI 神经网络分析
            </h3>
            <div class="summary-meta">
              <span class="meta-item">实时更新</span>
              <span class="meta-divider">•</span>
              <span class="meta-item">{{ new Date().toLocaleTimeString() }}</span>
            </div>
          </div>
          <div class="summary-content">
            <div class="summary-text">
              {{ stats.summary }}
            </div>
            <div class="summary-wave">
              <div class="wave" v-for="n in 20" :key="n"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：学生神经网络 -->
      <div class="center-panel">
        <!-- 学生神经网络图 -->
        <div class="neural-network">
          <div class="network-header">
            <h3 class="network-title">
              <span class="title-icon">🌐</span>
              学生神经网络
            </h3>
            <div class="network-controls">
              <button class="control-btn" @click="toggleViewMode">
                <span class="control-icon">{{ viewMode === 'grid' ? '🔲' : '⏺️' }}</span>
                <span class="control-text">{{ viewMode === 'grid' ? '网格视图' : '星图视图' }}</span>
              </button>
            </div>
          </div>
          
          <div class="network-container" :class="viewMode">
            <div v-if="!stats.questions_by_student || Object.keys(stats.questions_by_student).length === 0" 
                 class="empty-network">
              <div class="empty-core">
                <div class="core-pulse"></div>
              </div>
              <div class="empty-text">等待神经连接...</div>
              <div class="empty-subtext">学生节点即将接入网络</div>
            </div>
            
            <div v-else class="network-graph">
              <!-- 中心节点 -->
              <div class="center-node">
                <div class="node-core">
                  <div class="core-glow"></div>
                  <span class="core-text">AI</span>
                </div>
              </div>
              
              <!-- 学生节点 -->
              <div v-for="(questions, studentName, index) in stats.questions_by_student" 
                   :key="studentName" 
                   class="student-node"
                   :style="nodePosition(index)">
                <div class="node-orbital">
                  <div class="orbital-path"></div>
                </div>
                <div class="node-container" @click="selectStudent(studentName)">
                  <div class="node-visual">
                    <div class="node-dot"></div>
                    <div class="node-rings">
                      <div class="ring" v-for="i in 2" :key="i"></div>
                    </div>
                  </div>
                  <div class="node-info">
                    <div class="node-name">{{ studentName }}</div>
                    <div class="node-stats">{{ questions.length }} 次提问</div>
                  </div>
                  <div class="node-activity" :class="{ active: Math.random() > 0.5 }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 权威答案管理 -->
        <div class="authority-management">
          <div class="management-header">
            <h3 class="management-title">
              <span class="title-icon">📝</span>
              权威答案管理
            </h3>
            <div class="management-actions">
              <button class="action-btn refresh" @click="fetchPendingQuestions">
                <span class="action-icon">🔄</span>
                <span class="action-text">刷新</span>
              </button>
              <div class="pending-count" v-if="pendingQuestions.length > 0">
                <span class="count-badge">{{ pendingQuestions.length }}</span>
                <span class="count-text">待处理</span>
              </div>
            </div>
          </div>
          
          <div v-if="pendingQuestions.length === 0" class="empty-questions">
            <div class="empty-icon">✅</div>
            <div class="empty-text">暂无待处理问题</div>
            <div class="empty-subtext">所有AI答案均已审核</div>
          </div>
          
          <div v-else class="questions-hologram">
            <div v-for="q in pendingQuestions" :key="q.id" class="question-hologram">
              <div class="hologram-header">
                <div class="student-info">
                  <div class="student-avatar">👨‍🎓</div>
                  <div class="student-details">
                    <div class="student-name">{{ q.student_name }}</div>
                    <div class="question-time">提问时间: {{ formatTime(q.created_at) }}</div>
                  </div>
                </div>
                <div class="question-id">#{{ q.id }}</div>
              </div>
              
              <div class="hologram-content">
                <div class="content-section">
                  <h4 class="section-title">
                    <span class="title-icon">❓</span>
                    问题内容
                  </h4>
                  <div class="section-content">{{ q.content }}</div>
                </div>
                
                <div class="content-section">
                  <h4 class="section-title">
                    <span class="title-icon">🤖</span>
                    AI初步答案
                  </h4>
                  <div class="section-content ai-answer">{{ q.ai_answer }}</div>
                </div>
                
                <div v-if="q.authoritative_answer" class="content-section authoritative">
                  <h4 class="section-title">
                    <span class="title-icon">✅</span>
                    已设权威答案
                  </h4>
                  <div class="section-content">{{ q.authoritative_answer }}</div>
                </div>
                
                <div v-else class="content-section edit">
                  <h4 class="section-title">
                    <span class="title-icon">✏️</span>
                    设置权威答案
                  </h4>
                  <div class="edit-container">
                    <textarea 
                      v-model="q.newAuthAnswer" 
                      placeholder="在此输入权威答案..."
                      rows="4"
                      class="auth-textarea"
                      :class="{ focused: q.textareaFocused }"
                      @focus="q.textareaFocused = true"
                      @blur="q.textareaFocused = false"
                    ></textarea>
                    <div class="edit-actions">
                      <button 
                        class="submit-auth-btn"
                        @click="submitAuthAnswer(q)"
                        :disabled="!q.newAuthAnswer.trim() || q.submitting"
                      >
                        <span class="btn-text">{{ q.submitting ? '提交中...' : '设为权威' }}</span>
                        <div class="btn-glow" v-if="q.newAuthAnswer.trim() && !q.submitting"></div>
                      </button>
                      <button class="skip-btn" @click="skipQuestion(q)">
                        <span class="btn-text">跳过</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：通讯与监控 -->
      <div class="right-panel">
        <!-- 实时通讯 -->
        <div class="realtime-communication">
          <div class="comms-header">
            <h3 class="comms-title">
              <span class="title-icon">💬</span>
              实时通讯
            </h3>
            <div class="comms-status">
              <div class="status-dot online"></div>
              <span class="status-text">在线</span>
            </div>
          </div>
          
          <div class="messages-hologram">
            <div v-if="messages.length === 0" class="empty-messages">
              <div class="empty-icon">📭</div>
              <div class="empty-text">暂无新消息</div>
            </div>
            
            <div v-else class="messages-list">
              <div v-for="msg in messages.slice(0, 3)" :key="msg.id" class="message-bubble">
                <div class="message-header">
                  <div class="sender-info">
                    <div class="sender-avatar">👨‍🎓</div>
                    <div class="sender-details">
                      <div class="sender-name">{{ msg.sender }}</div>
                      <div class="message-time">{{ msg.timestamp }}</div>
                    </div>
                  </div>
                  <div class="message-status" v-if="!msg.reply_content">待回复</div>
                </div>
                
                <div class="message-content">{{ msg.content }}</div>
                
                <div v-if="msg.reply_content" class="reply-section">
                  <div class="reply-header">您的回复：</div>
                  <div class="reply-content">{{ msg.reply_content }}</div>
                </div>
                
                <div v-else class="reply-input">
                  <textarea 
                    v-model="msg.newReply" 
                    placeholder="输入回复内容..."
                    rows="3"
                    class="reply-textarea"
                  ></textarea>
                  <div class="reply-actions">
                    <button 
                      class="reply-btn"
                      @click="replyToMessage(msg)"
                      :disabled="!msg.newReply.trim() || msg.replying"
                    >
                      <span class="btn-text">{{ msg.replying ? '发送中...' : '发送' }}</span>
                      <div class="btn-wave" v-if="msg.newReply.trim() && !msg.replying"></div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="view-all-link">
            <a href="#" class="quantum-link" @click.prevent="viewAllMessages">
              <span class="link-text">查看全部通讯</span>
              <span class="link-arrow">↗</span>
            </a>
          </div>
        </div>

        <!-- 系统监控 -->
        <div class="system-monitor">
          <div class="monitor-header">
            <h3 class="monitor-title">
              <span class="title-icon">📈</span>
              系统监控
            </h3>
            <div class="monitor-refresh">
              <button class="refresh-btn mini" @click="fetchAllData">
                <span class="refresh-icon">↻</span>
              </button>
            </div>
          </div>
          
          <div class="monitor-metrics">
            <div class="metric-item">
              <div class="metric-label">AI响应时间</div>
              <div class="metric-value">28ms</div>
              <div class="metric-bar">
                <div class="bar-fill" style="width: 70%"></div>
              </div>
            </div>
            
            <div class="metric-item">
              <div class="metric-label">知识库查询</div>
              <div class="metric-value">94%</div>
              <div class="metric-bar">
                <div class="bar-fill" style="width: 94%"></div>
              </div>
            </div>
            
            <div class="metric-item">
              <div class="metric-label">网络延迟</div>
              <div class="metric-value">12ms</div>
              <div class="metric-bar">
                <div class="bar-fill" style="width: 90%"></div>
              </div>
            </div>
          </div>
          
          <div class="monitor-footer">
            <div class="status-item">
              <div class="status-icon">🟢</div>
              <div class="status-text">系统正常</div>
            </div>
            <div class="update-time">最后更新: {{ new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="quantum-loader">
      <div class="loader-ring"></div>
      <div class="loader-text">量子数据传输中...</div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="quantum-alert error">
      <div class="alert-icon">⚠️</div>
      <div class="alert-content">
        <div class="alert-title">系统错误</div>
        <div class="alert-message">{{ error }}</div>
      </div>
      <div class="alert-close" @click="error = ''">×</div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'QuantumControlCenter',
  setup() {
    const router = useRouter()
    
    // 数据状态
    const stats = ref({})
    const pendingQuestions = ref([])
    const messages = ref([])
    const loading = ref(false)
    const error = ref('')
    const viewMode = ref('star')
    const selectedStudent = ref(null)
    
    // 流式数据点样式
    const streamStyle = (n) => {
      return {
        animationDelay: `${n * 0.2}s`,
        left: `${n * 20}%`
      }
    }
    
    // 格式化时间
    const formatTime = (timestamp) => {
      if (!timestamp) return '刚刚'
      const date = new Date(timestamp)
      return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
    }
    
    // 节点位置计算
    const nodePosition = (index) => {
      const total = Object.keys(stats.value.questions_by_student || {}).length
      const angle = (index / total) * Math.PI * 2
      const radius = 150
      return {
        transform: `translate(calc(50% + ${Math.cos(angle) * radius}px), calc(50% + ${Math.sin(angle) * radius}px))`
      }
    }
    
    // 获取所有数据
    const fetchAllData = async () => {
      loading.value = true
      error.value = ''
      try {
        await Promise.all([
          fetchStats(),
          fetchPendingQuestions(),
          fetchMessages()
        ])
      } catch (err) {
        console.error('数据同步失败:', err)
        error.value = '数据同步失败'
      } finally {
        loading.value = false
      }
    }
    
    // 获取统计数据
    const fetchStats = async () => {
      try {
        const response = await axios.get('/api/questions/stats')
        stats.value = response.data
      } catch (err) {
        console.error('获取统计数据失败:', err)
        throw err
      }
    }
    
    // 获取待处理问题
    const fetchPendingQuestions = async () => {
      try {
        const response = await axios.get('/api/questions/pending')
        pendingQuestions.value = response.data.map(q => ({ 
          ...q, 
          newAuthAnswer: '',
          textareaFocused: false,
          submitting: false
        }))
      } catch (err) {
        console.error('获取问题列表失败:', err)
        throw err
      }
    }
    
    // 提交权威答案
    const submitAuthAnswer = async (question) => {
      if (!question.newAuthAnswer.trim()) return
      
      question.submitting = true
      try {
        await axios.post(`/api/questions/${question.id}/authoritative`, {
          answer: question.newAuthAnswer
        })
        
        question.authoritative_answer = question.newAuthAnswer
        question.newAuthAnswer = ''
        
        // 从待处理列表中移除
        pendingQuestions.value = pendingQuestions.value.filter(q => q.id !== question.id)
        
      } catch (err) {
        console.error('提交失败:', err)
        error.value = '提交失败'
      } finally {
        question.submitting = false
      }
    }
    
    // 跳过问题
    const skipQuestion = async (question) => {
      try {
        await axios.post(`/api/questions/${question.id}/skip`)
        
      } catch (err) {
        console.error('跳过失败:', err)
        error.value = '跳过失败'
      }
    }
    
    // 获取留言
    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data.map(m => ({ 
          ...m, 
          newReply: '',
          replying: false
        }))
      } catch (err) {
        console.error('获取留言失败:', err)
        throw err
      }
    }
    
    // 回复留言
    const replyToMessage = async (msg) => {
      if (!msg.newReply.trim()) return
      
      msg.replying = true
      try {
        await axios.post(`/api/messages/${msg.id}/reply`, {
          reply_content: msg.newReply
        })
        
        msg.reply_content = msg.newReply
        msg.newReply = ''
        
      } catch (err) {
        console.error('回复失败:', err)
        error.value = '回复失败'
      } finally {
        msg.replying = false
      }
    }
    
    // 查看全部消息
    const viewAllMessages = () => {
      // 可以在这里实现查看全部消息的逻辑
      console.log('查看全部消息')
    }
    
    // 选择学生
    const selectStudent = (studentName) => {
      selectedStudent.value = studentName
      // 可以在这里实现查看学生详情的逻辑
      console.log('选择学生:', studentName)
    }
    
    // 切换视图模式
    const toggleViewMode = () => {
      viewMode.value = viewMode.value === 'star' ? 'grid' : 'star'
    }
    
    // 退出登录
    const logout = async () => {
      try {
        await axios.post('/api/logout')
        router.push('/login')
      } catch (err) {
        console.error('登出失败:', err)
        router.push('/login')
      }
    }
    
    // 页面加载时获取数据
    onMounted(() => {
      fetchAllData()
    })
    
    return {
      stats,
      pendingQuestions,
      messages,
      loading,
      error,
      viewMode,
      selectedStudent,
      streamStyle,
      formatTime,
      nodePosition,
      fetchAllData,
      submitAuthAnswer,
      skipQuestion,
      replyToMessage,
      viewAllMessages,
      selectStudent,
      toggleViewMode,
      logout
    }
  }
}
</script>

<style scoped></style>
.quantum-control-center {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 0% 0%, #0a0a1a 0%, #000 50%),
    radial-gradient(ellipse at 100% 100%, #001122 0%, transparent 70%);
  color: #f8fafc;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  position: relative;
  overflow-x: hidden;
}

.neural-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  background: rgba(10, 10, 20, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  position: relative;
  z-index: 100;
}

.neural-status-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(0, 255, 255, 0.5), 
    transparent
  );
  animation: scan 3s linear infinite;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.data-stream {
  position: relative;
  width: 120px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.stream-dot {
  position: absolute;
  top: 0;
  width: 4px;
  height: 4px;
  background: #00ffff;
  border-radius: 50%;
  filter: blur(1px);
  animation: streamFlow 1.5s linear infinite;
}

.status-text {
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(0, 255, 128, 0.1);
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 20px;
}

.indicator-dot {
  width: 6px;
  height: 6px;
  background: #00ff80;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.indicator-text {
  color: #00ff80;
  font-size: 11px;
  font-weight: 500;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.data-refresh {
  position: relative;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: rgba(0, 150, 255, 0.1);
  border: 1px solid rgba(0, 150, 255, 0.2);
  border-radius: 20px;
  color: #00ffff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.refresh-btn:hover {
  background: rgba(0, 150, 255, 0.2);
  border-color: rgba(0, 150, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 150, 255, 0.3);
  transform: translateY(-2px);
}

.refresh-wave {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(0, 255, 255, 0.2), 
    transparent
  );
  transform: translateX(-100%);
  animation: slideGlow 2s infinite;
}

.user-node {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.node-avatar {
  position: relative;
  width: 36px;
  height: 36px;
}

.avatar-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: #00ffff;
  border-radius: 50%;
  z-index: 2;
}

.avatar-rings {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.avatar-rings .ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 50%;
  animation: orbit 4s linear infinite;
}

.avatar-rings .ring:nth-child(1) {
  width: 36px;
  height: 36px;
  animation-delay: 0s;
}

.avatar-rings .ring:nth-child(2) {
  width: 24px;
  height: 24px;
  animation-delay: -1.33s;
}

.avatar-rings .ring:nth-child(3) {
  width: 12px;
  height: 12px;
  animation-delay: -2.66s;
}

.node-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-name {
  color: #f8fafc;
  font-size: 12px;
  font-weight: 600;
}

.node-role {
  color: #00ffff;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.disconnect-btn {
  position: relative;
  padding: 8px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
}

.disconnect-btn:hover {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.3);
  color: #ff6b6b;
}

.disconnect-wave {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(255, 255, 255, 0.1), 
    transparent
  );
  transform: translateX(-100%);
  animation: slideGlow 3s infinite;
}

.control-grid {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 20px;
  padding: 20px;
  max-width: 1800px;
  margin: 0 auto;
}

.left-panel, .center-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quantum-stats {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f8fafc;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 20px;
}

.title-icon {
  font-size: 24px;
}

.stats-grid {
  display: grid;
  gap: 12px;
}

.stat-card {
  position: relative;
  padding: 20px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  gap: 15px;
  overflow: hidden;
  transition: all 0.3s;
}

.stat-card:hover {
  background: rgba(30, 41, 59, 0.5);
  border-color: rgba(0, 255, 255, 0.2);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  color: #f8fafc;
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
}

.stat-trend {
  color: #00ff80;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  background: rgba(0, 255, 128, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 128, 0.2);
}

.stat-trend.positive {
  color: #00ff80;
  background: rgba(0, 255, 128, 0.1);
  border-color: rgba(0, 255, 128, 0.2);
}

.stat-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent, 
    #00ffff, 
    transparent
  );
  animation: streamFlow 2s infinite;
}

.stat-wave.alert {
  background: linear-gradient(90deg, 
    transparent, 
    #ff6b6b, 
    transparent
  );
}

.neural-summary {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  flex: 1;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f8fafc;
  font-size: 18px;
  font-weight: 600;
}

.summary-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.meta-divider {
  color: #475569;
}

.summary-content {
  position: relative;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 255, 0.1);
  min-height: 150px;
}

.summary-text {
  font-size: 13px;
  line-height: 1.6;
  color: #cbd5e1;
  position: relative;
  z-index: 2;
}

.summary-wave {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.summary-wave .wave {
  position: absolute;
  bottom: 0;
  height: 2px;
  background: rgba(0, 255, 255, 0.2);
  animation: waveFlow 3s infinite;
}

@keyframes waveFlow {
  0% { 
    left: -100%; 
    width: 20%;
  }
  50% { 
    left: 40%; 
    width: 40%;
  }
  100% { 
    left: 100%; 
    width: 20%;
  }
}

.neural-network, .authority-management, .realtime-communication, .system-monitor {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.network-header, .management-header, .comms-header, .monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.network-title, .management-title, .comms-title, .monitor-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f8fafc;
  font-size: 18px;
  font-weight: 600;
}

.control-btn, .action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.control-btn:hover, .action-btn:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.2);
  color: #00ffff;
}

.control-btn.refresh:hover {
  background: rgba(0, 150, 255, 0.1);
  border-color: rgba(0, 150, 255, 0.2);
  color: #00ffff;
}

.network-container {
  height: 300px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
}

.empty-network {
  text-align: center;
  color: #64748b;
  padding: 40px 20px;
}

.empty-core {
  position: relative;
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
}

.core-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: #00ffff;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.empty-subtext {
  font-size: 12px;
  color: #475569;
}

.network-graph {
  position: relative;
  width: 100%;
  height: 100%;
}

.center-node {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
}

.node-core {
  position: relative;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(0, 255, 255, 0.3);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s;
}

.node-core:hover {
  transform: scale(1.1);
  box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
}

.core-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle, rgba(0, 255, 255, 0.2) 0%, transparent 70%);
  filter: blur(10px);
  border-radius: 50%;
}

.core-text {
  color: #00ffff;
  font-size: 16px;
  font-weight: 700;
  position: relative;
  z-index: 2;
}

.student-node {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 5;
}

.node-orbital {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  height: 300px;
  border: 1px solid rgba(0, 255, 255, 0.1);
  border-radius: 50%;
}

.orbital-path {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  animation: orbitSpin 20s linear infinite;
}

.node-container {
  position: relative;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  min-width: 120px;
  transform: translate(-50%, -50%);
}

.node-container:hover {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(0, 255, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
  transform: translate(-50%, -50%) scale(1.05);
}

.node-visual {
  position: relative;
  width: 40px;
  height: 40px;
}

.node-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: #00ffff;
  border-radius: 50%;
  z-index: 2;
}

.node-rings {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.node-rings .ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 50%;
  animation: orbit 3s linear infinite;
}

.node-rings .ring:nth-child(1) {
  width: 40px;
  height: 40px;
  animation-delay: 0s;
}

.node-rings .ring:nth-child(2) {
  width: 30px;
  height: 30px;
  animation-delay: -1s;
}

.node-info {
  text-align: center;
}

.node-name {
  color: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 2px;
}

.node-stats {
  color: #94a3b8;
  font-size: 10px;
}

.node-activity {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 6px;
  height: 6px;
  background: #94a3b8;
  border-radius: 50%;
}

.node-activity.active {
  background: #00ff80;
  box-shadow: 0 0 6px #00ff80;
  animation: blink 1s infinite;
}

.management-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pending-count {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.2);
  border-radius: 20px;
}

.count-badge {
  color: #ff6b6b;
  font-size: 12px;
  font-weight: 700;
}

.count-text {
  color: #ff6b6b;
  font-size: 10px;
  font-weight: 500;
}

.empty-questions {
  text-align: center;
  padding: 40px 20px;
  color: #64748b;
}

.empty-questions .empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-questions .empty-text {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.empty-questions .empty-subtext {
  font-size: 12px;
  color: #475569;
}

.questions-hologram {
  max-height: 400px;
  overflow-y: auto;
  padding-right: 10px;
}

.questions-hologram::-webkit-scrollbar {
  width: 4px;
}

.questions-hologram::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.questions-hologram::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 255, 0.3);
  border-radius: 2px;
}

.question-hologram {
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.question-hologram:hover {
  background: rgba(0, 0, 0, 0.3);
  border-color: rgba(0, 255, 255, 0.1);
  transform: translateY(-2px);
}

.hologram-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.student-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.student-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 50%;
  font-size: 20px;
}

.student-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.student-name {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
}

.question-time {
  color: #94a3b8;
  font-size: 10px;
  letter-spacing: 0.5px;
}

.question-id {
  color: #00ffff;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 20px;
}

.hologram-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.content-section {
  padding: 15px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.content-section.authoritative {
  border-color: rgba(0, 255, 128, 0.2);
  background: rgba(0, 255, 128, 0.05);
}

.content-section.edit {
  border-color: rgba(0, 255, 255, 0.2);
  background: rgba(0, 255, 255, 0.05);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.section-content {
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.5;
}

.ai-answer {
  color: #94a3b8;
  font-style: italic;
  border-left: 3px solid rgba(0, 255, 255, 0.3);
  padding-left: 12px;
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: 4px;
}

.auth-textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #f8fafc;
  font-size: 12px;
  font-family: inherit;
  resize: vertical;
  min-height: 100px;
  transition: all 0.3s;
  outline: none;
}

.auth-textarea:focus {
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
}

.edit-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-actions {
  display: flex;
  gap: 10px;
}

.submit-auth-btn, .skip-btn {
  flex: 1;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.submit-auth-btn {
  background: linear-gradient(135deg, #00ffff, #0088ff);
  color: #0f172a;
}

.submit-auth-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.submit-auth-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.skip-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.skip-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  transform: translateY(-2px);
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

.comms-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0, 255, 128, 0.1);
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 20px;
}

.status-dot.online {
  width: 6px;
  height: 6px;
  background: #00ff80;
  border-radius: 50%;
  animation: connectedPulse 2s infinite;
}

.messages-hologram {
  height: 300px;
  overflow-y: auto;
  padding-right: 10px;
}

.messages-hologram::-webkit-scrollbar {
  width: 4px;
}

.messages-hologram::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.messages-hologram::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 255, 0.3);
  border-radius: 2px;
}

.empty-messages {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}

.empty-messages .empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-messages .empty-text {
  font-size: 14px;
  font-weight: 500;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-bubble {
  padding: 15px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.sender-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sender-avatar {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 50%;
  font-size: 16px;
}

.sender-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sender-name {
  color: #f8fafc;
  font-size: 12px;
  font-weight: 600;
}

.message-time {
  color: #94a3b8;
  font-size: 10px;
}

.message-status {
  color: #ffa726;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(255, 167, 38, 0.1);
  border: 1px solid rgba(255, 167, 38, 0.2);
  border-radius: 20px;
}

.message-content {
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 10px;
  padding: 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.reply-section {
  padding: 10px;
  background: rgba(0, 255, 128, 0.05);
  border: 1px solid rgba(0, 255, 128, 0.1);
  border-radius: 8px;
  margin-top: 10px;
}

.reply-header {
  color: #00ff80;
  font-size: 10px;
  font-weight: 600;
  margin-bottom: 4px;
}

.reply-content {
  color: #94f8d1;
  font-size: 12px;
  line-height: 1.5;
}

.reply-input {
  margin-top: 10px;
}

.reply-textarea {
  width: 100%;
  padding: 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #f8fafc;
  font-size: 12px;
  font-family: inherit;
  resize: vertical;
  min-height: 60px;
  margin-bottom: 10px;
  transition: all 0.3s;
  outline: none;
}

.reply-textarea:focus {
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
}

.reply-actions {
  display: flex;
  justify-content: flex-end;
}

.reply-btn {
  padding: 8px 20px;
  background: linear-gradient(135deg, #00ffff, #0088ff);
  border: none;
  border-radius: 20px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.reply-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.reply-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-wave {
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

.view-all-link {
  margin-top: 15px;
  text-align: center;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.quantum-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #00ffff;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.2);
}

.quantum-link:hover {
  background: rgba(0, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}

.link-arrow {
  transition: transform 0.3s;
}

.quantum-link:hover .link-arrow {
  transform: translate(2px, -2px);
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.monitor-refresh .refresh-btn {
  padding: 6px;
  min-width: 32px;
  justify-content: center;
}

.monitor-refresh .refresh-btn .refresh-icon {
  margin: 0;
  font-size: 12px;
}

.monitor-metrics {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.3s;
}

.metric-item:hover {
  background: rgba(0, 0, 0, 0.3);
  border-color: rgba(0, 255, 255, 0.1);
  transform: translateX(4px);
}

.metric-label {
  flex: 1;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 500;
}

.metric-value {
  color: #00ffff;
  font-size: 16px;
  font-weight: 700;
  min-width: 40px;
  text-align: right;
}

.metric-bar {
  width: 60px;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ffff, #0088ff);
  border-radius: 3px;
  transition: width 1s ease-in-out;
}

.monitor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0, 255, 128, 0.1);
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 20px;
}

.status-icon {
  font-size: 6px;
}

.status-text {
  color: #00ff80;
  font-size: 10px;
  font-weight: 500;
}

.update-time {
  color: #94a3b8;
  font-size: 10px;
  letter-spacing: 0.5px;
}

.quantum-loader {
  position: fixed;
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
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
}

.loader-ring {
  width: 60px;
  height: 60px;
  border: 2px solid rgba(0, 255, 255, 0.3);
  border-top-color: #00ffff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

.loader-text {
  color: #00ffff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  animation: pulse 2s infinite;
}

.quantum-alert {
  position: fixed;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  max-width: 400px;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  z-index: 1000;
  animation: slideInRight 0.3s ease-out;
}

.quantum-alert.error {
  background: rgba(220, 38, 38, 0.1);
  border-color: rgba(220, 38, 38, 0.2);
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

.alert-message {
  color: #fecaca;
  font-size: 11px;
  line-height: 1.4;
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

/* 动画定义 */
@keyframes scan {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes streamFlow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes pulse {
  0%, 100% { 
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 255, 255, 0.4);
  }
  50% { 
    opacity: 0.5;
    box-shadow: 0 0 0 10px rgba(0, 255, 255, 0);
  }
}

@keyframes slideGlow {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
  100% { transform: translateX(100%); }
}

@keyframes orbit {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes orbitSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes connectedPulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(0, 255, 128, 0.4);
  }
  50% { 
    box-shadow: 0 0 0 6px rgba(0, 255, 128, 0);
  }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

@keyframes waveFlow {
  0% { 
    left: -100%; 
    width: 20%;
  }
  50% { 
    left: 40%; 
    width: 40%;
  }
  100% { 
    left: 100%; 
    width: 20%;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .control-grid {
    grid-template-columns: 1fr 2fr 1fr;
  }
}

@media (max-width: 1200px) {
  .control-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .right-panel {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .control-grid {
    grid-template-columns: 1fr;
  }
  
  .right-panel {
    grid-column: span 1;
  }
  
  .neural-status-bar {
    padding: 12px 20px;
    flex-direction: column;
    gap: 12px;
  }
  
  .status-left, .status-right {
    width: 100%;
    justify-content: space-between;
  }
}