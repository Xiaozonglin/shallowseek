<template>
  <div class="student-container">
    <!-- 添加一个学生页面的登出按钮（可选） -->
    <div class="student-header">
      <h1>学生工作台</h1>
      <button @click="logout" class="student-logout-btn">退出登录</button>
    </div>

    <div class="main-content">
      <!-- 左侧：提问区域 -->
      <div class="qa-section">
        <h2>向AI提问</h2>
        <div class="input-area">
          <textarea 
            v-model="question" 
            placeholder="请输入您的问题，例如：什么是加法？"
            rows="4"
          ></textarea>
          <button 
            @click="submitQuestion" 
            :disabled="!question.trim() || loading"
            class="ask-btn"
          >
            {{ loading ? '思考中...' : '提问' }}
          </button>
        </div>

        <!-- 答案显示区域 -->
        <div v-if="streamingAnswer || answer" class="answer-section">
          <h3>AI答案：</h3>
          <!-- 区域1：流式回答实时显示（正在生成时显示） -->
          <div v-if="streamingAnswer" class="streaming-answer">
            {{ streamingAnswer }}
            <span class="streaming-cursor">█</span> <!-- 可选的光标动画 -->
          </div>
          <!-- 区域2：最终答案静态显示（流结束后显示） -->
          <div v-else class="answer-content">
            {{ answer }}
          </div>
          
          <!-- 新增：答案来源展示 -->
          <div v-if="sources && sources.length > 0" class="sources-section">
            <h4>📚 答案参考来源：</h4>
            <ul class="sources-list">
              <li v-for="(source, index) in sources" :key="index">
                {{ source }}
              </li>
            </ul>
          </div>
          
          <div class="answer-meta">
            <small>本次回答基于文档检索生成</small>
          </div>
        </div>

        <!-- 历史问题 -->
        <div v-if="history.length > 0" class="history-section">
          <h3>提问历史</h3>
          <div class="history-list">
            <div v-for="(item, index) in history" :key="index" class="history-item">
              <div class="history-question"><strong>Q:</strong> {{ item.question }}</div>
              <div class="history-answer"><strong>A:</strong> {{ item.answer }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：留言给老师 -->
      <div class="message-section">
        <h2>给老师留言</h2>
        <div class="message-input">
          <textarea 
            v-model="messageToTeacher" 
            placeholder="有什么问题需要老师协助吗？"
            rows="3"
          ></textarea>
          <button 
            @click="sendMessageToTeacher" 
            :disabled="!messageToTeacher.trim() || sendingMessage"
            class="message-btn"
          >
            {{ sendingMessage ? '发送中...' : '发送留言' }}
          </button>
        </div>
        <div v-if="messageSuccess" class="success-message">
          留言已发送！老师会收到邮件通知。
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'  // 新增：导入 useRouter
import axios from 'axios'

export default {
  name: 'StudentView',
  setup() {
    const router = useRouter()  // 新增：获取路由实例
    const question = ref('');
    const answer = ref('');
    const streamingAnswer = ref('');
    const sources = ref([]);
    const loading = ref(false);
    const history = ref([]);
    const messageToTeacher = ref('');
    const sendingMessage = ref(false);
    const messageSuccess = ref(false);

    // 新增：登出方法
    const logout = async () => {
      try {
        // 发送登出请求到后端
        await axios.post('/api/logout')
        console.log('学生登出成功')
      } catch (error) {
        console.error('学生登出失败:', error)
      } finally {
        // 无论成功失败，都跳转到登录页
        router.push('/login')
      }
    }

    // 提交问题
    const submitQuestion = async () => {
      if (!question.value.trim()) return;

      loading.value = true;
      answer.value = '';
      streamingAnswer.value = ''; // 清空实时流

      try {
        const response = await fetch('/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: question.value }),
          credentials: 'include' // 重要：确保发送 Cookie
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                  streamingAnswer.value += data.token; // 实时追加
                }
              } catch (e) {
                console.warn('解析流数据失败:', e, line);
              }
            }
          }
        }

        // 流结束后，将最终结果存入 answer 和历史记录
        answer.value = streamingAnswer.value;
        history.value.unshift({
          question: question.value,
          answer: streamingAnswer.value
        });
        question.value = '';

      } catch (error) {
        console.error('提问失败:', error);
        alert('提问失败，请检查网络连接或控制台信息。');
      } finally {
        loading.value = false;
        streamingAnswer.value = ''; // 可选：清空实时流显示
      }
    };
    
    // 发送留言给老师
    const sendMessageToTeacher = async () => {
      if (!messageToTeacher.value.trim()) return
      
      sendingMessage.value = true
      messageSuccess.value = false
      
      try {
        await axios.post('/api/messages', {
          content: messageToTeacher.value
        })
        
        messageSuccess.value = true
        messageToTeacher.value = '' // 清空输入框
        setTimeout(() => {
          messageSuccess.value = false
        }, 3000)
        
      } catch (error) {
        console.error('发送留言失败:', error)
        alert(error.response?.data?.error || '发送失败')
      } finally {
        sendingMessage.value = false
      }
    }

    return {
      question,
      answer,
      sources,
      loading,
      history,
      messageToTeacher,
      sendingMessage,
      messageSuccess,
      logout,  // 新增：返回 logout 方法
      submitQuestion,
      sendMessageToTeacher
    }
  }
}
</script>

<style scoped>
/* 新增样式：学生头部区域和登出按钮 */
.student-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 15px;
  border-bottom: 2px solid #667eea;
}

.student-header h1 {
  color: #333;
  margin: 0;
}

.student-logout-btn {
  padding: 8px 20px;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: transform 0.2s;
}

.student-logout-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(231, 76, 60, 0.4);
}

.student-container {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 30px;
}

.qa-section, .message-section {
  background: white;
  padding: 25px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

h2 {
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #667eea;
}

.input-area textarea, .message-input textarea {
  width: 100%;
  padding: 15px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 16px;
  resize: vertical;
  box-sizing: border-box;
  margin-bottom: 15px;
}

.input-area textarea:focus, .message-input textarea:focus {
  outline: none;
  border-color: #667eea;
}

.ask-btn, .message-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.ask-btn:hover:not(:disabled), .message-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.ask-btn:disabled, .message-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.answer-section {
  margin-top: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #28a745;
}

.answer-content {
  font-size: 16px;
  line-height: 1.6;
  color: #333;
  margin: 10px 0;
}

.answer-meta {
  text-align: right;
  color: #6c757d;
  font-size: 14px;
}

.history-section {
  margin-top: 30px;
}

.history-list {
  max-height: 300px;
  overflow-y: auto;
}

.history-item {
  padding: 15px;
  margin-bottom: 15px;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 6px;
}

.history-question {
  color: #0066cc;
  margin-bottom: 8px;
}

.history-answer {
  color: #333;
  font-size: 15px;
}

.success-message {
  margin-top: 15px;
  padding: 10px;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
  text-align: center;
}

.sources-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px dashed #eee;
}

.sources-section h4 {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.sources-list {
  list-style-type: none;
  padding-left: 0;
  font-size: 13px;
  color: #888;
}

.sources-list li {
  padding: 4px 0;
  padding-left: 20px;
  position: relative;
  word-break: break-all; /* 防止长路径溢出 */
}

.sources-list li:before {
  content: '📄';
  position: absolute;
  left: 0;
}
</style>