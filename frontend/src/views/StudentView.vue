<template>
  <div class="neural-interface">
    <!-- 神经连接状态栏 -->
    <div class="neural-status-bar">
      <div class="status-left">
        <div class="neuron-pulse"></div>
        <span class="status-text">神经网络在线</span>
        <div class="latency-indicator">
          <span class="ping">延迟: {{ latency }}ms</span>
        </div>
      </div>
      <div class="status-right">
        <div class="user-avatar">
          <div class="avatar-core"></div>
          <div class="avatar-rings">
            <div class="ring" v-for="i in 3" :key="i"></div>
          </div>
        </div>
        <div class="user-info">
          <span class="username">{{ username }}</span>
          <span class="user-role">学生模式</span>
        </div>
        <button class="disconnect-btn" @click="logout">
          <span class="btn-label">断开连接</span>
          <div class="disconnect-wave"></div>
        </button>
      </div>
    </div>

    <!-- 主工作区 -->
    <div class="neural-workspace">
      <!-- 左侧：量子查询面板 -->
      <div class="query-panel">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="title-icon">⚛️</span>
            知识查询
          </h2>
          <div class="panel-subtitle">输入问题，启动神经网络计算</div>
        </div>
        
        <!-- 查询输入区 -->
        <div class="query-input-container">
          <div class="input-field">
            <textarea 
              v-model="question" 
              placeholder="输入您的问题，例如：什么是量子叠加？"
              rows="4"
              class="quantum-textarea"
              @keydown.enter.exact.prevent="submitQuestion"
            ></textarea>
            <div class="input-decoration"></div>
          </div>
          
          <!-- 查询按钮 -->
          <button 
            class="quantum-query-btn"
            :class="{ thinking: loading }"
            @click="submitQuestion"
            :disabled="!question.trim() || loading"
          >
            <div class="btn-content">
              <span class="btn-label">开始计算</span>
              <div class="btn-orbits">
                <div class="orbit" v-for="i in 3" :key="i"></div>
              </div>
            </div>
            <div class="btn-particles">
              <div class="particle" v-for="n in 8" :key="'p'+n"></div>
            </div>
          </button>
        </div>

        <!-- 答案展示区 -->
        <div v-if="streamingAnswer || answer" class="answer-hologram">
          <div class="hologram-header">
            <h3 class="hologram-title">
              <span class="title-icon">🔮</span>
              计算完成
            </h3>
            <div class="hologram-meta">
              <span class="meta-item">实时推理</span>
              <span class="meta-divider">•</span>
              <span class="meta-item">文档检索</span>
              <span class="meta-divider">•</span>
              <span class="meta-item">{{ answer.length }} 字符</span>
            </div>
          </div>
          
          <!-- 流式回答展示 -->
          <div class="hologram-content" v-if="streamingAnswer">
            <div class="streaming-display">
              <div class="streaming-text" v-html="renderedStreamingAnswer"></div>
              <div class="streaming-cursor-container">
                <div class="neural-cursor"></div>
              </div>
            </div>
            <div class="streaming-status">
              <div class="status-dot thinking"></div>
              <span class="status-text">神经网络推理中...</span>
            </div>
          </div>
          
          <!-- 静态答案展示 -->
          <div v-if="!streamingAnswer && answer" class="static-answer">
            <div class="answer-content" v-html="renderedAnswer"></div>
            
            <!-- 知识来源 -->
            <div v-if="sources && sources.length > 0" class="knowledge-sources">
              <div class="sources-header">
                <span class="sources-icon">📚</span>
                <span class="sources-title">知识向量源</span>
              </div>
              <div class="sources-grid">
                <div v-for="(source, index) in sources" :key="index" class="source-chip">
                  <span class="source-index">#{{ index + 1 }}</span>
                  <span class="source-content">{{ source }}</span>
                  <div class="source-relevance"></div>
                </div>
              </div>
            </div>
            
            <div class="answer-footer">
              <div class="footer-actions">
                <button class="action-btn">
                  <span class="action-icon">📋</span>
                  <span class="action-text">复制</span>
                </button>
                <button class="action-btn">
                  <span class="action-icon">⭐</span>
                  <span class="action-text">收藏</span>
                </button>
                <button class="action-btn">
                  <span class="action-icon">🔁</span>
                  <span class="action-text">重新计算</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：辅助面板 -->
      <div class="auxiliary-panel">
        <!-- 历史记录 -->
        <div class="history-hologram">
          <div class="hologram-header">
            <h3 class="hologram-title">
              <span class="title-icon">📅</span>
              查询历史
            </h3>
            <div class="hologram-actions">
              <button class="hologram-action-btn">
                <span class="action-icon">🗑️</span>
              </button>
              <button class="hologram-action-btn">
                <span class="action-icon">🔍</span>
              </button>
            </div>
          </div>
          
          <div v-if="history.length > 0" class="history-timeline">
            <div v-for="(item, index) in history.slice(0, 5)" :key="index" class="history-event">
              <div class="event-time">{{ formatTime(index) }}</div>
              <div class="event-content">
                <div class="event-question">{{ item.question }}</div>
                <div class="event-answer-preview">{{ item.answer.substring(0, 50) }}...</div>
              </div>
              <div class="event-indicator">
                <div class="indicator-dot"></div>
                <div class="indicator-line"></div>
              </div>
            </div>
          </div>
          <div v-else class="empty-history">
            <div class="empty-icon">🕳️</div>
            <div class="empty-text">暂无查询记录</div>
            <div class="empty-subtext">开始您的首次量子计算</div>
          </div>
        </div>
        
        <!-- 导师通讯 -->
        <div class="mentor-communication">
          <div class="hologram-header">
            <h3 class="hologram-title">
              <span class="title-icon">🧑‍🏫</span>
              导师通讯
            </h3>
            <div class="connection-status">
              <div class="status-dot connected"></div>
              <span class="status-text">在线</span>
            </div>
          </div>
          
          <div class="message-input">
            <textarea 
              v-model="messageToTeacher" 
              placeholder="输入留言，启动传输..."
              rows="3"
              class="quantum-textarea"
            ></textarea>
            <button 
              class="quantum-send-btn"
              @click="sendMessageToTeacher"
              :disabled="!messageToTeacher.trim() || sendingMessage"
            >
              <span class="btn-label">传输</span>
              <div class="btn-wave"></div>
            </button>
          </div>
          
          <div v-if="messageSuccess" class="transmission-success">
            <div class="success-icon">✅</div>
            <div class="success-content">
              <div class="success-title">传输完成</div>
              <div class="success-message">已发送至导师终端</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { marked } from 'marked'

// 配置marked（如果需要支持数学公式）
marked.setOptions({
  breaks: true, // 换行符转换为<br>
  gfm: true,    // 启用GitHub风格Markdown
});

export default {
  name: 'NeuralStudentView',
  setup() {
    const router = useRouter()
    const question = ref('')
    const answer = ref('')
    const streamingAnswer = ref('')
    const sources = ref([])
    const loading = ref(false)
    const history = ref([])
    const messageToTeacher = ref('')
    const sendingMessage = ref(false)
    const messageSuccess = ref(false)
    const username = ref('学习者')
    const latency = ref(28)

    // 配置marked
    marked.setOptions({
      breaks: true,
      gfm: true
    })

    const renderedAnswer = computed(() => {
      if (!answer.value) return ''
      let cleanAnswer = answer.value
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')
      return marked(cleanAnswer)
    })

    const renderedStreamingAnswer = computed(() => {
      if (!streamingAnswer.value) return ''
      let cleanAnswer = streamingAnswer.value
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')
      return marked(cleanAnswer)
    })

    const formatTime = (index) => {
      const now = new Date()
      const time = new Date(now.getTime() - index * 60000)
      return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const logout = async () => {
      try {
        await axios.post('/api/logout')
        router.push('/login')
      } catch (error) {
        console.error('断开连接失败:', error)
        router.push('/login')
      }
    }

    const submitQuestion = async () => {
      if (!question.value.trim()) return
      loading.value = true
      answer.value = ''
      streamingAnswer.value = ''

      try {
        const response = await fetch('/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: question.value }),
          credentials: 'include'
        })

        if (!response.ok || !response.body) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.token) {
                  let token = data.token
                    .replace(/<\|im_end\|>/g, '')
                    .replace(/<\|im_start\|>/g, '')
                  if (token) {
                    streamingAnswer.value += token
                  }
                }
                // 新增：处理sources字段
                if (data.sources && Array.isArray(data.sources)) {
                  sources.value = data.sources; // 更新来源数组
                }
              } catch (e) {
                console.warn('解析数据失败:', e, line)
              }
            }
          }
        }

        answer.value = streamingAnswer.value
        history.value.unshift({
          question: question.value,
          answer: streamingAnswer.value,
          sources: sources.value
        })
        question.value = ''

      } catch (error) {
        console.error('计算失败:', error)
        alert('计算失败，请检查连接状态')
      } finally {
        loading.value = false
        streamingAnswer.value = ''
      }
    }

    const sendMessageToTeacher = async () => {
      if (!messageToTeacher.value.trim()) return
      sendingMessage.value = true
      messageSuccess.value = false

      try {
        await axios.post('/api/messages', {
          content: messageToTeacher.value
        })
        
        messageSuccess.value = true
        messageToTeacher.value = ''
        setTimeout(() => {
          messageSuccess.value = false
        }, 3000)
        
      } catch (error) {
        console.error('传输失败:', error)
        alert(error.response?.data?.error || '传输失败')
      } finally {
        sendingMessage.value = false
      }
    }

    return {
      question,
      answer,
      streamingAnswer,
      sources,
      loading,
      history,
      messageToTeacher,
      sendingMessage,
      messageSuccess,
      username,
      latency,
      renderedAnswer,
      renderedStreamingAnswer,
      logout,
      submitQuestion,
      sendMessageToTeacher,
      formatTime
    }
  }
}
</script>

<style scoped>
.neural-interface {
  min-height: 100vh;
  background: 
    radial-gradient(ellipse at 0% 0%, #0a0a1a 0%, #000 50%),
    radial-gradient(ellipse at 100% 100%, #001122 0%, transparent 70%);
  color: #f8fafc;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
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
  overflow: hidden;
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
    #00ffff, 
    transparent
  );
  animation: scan 3s linear infinite;
}

@keyframes scan {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.status-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.neuron-pulse {
  width: 12px;
  height: 12px;
  background: #00ffff;
  border-radius: 50%;
  position: relative;
  animation: neuronPulse 2s infinite;
}

@keyframes neuronPulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(0, 255, 255, 0.4); 
  }
  50% { 
    box-shadow: 0 0 0 10px rgba(0, 255, 255, 0); 
  }
}

.status-text {
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.latency-indicator {
  padding: 6px 12px;
  background: rgba(0, 255, 255, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 255, 0.2);
}

.ping {
  color: #00ffff;
  font-size: 11px;
  font-weight: 500;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-avatar {
  position: relative;
  width: 40px;
  height: 40px;
}

.avatar-core {
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
  animation: orbit 6s linear infinite;
}

.avatar-rings .ring:nth-child(1) {
  width: 40px;
  height: 40px;
  animation-delay: 0s;
}

.avatar-rings .ring:nth-child(2) {
  width: 30px;
  height: 30px;
  animation-delay: -2s;
}

.avatar-rings .ring:nth-child(3) {
  width: 20px;
  height: 20px;
  animation-delay: -4s;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.username {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
}

.user-role {
  color: #00ffff;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1px;
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

.neural-workspace {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 30px;
  padding: 30px;
  max-width: 1600px;
  margin: 0 auto;
}

.query-panel, .auxiliary-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #f8fafc;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.title-icon {
  font-size: 28px;
}

.panel-subtitle {
  color: #94a3b8;
  font-size: 13px;
  letter-spacing: 1px;
}

.query-input-container {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.input-field {
  position: relative;
  margin-bottom: 20px;
}

.quantum-textarea {
  width: 100%;
  padding: 20px;
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: #f8fafc;
  font-size: 16px;
  font-family: inherit;
  resize: vertical;
  transition: all 0.3s;
  outline: none;
}

.quantum-textarea:focus {
  border-color: rgba(0, 255, 255, 0.3);
  background: rgba(30, 41, 59, 0.5);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
}

.input-decoration {
  position: absolute;
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 2px;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(0, 255, 255, 0.5), 
    transparent
  );
  transform: scaleX(0);
  transition: transform 0.3s;
}

.quantum-textarea:focus ~ .input-decoration {
  transform: scaleX(1);
}

.quantum-query-btn {
  position: relative;
  width: 100%;
  padding: 20px;
  background: linear-gradient(135deg, 
    rgba(0, 200, 255, 0.2), 
    rgba(0, 150, 255, 0.1)
  );
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 12px;
  color: #00ffff;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
}

.quantum-query-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, 
    rgba(0, 200, 255, 0.3), 
    rgba(0, 150, 255, 0.2)
  );
  box-shadow: 
    0 0 30px rgba(0, 255, 255, 0.3),
    inset 0 0 20px rgba(0, 255, 255, 0.1);
  transform: translateY(-2px);
}

.quantum-query-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quantum-query-btn.thinking {
  animation: thinkingGlow 1.5s infinite;
}

@keyframes thinkingGlow {
  0%, 100% { 
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
  }
  50% { 
    box-shadow: 0 0 40px rgba(0, 255, 255, 0.4);
  }
}

.btn-content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.btn-orbits {
  position: relative;
  width: 20px;
  height: 20px;
}

.btn-orbits .orbit {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 50%;
  animation: orbit 2s linear infinite;
}

.btn-orbits .orbit:nth-child(1) {
  width: 20px;
  height: 20px;
  animation-delay: 0s;
}

.btn-orbits .orbit:nth-child(2) {
  width: 15px;
  height: 15px;
  animation-delay: -0.66s;
}

.btn-orbits .orbit:nth-child(3) {
  width: 10px;
  height: 10px;
  animation-delay: -1.33s;
}

.btn-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.btn-particles .particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(0, 255, 255, 0.6);
  border-radius: 50%;
  animation: floatUp 2s infinite linear;
}

@keyframes floatUp {
  0% {
    transform: translateY(100%) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(-100%) rotate(360deg);
    opacity: 0;
  }
}

.answer-hologram {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: 
    0 10px 30px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.hologram-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.hologram-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f8fafc;
  font-size: 18px;
  font-weight: 600;
}

.hologram-meta {
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

.streaming-display {
  position: relative;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 255, 0.1);
  min-height: 200px;
  margin-bottom: 20px;
}

.streaming-text {
  font-size: 14px;
  line-height: 1.6;
  color: #e2e8f0;
}

.streaming-cursor-container {
  display: inline-block;
  margin-left: 4px;
}

.neural-cursor {
  width: 8px;
  height: 20px;
  background: #00ffff;
  animation: cursorBlink 1s infinite;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.streaming-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(0, 255, 255, 0.1);
  border-radius: 20px;
  width: fit-content;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.thinking {
  background: #00ffff;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { 
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 255, 255, 0.4);
  }
  50% { 
    opacity: 0.5;
    box-shadow: 0 0 0 8px rgba(0, 255, 255, 0);
  }
}

.static-answer {
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.answer-content {
  font-size: 15px;
  line-height: 1.7;
  color: #e2e8f0;
  margin-bottom: 30px;
}

.answer-content :deep(h1),
.answer-content :deep(h2),
.answer-content :deep(h3) {
  color: #00ffff;
  margin-top: 20px;
  margin-bottom: 10px;
}

.answer-content :deep(code) {
  background: rgba(0, 255, 255, 0.1);
  color: #00ffff;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.answer-content :deep(pre) {
  background: rgba(0, 0, 0, 0.3);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
  margin: 15px 0;
}

.answer-content :deep(blockquote) {
  border-left: 4px solid #00ffff;
  padding-left: 15px;
  margin: 15px 0;
  color: #94a3b8;
  font-style: italic;
}

.knowledge-sources {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  color: #00ffff;
  font-size: 14px;
  font-weight: 600;
}

.sources-grid {
  display: grid;
  gap: 10px;
}

.source-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.source-chip:hover {
  background: rgba(30, 41, 59, 0.5);
  border-color: rgba(0, 255, 255, 0.2);
  transform: translateX(4px);
}

.source-index {
  color: #00ffff;
  font-size: 12px;
  font-weight: 600;
  min-width: 30px;
}

.source-content {
  flex: 1;
  color: #cbd5e1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-relevance {
  width: 4px;
  height: 20px;
  background: linear-gradient(180deg, #00ffff, #0088ff);
  border-radius: 2px;
  animation: relevancePulse 2s infinite;
}

@keyframes relevancePulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.answer-footer {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.footer-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
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

.action-btn:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.2);
  color: #00ffff;
}

.history-hologram,
.mentor-communication {
  padding: 20px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.hologram-actions {
  display: flex;
  gap: 8px;
}

.hologram-action-btn {
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.3s;
}

.hologram-action-btn:hover {
  background: rgba(0, 255, 255, 0.1);
  border-color: rgba(0, 255, 255, 0.2);
  color: #00ffff;
}

.history-timeline {
  position: relative;
  padding-left: 20px;
}

.history-timeline::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 8px;
  width: 2px;
  background: linear-gradient(180deg, 
    transparent, 
    rgba(0, 255, 255, 0.3), 
    transparent
  );
}

.history-event {
  position: relative;
  padding: 12px 0 12px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.history-event:last-child {
  border-bottom: none;
}

.event-time {
  color: #00ffff;
  font-size: 10px;
  font-weight: 600;
  margin-bottom: 4px;
  letter-spacing: 1px;
}

.event-content {
  margin-left: 8px;
}

.event-question {
  color: #f8fafc;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-answer-preview {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.4;
}

.event-indicator {
  position: absolute;
  left: 4px;
  top: 16px;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  background: #00ffff;
  border-radius: 50%;
  position: relative;
  z-index: 2;
}

.indicator-line {
  position: absolute;
  top: 8px;
  left: 3px;
  width: 2px;
  height: calc(100% - 8px);
  background: rgba(0, 255, 255, 0.3);
}

.empty-history {
  text-align: center;
  padding: 40px 20px;
  color: #64748b;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.empty-subtext {
  font-size: 12px;
  color: #475569;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0, 255, 128, 0.1);
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 20px;
}

.status-dot.connected {
  width: 6px;
  height: 6px;
  background: #00ff80;
  border-radius: 50%;
  animation: connectedPulse 2s infinite;
}

@keyframes connectedPulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(0, 255, 128, 0.4);
  }
  50% { 
    box-shadow: 0 0 0 6px rgba(0, 255, 128, 0);
  }
}

.quantum-send-btn {
  width: 100%;
  margin-top: 12px;
  padding: 15px;
  background: linear-gradient(135deg, 
    rgba(0, 255, 128, 0.2), 
    rgba(0, 200, 128, 0.1)
  );
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 12px;
  color: #00ff80;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.quantum-send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, 
    rgba(0, 255, 128, 0.3), 
    rgba(0, 200, 128, 0.2)
  );
  box-shadow: 0 0 20px rgba(0, 255, 128, 0.3);
  transform: translateY(-2px);
}

.quantum-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-wave {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(0, 255, 128, 0.2), 
    transparent
  );
  transform: translateX(-100%);
  animation: slideGlow 2s infinite;
}

.transmission-success {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  margin-top: 15px;
  background: rgba(0, 255, 128, 0.1);
  border: 1px solid rgba(0, 255, 128, 0.2);
  border-radius: 12px;
  animation: slideIn 0.5s ease-out;
}

.success-icon {
  font-size: 20px;
}

.success-content {
  flex: 1;
}

.success-title {
  color: #00ff80;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 2px;
}

.success-message {
  color: #94f8d1;
  font-size: 11px;
}
</style>