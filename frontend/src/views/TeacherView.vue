<template>
  <div class="teacher-page">
    <div class="container teacher-shell">
      <section class="teacher-hero">
        <div>
          <div class="teacher-eyebrow">Teacher Console</div>
          <h1>轻松掌握学生学习状态。</h1>
          <p>
            把统计、待处理问题与留言回复集中到同一工作台，信息更清晰，决策更直接。
          </p>
        </div>
      </section>

      <transition name="soft-rise">
        <a-spin v-if="loading" tip="数据加载中..." class="teacher-loading" />
      </transition>
      <transition name="soft-rise">
        <a-alert v-if="error" type="error" message="加载失败" :description="error" show-icon class="teacher-error" />
      </transition>

      <a-row :gutter="[24, 24]">
        <a-col :xs="24" :xl="16">
          <div class="stats-grid">
            <a-card class="surface-card stat-tile">
              <span>总提问数</span>
              <strong>{{ stats.total_questions || 0 }}</strong>
            </a-card>
            <a-card class="surface-card stat-tile">
              <span>活跃学生数</span>
              <strong>{{ Object.keys(stats.questions_by_student || {}).length }}</strong>
            </a-card>
          </div>

          <a-card v-if="stats.summary" class="surface-card teacher-card" title="AI 学情分析">
            <div class="summary-content markdown-body" v-html="renderMarkdown(stats.summary)"></div>
          </a-card>

          <a-card class="surface-card teacher-card" title="待处理权威答案">
            <template #extra>
              <a-button type="primary" size="small" @click="fetchPendingQuestions">刷新</a-button>
            </template>

            <a-empty v-if="pendingQuestions.length === 0" description="当前没有待处理问题" />

            <a-collapse v-else v-model:activeKey="activeQuestionKeys" accordion>
              <a-collapse-panel
                v-for="item in pendingQuestions"
                :key="item.id"
                :header="`${item.student_name} · ${item.content.substring(0, 28)}...`"
              >
                <div class="qa-block">
                  <span class="block-label">学生问题</span>
                  <p>{{ item.content }}</p>
                </div>

                <div class="qa-block">
                  <span class="block-label">AI 初步回答</span>
                  <div class="answer-box">{{ item.ai_answer }}</div>
                </div>

                <div v-if="item.authoritative_answer" class="qa-block">
                  <span class="block-label">已提交权威答案</span>
                  <div class="answer-box">{{ item.authoritative_answer }}</div>
                </div>

                <div v-else class="qa-block">
                  <span class="block-label">提交权威答案</span>
                  <a-textarea
                    v-model:value="item.newAuthAnswer"
                    placeholder="在这里写入你希望学生最终看到的答案。"
                    :rows="4"
                  />
                  <a-button
                    type="primary"
                    class="submit-answer"
                    @click="submitAuthAnswer(item)"
                    :disabled="!item.newAuthAnswer || !item.newAuthAnswer.trim()"
                  >
                    设为权威答案
                  </a-button>
                </div>

                <div class="qa-actions">
                  <a-popconfirm
                    title="确定删除这条问答吗？删除后不会进入权威答案处理。"
                    ok-text="删除"
                    cancel-text="取消"
                    @confirm="deletePendingQuestion(item)"
                  >
                    <a-button danger @click.stop>
                      <template #icon><delete-outlined /></template>
                      删除该问答
                    </a-button>
                  </a-popconfirm>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </a-card>

          <a-card class="surface-card teacher-card" title="学生学习分析">
            <a-empty
              v-if="!stats.questions_by_student || Object.keys(stats.questions_by_student).length === 0"
              description="暂无学生提问数据"
            />

            <a-collapse v-else v-model:activeKey="activeStudentKeys" accordion>
              <a-collapse-panel
                v-for="(questions, studentName) in stats.questions_by_student"
                :key="studentName"
                :header="`${studentName} · 提问 ${questions.length} 次`"
              >
                <div class="student-summary">
                  <span class="block-label">学习概览</span>
                  <div
                    v-if="stats.student_summaries && stats.student_summaries[studentName]"
                    class="student-summary-content markdown-body"
                    v-html="renderMarkdown(stats.student_summaries[studentName])"
                  ></div>
                  <p v-else>暂时没有总结内容。</p>
                </div>

                <div class="question-list">
                  <article v-for="(item, index) in questions" :key="index" class="question-entry">
                    <span class="question-index">Q{{ index + 1 }}</span>
                    <p>{{ item.question }}</p>
                  </article>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </a-card>
        </a-col>

        <a-col :xs="24" :xl="8">
          <a-card class="surface-card teacher-card" title="学生留言与回复">
            <a-empty v-if="messages.length === 0" description="暂无学生留言" />

            <TransitionGroup v-else name="stack-reveal" tag="div" class="message-stack">
              <article v-for="item in messages" :key="item.id" class="message-entry">
                <div class="message-head">
                  <div>
                    <strong>{{ item.sender }}</strong>
                    <small>{{ item.timestamp }}</small>
                  </div>
                </div>

                <p class="message-content">{{ item.content }}</p>

                <div v-if="item.reply_content" class="reply-box">
                  <span class="block-label">你的回复</span>
                  <p>{{ item.reply_content }}</p>
                </div>

                <div v-else class="reply-editor">
                  <a-textarea
                    v-model:value="item.newReply"
                    placeholder="输入回复内容..."
                    :rows="3"
                  />
                  <a-button
                    type="primary"
                    @click="replyToMessage(item)"
                    :disabled="!item.newReply || !item.newReply.trim()"
                  >
                    发送回复
                  </a-button>
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
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { message as toast } from 'ant-design-vue'
import { DeleteOutlined } from '@ant-design/icons-vue'

export default {
  name: 'TeacherView',
  components: {
    DeleteOutlined
  },
  setup() {
    const stats = ref({})
    const pendingQuestions = ref([])
    const messages = ref([])
    const loading = ref(false)
    const error = ref('')
    const activeQuestionKeys = ref([])
    const activeStudentKeys = ref([])

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

    const sanitizeMarkdown = (content) =>
      String(content || '')
        .replace(/<\|im_end\|>/g, '')
        .replace(/<\|im_start\|>/g, '')

    const renderMarkdown = (content) => {
      if (!content) return ''
      return marked(renderLatex(sanitizeMarkdown(content)))
    }

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

    const fetchPendingQuestions = async () => {
      try {
        const response = await axios.get('/api/questions/pending')
        pendingQuestions.value = response.data.map((item) => ({ ...item, newAuthAnswer: '' }))
      } catch (err) {
        console.error('获取问题列表失败:', err)
      }
    }

    const submitAuthAnswer = async (question) => {
      if (!question.newAuthAnswer || !question.newAuthAnswer.trim()) return

      try {
        await axios.post(`/api/questions/${question.id}/authoritative`, {
          answer: question.newAuthAnswer
        })
        question.authoritative_answer = question.newAuthAnswer
        question.newAuthAnswer = ''
      } catch (err) {
        console.error('提交权威答案失败:', err)
      }
    }

    const deletePendingQuestion = async (question) => {
      try {
        await axios.delete(`/api/questions/${question.id}`)
        pendingQuestions.value = pendingQuestions.value.filter((item) => item.id !== question.id)
        await fetchStats()
        toast.success('问答已删除')
      } catch (err) {
        console.error('删除问答失败:', err)
        toast.error(err.response?.data?.error || '删除失败，请稍后重试')
      }
    }

    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data.map((item) => ({ ...item, newReply: '' }))
      } catch (err) {
        console.error('获取留言失败:', err)
      }
    }

    const replyToMessage = async (msg) => {
      try {
        await axios.post(`/api/messages/${msg.id}/reply`, {
          reply_content: msg.newReply
        })
        msg.reply_content = msg.newReply
        msg.newReply = ''
      } catch (err) {
        console.error('回复留言失败:', err)
      }
    }

    onMounted(() => {
      fetchStats()
      fetchPendingQuestions()
      fetchMessages()
    })

    return {
      stats,
      pendingQuestions,
      messages,
      loading,
      error,
      activeQuestionKeys,
      activeStudentKeys,
      DeleteOutlined,
      renderMarkdown,
      fetchPendingQuestions,
      submitAuthAnswer,
      deletePendingQuestion,
      replyToMessage
    }
  }
}
</script>

<style scoped>
.teacher-shell {
  position: relative;
  z-index: 1;
}

.teacher-hero {
  margin-bottom: 28px;
  padding: 16px 0 8px;
}

.teacher-eyebrow {
  display: inline-flex;
  margin-bottom: 14px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
  animation: revealUp 0.7s ease both;
}

.teacher-hero h1 {
  max-width: 920px;
  margin: 0 0 12px;
  font-size: clamp(30px, 4.3vw, 50px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  animation: revealUp 0.88s ease both;
  animation-delay: 0.08s;
}

.teacher-hero p {
  max-width: 760px;
  margin: 0;
  color: rgba(255, 255, 255, 0.56);
  line-height: 1.8;
  animation: revealUp 1s ease both;
  animation-delay: 0.16s;
}

.teacher-loading,
.teacher-error {
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-tile {
  animation: revealUp 0.9s ease both;
}

.stat-tile:nth-child(1) {
  animation-delay: 0.2s;
}

.stat-tile:nth-child(2) {
  animation-delay: 0.3s;
}

.stat-tile :deep(.ant-card-body) {
  padding: 24px;
}

.stat-tile span {
  display: block;
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

.stat-tile strong {
  display: block;
  margin-top: 14px;
  font-size: 36px;
  font-weight: 600;
}

.teacher-card {
  margin-bottom: 24px;
  animation: revealUp 0.95s ease both;
}

.teacher-card:nth-of-type(2) {
  animation-delay: 0.24s;
}

.teacher-card:nth-of-type(3) {
  animation-delay: 0.32s;
}

.summary-content {
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.78);
}

.student-summary-content {
  color: rgba(255, 255, 255, 0.76);
}

.markdown-body {
  font-size: 15px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.78);
  word-break: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 1.1em 0 0.55em;
  color: rgba(255, 255, 255, 0.96);
  line-height: 1.35;
}

.markdown-body :deep(h1) {
  font-size: 24px;
}

.markdown-body :deep(h2) {
  font-size: 21px;
}

.markdown-body :deep(h3) {
  font-size: 18px;
}

.markdown-body :deep(p),
.markdown-body :deep(ul),
.markdown-body :deep(ol),
.markdown-body :deep(pre),
.markdown-body :deep(blockquote),
.markdown-body :deep(table) {
  margin: 0 0 16px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
}

.markdown-body :deep(li + li) {
  margin-top: 6px;
}

.markdown-body :deep(hr) {
  margin: 24px 0;
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.markdown-body :deep(strong) {
  color: rgba(255, 255, 255, 0.94);
  font-weight: 700;
}

.markdown-body :deep(code) {
  padding: 0.18em 0.45em;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.96);
}

.markdown-body :deep(pre) {
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: auto;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: transparent;
}

.markdown-body :deep(blockquote) {
  padding-left: 16px;
  border-left: 2px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.58);
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.markdown-body :deep(.katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 6px 0;
}

.qa-block,
.student-summary {
  margin-bottom: 18px;
}

.block-label {
  display: inline-flex;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.qa-block p,
.student-summary p {
  margin: 0;
  color: rgba(255, 255, 255, 0.76);
  line-height: 1.8;
}

.answer-box {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.76);
  line-height: 1.8;
  white-space: pre-wrap;
  transition: transform 0.32s ease, border-color 0.32s ease;
}

.answer-box:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.14);
}

.submit-answer {
  margin-top: 14px;
}

.qa-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.question-list {
  display: grid;
  gap: 12px;
}

.question-entry {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform 0.32s ease, border-color 0.32s ease, background 0.32s ease;
}

.question-entry:hover {
  transform: translateY(-3px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.045);
}

.question-index {
  color: rgba(255, 255, 255, 0.38);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.question-entry p {
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.8;
}

.message-stack {
  display: grid;
  gap: 16px;
}

.message-entry {
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: transform 0.32s ease, border-color 0.32s ease, background 0.32s ease;
}

.message-entry:hover {
  transform: translateY(-3px);
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.045);
}

.message-head strong {
  display: block;
  color: rgba(255, 255, 255, 0.95);
  font-size: 16px;
}

.message-head small {
  color: rgba(255, 255, 255, 0.38);
  font-size: 12px;
}

.message-content {
  margin: 14px 0 0;
  color: rgba(255, 255, 255, 0.76);
  line-height: 1.8;
}

.reply-box,
.reply-editor {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.reply-box p {
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.8;
}

.reply-editor .ant-btn {
  margin-top: 12px;
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

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .question-entry {
    grid-template-columns: 1fr;
  }
}
</style>
