<template>
  <div class="workspace-page">
    <div class="container workspace-shell">
      <section class="workspace-hero">
        <div>
          <div class="workspace-eyebrow">Student Workspace</div>
          <h1>专注提问、阅读答案、与老师协作。</h1>
          <p>
            让 AI 问答、图像理解与留言记录在同一屏内自然流动。
          </p>
        </div>
        <div class="workspace-stats">
          <div class="metric-card">
            <span>历史提问</span>
            <strong>{{ history.length }}</strong>
          </div>
          <div class="metric-card">
            <span>留言记录</span>
            <strong>{{ messages.length }}</strong>
          </div>
        </div>
      </section>

      <a-row :gutter="[24, 24]">
        <a-col :xs="24" :xl="16">
          <a-card class="surface-card panel-card composer-card" title="智能提问">
            <a-form layout="vertical">
              <a-form-item label="输入问题">
                <a-textarea
                  v-model:value="question"
                  placeholder="输入你想问的问题，或上传一张图片让系统一起分析。"
                  :rows="5"
                />
              </a-form-item>

              <a-form-item label="图像输入（可选）">
                <div class="upload-row">
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
                  <span class="upload-tip">支持课堂截图、习题照片、讲义页面。</span>
                </div>

                <transition name="soft-rise">
                  <div v-if="uploadedImage" class="image-preview">
                    <img :src="uploadedImage" alt="上传预览" />
                    <a-button type="link" danger @click="removeImage">移除图片</a-button>
                  </div>
                </transition>
              </a-form-item>

              <div class="action-row">
                <a-button
                  type="primary"
                  @click="submitQuestion"
                  :disabled="(!question.trim() && !uploadedImage) || loading"
                  :loading="loading"
                >
                  {{ loading ? '生成中...' : '发送提问' }}
                </a-button>

                <a-button
                  v-if="uploadedImage && !question.trim()"
                  type="dashed"
                  @click="analyzeImageOnly"
                  :loading="loading"
                >
                  仅分析图片
                </a-button>
              </div>
            </a-form>
          </a-card>

          <transition name="soft-rise">
            <a-card v-if="streamingAnswer || answer" class="surface-card panel-card answer-panel" title="回答结果">
              <div v-if="streamingAnswer" class="answer-stream markdown-body" v-html="renderedStreamingAnswer"></div>
              <div v-else class="answer-body markdown-body" v-html="renderedAnswer"></div>

              <div v-if="sources && sources.length > 0" class="sources-block">
                <a-divider orientation="left">参考来源</a-divider>
                <a-list item-layout="horizontal" :data-source="sources">
                  <template #renderItem="{ item }">
                    <a-list-item>
                      <span class="source-item">{{ item }}</span>
                    </a-list-item>
                  </template>
                </a-list>
              </div>
            </a-card>
          </transition>

          <a-card class="surface-card panel-card" title="提问历史">
            <a-empty v-if="history.length === 0" description="还没有历史记录" />
            <TransitionGroup v-else name="stack-reveal" tag="div" class="history-stack">
              <article v-for="(item, index) in history" :key="`${index}-${item.question}`" class="history-entry">
                <div class="history-question">
                  <span class="history-kicker">Q{{ index + 1 }}</span>
                  <h3>{{ item.question }}</h3>
                </div>
                <div class="history-answer markdown-body" v-html="renderHistoryAnswer(item.answer)"></div>
              </article>
            </TransitionGroup>
          </a-card>
        </a-col>

        <a-col :xs="24" :xl="8">
          <a-card class="surface-card panel-card" title="给老师留言">
            <a-form layout="vertical">
              <a-form-item label="留言内容">
                <a-textarea
                  v-model:value="messageToTeacher"
                  placeholder="把需要老师进一步帮助的问题写在这里。"
                  :rows="4"
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

            <transition name="soft-rise">
              <a-alert
                v-if="messageSuccess"
                type="success"
                message="发送成功"
                description="老师将会在教师端查看并回复你的留言。"
                show-icon
              />
            </transition>
          </a-card>

          <a-card class="surface-card panel-card" title="留言记录">
            <a-empty v-if="messages.length === 0" description="暂无留言记录" />

            <TransitionGroup v-else name="stack-reveal" tag="div" class="message-stack">
              <article v-for="item in messages" :key="item.id" class="message-entry">
                <div class="message-meta">
                  <span>{{ new Date(item.timestamp).toLocaleString('zh-CN') }}</span>
                  <a-tag :color="item.status === 'replied' ? 'success' : 'default'">
                    {{ item.status === 'replied' ? '已回复' : '待回复' }}
                  </a-tag>
                </div>
                <p class="message-content">{{ item.content }}</p>

                <div v-if="item.reply_content" class="reply-block">
                  <span class="reply-label">老师回复</span>
                  <p>{{ item.reply_content }}</p>
                  <small v-if="item.reply_timestamp">
                    {{ new Date(item.reply_timestamp).toLocaleString('zh-CN') }}
                  </small>
                </div>
              </article>
            </TransitionGroup>
          </a-card>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { UploadOutlined } from '@ant-design/icons-vue'

export default {
  name: 'StudentView',
  setup() {
    const question = ref('')
    const answer = ref('')
    const streamingAnswer = ref('')
    const loading = ref(false)
    const sources = ref([])
    const history = ref([])
    const messages = ref([])
    const messageToTeacher = ref('')
    const sendingMessage = ref(false)
    const messageSuccess = ref(false)
    const uploadedImage = ref('')

    marked.setOptions({
      breaks: true,
      gfm: true
    })

    const renderLatex = (text) => {
      if (!text) return ''

      let result = text
      result = result.replace(/\\\[([\s\S]+?)\\\]/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: true, throwOnError: false })
        } catch {
          return match
        }
      })
      result = result.replace(/\$\$([\s\S]+?)\$\$/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: true, throwOnError: false })
        } catch {
          return match
        }
      })
      result = result.replace(/\\\(([^)]+?)\\\)/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: false, throwOnError: false })
        } catch {
          return match
        }
      })
      result = result.replace(/\$([^\$\n]+?)\$/g, (match, latex) => {
        try {
          return katex.renderToString(latex.trim(), { displayMode: false, throwOnError: false })
        } catch {
          return match
        }
      })
      return result
    }

    const sanitizeAnswer = (content) =>
      content.replace(/<\|im_end\|>/g, '').replace(/<\|im_start\|>/g, '')

    const renderedAnswer = computed(() => {
      if (!answer.value) return ''
      return marked(renderLatex(sanitizeAnswer(answer.value)))
    })

    const renderedStreamingAnswer = computed(() => {
      if (!streamingAnswer.value) return ''
      return marked(renderLatex(sanitizeAnswer(streamingAnswer.value)))
    })

    const renderHistoryAnswer = (content) => {
      if (!content) return ''
      return marked(renderLatex(sanitizeAnswer(content)))
    }

    const handleImageUpload = (file) =>
      new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (event) => {
          uploadedImage.value = event.target.result
          resolve(false)
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
      })

    const removeImage = () => {
      uploadedImage.value = ''
    }

    const readStreamingResponse = async (response) => {
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
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.token) {
              const token = sanitizeAnswer(data.token)
              if (token) {
                streamingAnswer.value += token
              }
            }
          } catch (error) {
            console.warn('解析流式数据失败:', error)
          }
        }
      }
    }

    const analyzeImageOnly = async () => {
      if (!uploadedImage.value) return

      loading.value = true
      answer.value = ''
      streamingAnswer.value = ''

      try {
        const response = await fetch('/api/multimodal/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: uploadedImage.value.split(',')[1] }),
          credentials: 'include'
        })

        await readStreamingResponse(response)
        answer.value = streamingAnswer.value
        history.value.unshift({
          question: '[图片分析]',
          answer: streamingAnswer.value
        })
      } catch (error) {
        console.error('图片分析失败:', error)
        alert('图片分析失败，请稍后重试。')
      } finally {
        loading.value = false
        streamingAnswer.value = ''
      }
    }

    const submitQuestion = async () => {
      if (!question.value.trim() && !uploadedImage.value) return

      loading.value = true
      answer.value = ''
      streamingAnswer.value = ''

      try {
        const withImage = Boolean(uploadedImage.value)
        const response = await fetch(withImage ? '/api/multimodal/qa' : '/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            withImage
              ? { question: question.value, image: uploadedImage.value.split(',')[1] }
              : { question: question.value }
          ),
          credentials: 'include'
        })

        await readStreamingResponse(response)
        answer.value = streamingAnswer.value
        history.value.unshift({
          question: question.value || '[图片分析]',
          answer: streamingAnswer.value
        })
        question.value = ''
        removeImage()
      } catch (error) {
        console.error('提问失败:', error)
        alert('提问失败，请检查网络或稍后重试。')
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
        await fetchMessages()

        setTimeout(() => {
          messageSuccess.value = false
        }, 3000)
      } catch (error) {
        console.error('发送留言失败:', error)
        alert(error.response?.data?.error || '发送失败，请稍后重试。')
      } finally {
        sendingMessage.value = false
      }
    }

    const fetchQuestionHistory = async () => {
      try {
        const response = await axios.get('/api/student/questions/history')
        history.value = response.data.map((item) => ({
          question: item.question,
          answer: item.answer
        }))
      } catch (error) {
        console.error('加载提问历史失败:', error)
      }
    }

    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data
      } catch (error) {
        console.error('加载留言历史失败:', error)
      }
    }

    onMounted(() => {
      fetchQuestionHistory()
      fetchMessages()
    })

    return {
      question,
      answer,
      streamingAnswer,
      loading,
      sources,
      history,
      messages,
      messageToTeacher,
      sendingMessage,
      messageSuccess,
      uploadedImage,
      UploadOutlined,
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
.workspace-page {
  position: relative;
}

.workspace-shell {
  position: relative;
  z-index: 1;
}

.workspace-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  margin-bottom: 28px;
  padding: 14px 0 8px;
}

.workspace-eyebrow {
  display: inline-flex;
  margin-bottom: 14px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
  animation: revealUp 0.72s ease both;
}

.workspace-hero h1 {
  max-width: 760px;
  margin: 0 0 12px;
  font-size: clamp(30px, 4.5vw, 52px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  animation: revealUp 0.88s ease both;
  animation-delay: 0.08s;
}

.workspace-hero p {
  max-width: 680px;
  margin: 0;
  color: rgba(255, 255, 255, 0.56);
  line-height: 1.8;
  animation: revealUp 1s ease both;
  animation-delay: 0.16s;
}

.workspace-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(120px, 1fr));
  gap: 14px;
  min-width: 280px;
}

.metric-card {
  position: relative;
  overflow: hidden;
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  animation: revealUp 0.95s ease both;
  transition: transform 0.35s ease, border-color 0.35s ease;
}

.metric-card:nth-child(1) {
  animation-delay: 0.22s;
}

.metric-card:nth-child(2) {
  animation-delay: 0.32s;
}

.metric-card::after {
  content: "";
  position: absolute;
  inset: auto -20% -60% auto;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.15), transparent 70%);
  animation: metricGlow 6s ease-in-out infinite;
}

.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.14);
}

.metric-card span {
  display: block;
  color: rgba(255, 255, 255, 0.46);
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 12px;
  font-size: 30px;
  font-weight: 600;
}

.panel-card {
  margin-bottom: 24px;
  animation: revealUp 0.85s ease both;
}

.panel-card:nth-child(1) {
  animation-delay: 0.18s;
}

.panel-card:nth-child(2) {
  animation-delay: 0.26s;
}

.panel-card:nth-child(3) {
  animation-delay: 0.34s;
}

.composer-card :deep(.ant-card-body) {
  padding-top: 20px;
}

.upload-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.upload-tip {
  color: rgba(255, 255, 255, 0.42);
  font-size: 13px;
}

.image-preview {
  margin-top: 16px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.image-preview img {
  display: block;
  width: 100%;
  max-height: 240px;
  object-fit: contain;
  border-radius: 14px;
  margin-bottom: 8px;
}

.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.answer-panel :deep(.ant-card-body) {
  display: grid;
  gap: 20px;
}

.answer-body,
.answer-stream {
  min-height: 160px;
  padding: 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.answer-stream {
  position: relative;
}

.answer-stream::after {
  content: "";
  display: inline-block;
  width: 10px;
  height: 20px;
  margin-left: 6px;
  vertical-align: middle;
  background: rgba(255, 255, 255, 0.86);
  animation: blink 1s infinite;
}

.sources-block {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 4px;
}

.source-item {
  color: rgba(255, 255, 255, 0.62);
}

.history-stack,
.message-stack {
  display: grid;
  gap: 16px;
}

.history-entry,
.message-entry {
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform 0.32s ease, border-color 0.32s ease, background 0.32s ease;
}

.history-entry:hover,
.message-entry:hover {
  transform: translateY(-3px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.045);
}

.history-question {
  margin-bottom: 18px;
}

.history-kicker {
  display: inline-flex;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.history-question h3 {
  margin: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.96);
}

.history-answer {
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
}

.message-content {
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.8;
}

.reply-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.reply-label {
  display: inline-flex;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.reply-block p,
.reply-block small {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.8;
}

.reply-block small {
  display: block;
  margin-top: 8px;
  color: rgba(255, 255, 255, 0.38);
}

.markdown-body {
  font-size: 15px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.8);
  word-break: break-word;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin: 1.2em 0 0.6em;
  color: rgba(255, 255, 255, 0.96);
  line-height: 1.3;
}

.markdown-body p,
.markdown-body ul,
.markdown-body ol,
.markdown-body pre,
.markdown-body blockquote,
.markdown-body table {
  margin: 0 0 16px;
}

.markdown-body code {
  padding: 0.18em 0.45em;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.96);
}

.markdown-body pre {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: auto;
}

.markdown-body pre code {
  padding: 0;
  background: transparent;
}

.markdown-body blockquote {
  padding-left: 16px;
  border-left: 2px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.56);
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
}

.markdown-body th,
.markdown-body td {
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.markdown-body a {
  color: rgba(255, 255, 255, 0.92);
}

.soft-rise-enter-active,
.soft-rise-leave-active,
.stack-reveal-enter-active,
.stack-reveal-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease, filter 0.35s ease;
}

.soft-rise-enter-from,
.soft-rise-leave-to,
.stack-reveal-enter-from,
.stack-reveal-leave-to {
  opacity: 0;
  transform: translateY(16px);
  filter: blur(6px);
}

.stack-reveal-move {
  transition: transform 0.35s ease;
}

@keyframes revealUp {
  from {
    opacity: 0;
    transform: translateY(22px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes metricGlow {
  0%,
  100% {
    transform: scale(0.9);
    opacity: 0.35;
  }
  50% {
    transform: scale(1.18);
    opacity: 0.55;
  }
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}

@media (max-width: 992px) {
  .workspace-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-stats {
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .workspace-stats {
    grid-template-columns: 1fr;
  }

  .upload-row,
  .action-row,
  .message-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
