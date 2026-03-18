<template>
  <a-layout class="student-container">
    <a-layout-content>
      <a-row :gutter="[16, 16]" style="padding: 24px;">
        <!-- 左侧：提问区域 -->
        <a-col :xs="24" :md="16">
          <a-card title="向AI提问" class="qa-section">
            <a-form layout="vertical">
              <a-form-item>
                <a-textarea
                  v-model:value="question"
                  placeholder="请输入您的问题，例如：什么是加法？"
                  :rows="4"
                />
              </a-form-item>
              <a-form-item>
                <a-button 
                  type="primary" 
                  block
                  @click="submitQuestion" 
                  :disabled="!question.trim() || loading"
                  :loading="loading"
                >
                  {{ loading ? '思考中...' : '提问' }}
                </a-button>
              </a-form-item>
            </a-form>

            <!-- 答案显示区域 -->
            <div v-if="streamingAnswer || answer" class="answer-section">
              <a-divider orientation="left">AI答案</a-divider>
              <!-- 流式回答实时显示 -->
              <a-card v-if="streamingAnswer" class="streaming-card">
                <div class="streaming-wrapper">
                  <div class="streaming-answer markdown-body" v-html="renderedStreamingAnswer"></div>
                  <span class="streaming-cursor">█</span>
                </div>
              </a-card>
              <!-- 静态答案显示 -->
              <a-card v-else-if="!streamingAnswer && answer" class="answer-card">
                <div class="answer-content markdown-body" v-html="renderedAnswer">
                </div>
                
                <!-- 新增：答案来源展示 -->
                <div v-if="sources && sources.length > 0" class="sources-section">
                  <a-divider orientation="left">📚 答案参考来源</a-divider>
                  <a-list
                    item-layout="horizontal"
                    :data-source="sources"
                  >
                    <template #renderItem="{ item }">
                      <a-list-item>
                        <a-list-item-meta
                          avatar="📄"
                          title="{{ item }}"
                        />
                      </a-list-item>
                    </template>
                  </a-list>
                </div>
                
                <div class="answer-meta">
                  <a-tag color="blue">本次回答基于文档检索生成</a-tag>
                </div>
              </a-card>
            </div>

            <!-- 历史问题 -->
            <div v-if="history.length > 0" class="history-section">
              <a-divider orientation="left">提问历史</a-divider>
              <a-list
                item-layout="vertical"
                :data-source="history"
              >
                <template #renderItem="{ item, index }">
                  <a-list-item :key="index">
                    <a-list-item-meta
                      :title="`<strong>Q:</strong> ${item.question}`"
                      :description="`<strong>A:</strong> ${item.answer}`"
                    />
                  </a-list-item>
                </template>
              </a-list>
            </div>
          </a-card>
        </a-col>

        <!-- 右侧：留言给老师 -->
        <a-col :xs="24" :md="8">
          <a-card title="给老师留言" class="message-section">
            <a-form layout="vertical">
              <a-form-item>
                <a-textarea
                  v-model:value="messageToTeacher"
                  placeholder="有什么问题需要老师协助吗？"
                  :rows="3"
                />
              </a-form-item>
              <a-form-item>
                <a-button 
                  type="primary" 
                  block
                  @click="sendMessageToTeacher" 
                  :disabled="!messageToTeacher.trim() || sendingMessage"
                  :loading="sendingMessage"
                >
                  {{ sendingMessage ? '发送中...' : '发送留言' }}
                </a-button>
              </a-form-item>
            </a-form>
            <a-alert 
              v-if="messageSuccess" 
              type="success" 
              message="留言已发送！" 
              description="老师会收到邮件通知。"
              show-icon
            />
          </a-card>
        </a-col>
      </a-row>
    </a-layout-content>
  </a-layout>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'

export default {
  name: 'StudentView',
  setup() {
    const router = useRouter()
    const question = ref('');
    const answer = ref('');
    const streamingAnswer = ref('');
    const loading = ref(false);
    const sources = ref([]);
    const history = ref([]);
    const messageToTeacher = ref('');
    const sendingMessage = ref(false);
    const messageSuccess = ref(false);

    marked.setOptions({
      breaks: true,
      gfm: true
    })

    const renderLatex = (text) => {
      if (!text) return ''
      let result = text
      
      // 处理 \[...\] 格式的行间公式
      result = result.replace(/\\\[([\s\S]+?)\\\]/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: true, throwOnError: false })
        } catch (e) {
          return match
        }
      })
      
      // 处理 $$...$$ 格式的行间公式
      result = result.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: true, throwOnError: false })
        } catch (e) {
          return match
        }
      })
      
      // 处理 \(...\) 格式的行内公式
      result = result.replace(/\\\(([^)]+?)\\\)/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: false, throwOnError: false })
        } catch (e) {
          return match
        }
      })
      
      // 处理 $...$ 格式的行内公式
      result = result.replace(/\$([^\$\n]+?)\$/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: false, throwOnError: false })
        } catch (e) {
          return match
        }
      })
      
      return result
    }

    const renderedAnswer = computed(() => {
      if (!answer.value) return ''
      let cleanAnswer = answer.value
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')
      const withLatex = renderLatex(cleanAnswer)
      return marked(withLatex)
    })

    const renderedStreamingAnswer = computed(() => {
      if (!streamingAnswer.value) return ''
      let cleanAnswer = streamingAnswer.value
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')
      const withLatex = renderLatex(cleanAnswer)
      return marked(withLatex)
    })

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
                  // 过滤特殊标记
                  let token = data.token
                    .replace(/<\|im_end\|>/g, '')
                    .replace(/<\|im_start\|>/g, '')
                  if (token) {
                    streamingAnswer.value += token; // 实时追加
                  }
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
      streamingAnswer,  // 新增：返回streamingAnswer变量
      sources,
      loading,
      history,
      messageToTeacher,
      sendingMessage,
      messageSuccess,
      logout,  // 新增：返回 logout 方法
      submitQuestion,
      sendMessageToTeacher,
      renderedAnswer,
      renderedStreamingAnswer
    }
  }
}
</script>

<style scoped>
.student-container {
  min-height: 100vh;
  background: #0a0a0a;
}

.qa-section,
.message-section {
  margin-bottom: 24px;
}

.streaming-wrapper {
  position: relative;
  display: inline-block;
  width: 100%;
}

.streaming-answer {
  position: relative;
  display: inline;
}

.streaming-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  font-weight: bold;
  color: #fff;
  margin-left: 2px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.answer-section {
  margin-top: 24px;
}

.answer-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.streaming-card {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.answer-content {
  padding: 16px;
  background: #141414;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.sources-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.answer-meta {
  margin-top: 16px;
  text-align: right;
}

.history-section {
  margin-top: 24px;
}

/* Markdown渲染样式 - 暗色主题 */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: #e0e0e0;
  word-wrap: break-word;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: #fff;
}

.markdown-body h1 { font-size: 2em; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: .3em; }
.markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: .3em; }
.markdown-body h3 { font-size: 1.25em; }
.markdown-body h4 { font-size: 1em; }

.markdown-body p {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body code {
  padding: .2em .4em;
  margin: 0;
  font-size: 85%;
  white-space: break-spaces;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace;
  color: #fff;
}

.markdown-body pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #1a1a1a;
  border-radius: 6px;
  margin-top: 0;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-body pre code {
  background-color: transparent;
  padding: 0;
}

.markdown-body ul,
.markdown-body ol {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-body li {
  margin-top: .25em;
}

.markdown-body blockquote {
  margin: 0 0 16px;
  padding: 0 1em;
  color: #888;
  border-left: .25em solid rgba(255, 255, 255, 0.2);
}

.markdown-body a {
  color: #fff;
  text-decoration: underline;
}

.markdown-body a:hover {
  text-decoration: underline;
}

.markdown-body table {
  border-spacing: 0;
  border-collapse: collapse;
  display: block;
  width: max-content;
  max-width: 100%;
  overflow: auto;
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body table tr {
  background-color: #141414;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-body table th,
.markdown-body table td {
  padding: 6px 13px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.markdown-body table th {
  font-weight: 600;
  background-color: #1a1a1a;
}

.markdown-body img {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #141414;
}

.markdown-body hr {
  height: .25em;
  padding: 0;
  margin: 24px 0;
  background-color: rgba(255, 255, 255, 0.1);
  border: 0;
}
</style>