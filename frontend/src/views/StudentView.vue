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
                   placeholder="请输入您的问题，例如：什么是加法？或者上传图片进行视觉问答"
                   :rows="4"
                 />
               </a-form-item>
               
               <!-- 新增：图像上传区域 -->
               <a-form-item>
                 <div class="image-upload-section">
                   <a-upload
                     :before-upload="handleImageUpload"
                     :show-upload-list="false"
                     accept=".png,.jpg,.jpeg,.gif,.bmp"
                   >
                     <a-button>
                       <template #icon><upload-outlined /></template>
                       上传图片
                     </a-button>
                   </a-upload>
                   
                   <div v-if="uploadedImage" class="image-preview">
                     <img :src="uploadedImage" alt="上传的图片" />
                     <a-button 
                       type="link" 
                       danger 
                       @click="removeImage"
                       size="small"
                     >
                       移除
                     </a-button>
                   </div>
                 </div>
               </a-form-item>
               
               <a-form-item>
                 <a-space>
                   <a-button 
                     type="primary" 
                     @click="submitQuestion" 
                     :disabled="(!question.trim() && !uploadedImage) || loading"
                     :loading="loading"
                   >
                     {{ loading ? '思考中...' : '提问' }}
                   </a-button>
                   
                   <a-button 
                     v-if="uploadedImage && !question.trim()"
                     type="dashed"
                     @click="analyzeImageOnly"
                     :loading="loading"
                   >
                     仅分析图片
                   </a-button>
                 </a-space>
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
                    <a-card size="small" class="history-item">
                      <div class="history-question">
                        <span class="history-label">Q:</span>
                        <span>{{ item.question }}</span>
                      </div>
                      <div class="history-answer markdown-body" v-html="renderHistoryAnswer(item.answer)">
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>
            </div>
          </a-card>
        </a-col>

        <!-- 右侧：留言给老师 -->
        <a-col :xs="24" :md="8">
          <!-- 发送留言卡片 -->
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

          <!-- 留言历史卡片 -->
          <a-card title="留言历史" class="message-history-section">
            <a-empty v-if="messages.length === 0" description="暂无留言历史" />
            
            <a-list v-else
              item-layout="vertical"
              :data-source="messages"
              size="small"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-card size="small">
                    <template #title>
                      <span>留言时间：{{ new Date(item.timestamp).toLocaleString('zh-CN') }}</span>
                    </template>
                    <p>{{ item.content }}</p>
                    
                    <!-- 显示老师回复 -->
                    <div v-if="item.reply_content" style="margin-top: 12px;">
                      <a-divider style="margin: 8px 0;" />
                      <p style="color: #1890ff;"><strong>老师回复:</strong> {{ item.reply_content }}</p>
                      <p v-if="item.reply_timestamp" style="font-size: 12px; color: #888;">
                        回复时间：{{ new Date(item.reply_timestamp).toLocaleString('zh-CN') }}
                      </p>
                    </div>
                    
                    <!-- 显示状态 -->
                    <div v-else style="margin-top: 8px;">
                      <a-tag :color="item.status === 'replied' ? 'green' : 'orange'">
                        {{ item.status === 'replied' ? '已回复' : '未回复' }}
                      </a-tag>
                    </div>
                  </a-card>
                </a-list-item>
              </template>
            </a-list>
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
import { UploadOutlined } from '@ant-design/icons-vue'

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
    const messages = ref([]); // 新增：留言历史
    const messageToTeacher = ref('');
    const sendingMessage = ref(false);
    const messageSuccess = ref(false);
    const uploadedImage = ref(''); // 新增：上传的图片base64
    const imageFile = ref(null); // 新增：图片文件对象

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

    // 渲染历史答案的方法
    const renderHistoryAnswer = (answer) => {
      if (!answer) return ''
      let cleanAnswer = answer
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')
      const withLatex = renderLatex(cleanAnswer)
      return marked(withLatex)
    }

    // 新增：图像上传处理
    const handleImageUpload = (file) => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => {
          uploadedImage.value = e.target.result
          imageFile.value = file
          resolve(false) // 返回false阻止自动上传
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
    }

    // 移除图片
    const removeImage = () => {
      uploadedImage.value = ''
      imageFile.value = null
    }

    // 仅分析图片
    const analyzeImageOnly = async () => {
      if (!uploadedImage.value) return
      
      loading.value = true
      answer.value = ''
      streamingAnswer.value = ''
      
      try {
        const response = await fetch('/api/multimodal/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            image: uploadedImage.value.split(',')[1] // 移除data:image前缀
          }),
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
              } catch (e) {
                console.warn('解析流数据失败:', e, line)
              }
            }
          }
        }

        answer.value = streamingAnswer.value
        history.value.unshift({
          question: '[图片分析]',
          answer: streamingAnswer.value
        })

      } catch (error) {
        console.error('图片分析失败:', error)
        alert('图片分析失败，请检查网络连接。')
      } finally {
        loading.value = false
        streamingAnswer.value = ''
      }
    }

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

    // 提交问题（支持多模态）
    const submitQuestion = async () => {
      if (!question.value.trim() && !uploadedImage.value) return;

      loading.value = true;
      answer.value = '';
      streamingAnswer.value = ''; // 清空实时流

      try {
        const apiEndpoint = uploadedImage.value ? '/api/multimodal/qa' : '/api/qa'
        const requestBody = uploadedImage.value ? {
          question: question.value,
          image: uploadedImage.value.split(',')[1] // 移除data:image前缀
        } : {
          question: question.value
        }

        const response = await fetch(apiEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
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
          question: question.value || '[图片分析]',
          answer: streamingAnswer.value
        });
        question.value = '';
        removeImage(); // 清空上传的图片

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
        
        // 重新加载留言历史
        await fetchMessages()
        
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

    // 加载历史问答记录
    const fetchQuestionHistory = async () => {
      try {
        const response = await axios.get('/api/student/questions/history')
        // 将历史记录转换为前端需要的格式
        history.value = response.data.map(item => ({
          question: item.question,
          answer: item.answer
        }))
      } catch (error) {
        console.error('加载历史记录失败:', error)
        if (error.response?.status !== 401) {
          // 如果不是认证错误，才显示错误
          console.error('加载历史记录失败:', error)
        }
      }
    }

    // 加载留言历史记录
    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data
      } catch (error) {
        console.error('加载留言历史失败:', error)
        if (error.response?.status !== 401) {
          console.error('加载留言历史失败:', error)
        }
      }
    }

    // 页面加载时获取历史数据
    onMounted(() => {
      fetchQuestionHistory()
      fetchMessages()
    })

    return {
      question,
      answer,
      streamingAnswer,
      sources,
      loading,
      history,
      messages,
      messageToTeacher,
      sendingMessage,
      messageSuccess,
      uploadedImage,
      UploadOutlined,
      logout,
      submitQuestion,
      sendMessageToTeacher,
      handleImageUpload,
      removeImage,
      analyzeImageOnly,
      renderedAnswer,
      renderedStreamingAnswer,
      renderHistoryAnswer
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
.message-section,
.message-history-section {
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

.history-item {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  margin-bottom: 16px;
}

.history-question {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.history-label {
  font-weight: 600;
  color: #fff;
  margin-right: 8px;
}

.history-answer {
  padding: 12px;
  background: #141414;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
  color: #e0e0e0;
}

/* 图像上传区域样式 */
.image-upload-section {
  margin-bottom: 16px;
}

.image-preview {
  margin-top: 12px;
  padding: 12px;
  background: #1a1a1a;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
  margin-bottom: 8px;
  display: block;
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