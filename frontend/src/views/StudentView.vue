<template>
  <div class="workspace-page">
    <student-sidebar
      :history="history"
      :active-id="selectedHistoryId"
      :panel="activePanel"
      :open="sidebarOpen"
      @new-question="startNewQuestion"
      @select="selectHistory"
      @rename="renameHistoryTitle"
      @delete="deleteHistoryRecord"
      @open-plugins="openPlugins"
      @open-workspace="openWorkspace"
    />

    <transition name="soft-rise">
      <div v-if="sidebarOpen" class="sidebar-backdrop" @click="sidebarOpen = false"></div>
    </transition>

    <button class="sidebar-toggle" type="button" aria-label="打开侧边栏" @click="sidebarOpen = !sidebarOpen">
      <menu-outlined />
    </button>

    <div class="workspace-main">
      <div class="container workspace-shell">
        <section v-if="activePanel === 'plugin'" class="plugin-page">
          <header class="plugin-hero">
            <div>
              <div class="workspace-eyebrow">Student Plugins</div>
              <h1>学生插件</h1>
              <p>把学生自己开发的工具、知识库与 Agent 助手接入学习工作区。</p>
            </div>
            <a-button type="primary" @click="showPluginHint">
              <template #icon><plus-outlined /></template>
              添加插件
            </a-button>
          </header>

          <div class="plugin-grid">
            <a-card v-for="plugin in demoPlugins" :key="plugin.name" class="surface-card plugin-card">
              <div class="plugin-card-head">
                <span class="plugin-glyph">{{ plugin.glyph }}</span>
              </div>
              <h3>{{ plugin.name }}</h3>
              <p>{{ plugin.description }}</p>
              <div class="plugin-card-foot">
                <a-button
                  size="small"
                  :type="plugin.installed ? 'default' : 'primary'"
                  :disabled="plugin.installed"
                  @click="showPluginHint"
                >
                  {{ plugin.installed ? '已添加' : '添加' }}
                </a-button>
              </div>
            </a-card>

            <button type="button" class="plugin-add-card" @click="showPluginHint">
              <plus-outlined />
              <span>添加学生插件</span>
            </button>
          </div>
        </section>

        <section v-if="activePanel === 'workspace'" class="workspace-hero">
        <div>
          <div class="workspace-eyebrow">Student Workspace</div>
          <h1>What should we work on?</h1>
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

      <a-row v-if="activePanel === 'workspace'" :gutter="[24, 24]">
        <a-col :xs="24" :xl="16">
          <a-card class="surface-card panel-card composer-card" title="智能提问">
            <a-form layout="vertical">
              <div class="mode-switch">
                <a-radio-group v-model:value="currentMode" size="small">
                  <a-radio-button value="fast">快答</a-radio-button>
                  <a-radio-button value="deep">深度</a-radio-button>
                </a-radio-group>
                <span class="mode-hint">
                  {{ currentMode === 'deep' ? 'Agent 检索 + 卡片化回答' : '直接生成文字回答' }}
                </span>
              </div>

              <answer-style-panel
                v-model:template="selectedTemplate"
                v-model:style="selectedStyle"
                :templates="answerTemplates"
                :styles="answerStyles"
              />

              <a-form-item label="输入问题">
                <a-textarea
                  v-model:value="question"
                  placeholder="输入你想问的问题，或上传图片 / 文件让系统一起分析。"
                  :rows="5"
                />
              </a-form-item>

              <a-form-item label="文件输入（可选）">
                <div class="upload-row">
                  <a-upload
                    :before-upload="handleFileUpload"
                    :show-upload-list="false"
                    accept=".png,.jpg,.jpeg,.gif,.bmp,.webp,.txt,.md,.markdown,.csv,.json,.log"
                  >
                    <a-button>
                      <template #icon><upload-outlined /></template>
                      上传文件
                    </a-button>
                  </a-upload>
                  <span class="upload-tip">支持图片，以及 TXT / MD / CSV / JSON 等文本文件。</span>
                </div>

                <transition name="soft-rise">
                  <div v-if="uploadedFile" class="file-preview">
                    <img v-if="uploadedFile.kind === 'image'" :src="uploadedFile.dataUrl" alt="上传预览" />
                    <div v-else class="file-summary">
                      <div class="file-meta">
                        <span class="file-name">{{ uploadedFile.name }}</span>
                        <span class="file-size">{{ formatFileSize(uploadedFile.size) }} · 已读取文本</span>
                      </div>
                      <pre class="file-text-preview">{{ textPreview }}</pre>
                    </div>
                    <a-button type="link" danger @click="removeFile">移除文件</a-button>
                  </div>
                </transition>
              </a-form-item>

              <div class="action-row">
                <a-button
                  type="primary"
                  @click="submitQuestion"
                  :disabled="(!question.trim() && !uploadedFile) || loading"
                  :loading="loading"
                >
                  {{ loading ? '生成中...' : '发送提问' }}
                </a-button>

                <a-button
                  v-if="uploadedFile && !question.trim()"
                  type="dashed"
                  @click="analyzeFileOnly"
                  :loading="loading"
                >
                  仅分析文件
                </a-button>
              </div>
            </a-form>
          </a-card>

          <transition name="soft-rise">
            <a-card
              v-if="!selectedHistory && (streamingAnswer || answer)"
              class="surface-card panel-card answer-panel"
              title="回答结果"
            >
              <template #extra>
                <div class="answer-copy-toolbar">
                  <a-radio-group v-model:value="copyMode" size="small" button-style="solid">
                    <a-radio-button value="markdown">Markdown</a-radio-button>
                    <a-radio-button value="plain">纯文本</a-radio-button>
                  </a-radio-group>
                  <a-button size="small" @click="copyAnswer" :disabled="!copyableAnswer">
                    <template #icon><copy-outlined /></template>
                    复制
                  </a-button>
                </div>
              </template>
              <div v-if="streamingAnswer" class="answer-stream markdown-body" v-html="renderedStreamingAnswer"></div>
              <div v-else class="answer-body markdown-body" v-html="renderedAnswer"></div>

              <tool-trace
                v-if="agentTrace.length || (loading && agentStatus)"
                :trace="agentTrace"
                :duration-ms="agentDuration"
                :status="loading ? agentStatus : ''"
              />

              <answer-cards
                v-if="agentUi"
                :ui="agentUi"
                :sources="agentSources"
                :chapters="chapterTitles"
                @follow-up="askFollowUp"
              />

              <div v-if="agentSources.length > 0" class="sources-block">
                <a-divider orientation="left">参考来源</a-divider>
                <citation-chips
                  :citations="agentSources.map((source) => source.citation)"
                  :sources="agentSources"
                  @follow-up="askFollowUp"
                />
              </div>

              <div v-if="currentQuestionId" class="privacy-bar">
                <div class="privacy-copy">
                  <lock-outlined v-if="!currentQuestionShared" class="privacy-icon" />
                  <safety-certificate-outlined v-else class="privacy-icon is-accepted" />
                  <span v-if="!currentQuestionShared">
                    这次问答默认<strong>仅自己可见</strong>，不会自动同步给老师。
                  </span>
                  <span v-else-if="currentQuestionAnswered">
                    已提交给老师，老师已回复；这条问答会保留在课程记录中。
                  </span>
                  <span v-else>
                    已提交给老师，老师可以查看并回复；老师回复前可撤回。
                  </span>
                </div>
                <a-button
                  v-if="!currentQuestionShared"
                  type="primary"
                  size="small"
                  :loading="sharingBusy"
                  @click="shareQuestionToTeacher(currentQuestionId)"
                >
                  提交给老师
                </a-button>
                <a-button
                  v-else-if="!currentQuestionAnswered"
                  size="small"
                  :loading="sharingBusy"
                  @click="withdrawQuestionFromTeacher(currentQuestionId)"
                >
                  撤回
                </a-button>
                <a-tag v-else color="green">老师已回复</a-tag>
              </div>
            </a-card>
          </transition>

          <transition name="soft-rise">
            <a-card
              v-if="selectedHistory"
              class="surface-card panel-card history-detail-panel"
              title="历史记录"
            >
              <template #extra>
                <div class="history-detail-actions">
                  <a-button size="small" @click="closeHistoryDetail">返回</a-button>
                  <a-popconfirm
                    title="确定删除这条提问记录吗？"
                    ok-text="删除"
                    cancel-text="取消"
                    @confirm="deleteHistoryRecord(selectedHistory)"
                  >
                    <a-button type="text" danger size="small">
                      <template #icon><delete-outlined /></template>
                      删除
                    </a-button>
                  </a-popconfirm>
                </div>
              </template>

              <div class="history-meta">
                <span>{{ new Date(selectedHistory.timestamp).toLocaleString('zh-CN') }}</span>
                <a-tag :color="selectedHistory.mode === 'deep' ? 'blue' : 'default'">
                  {{ selectedHistory.mode === 'deep' ? '深度' : '快答' }}
                </a-tag>
                <a-tag color="purple">{{ templateLabel(selectedHistory.template) }}</a-tag>
                <a-tag>{{ styleLabel(selectedHistory.style) }}</a-tag>
              </div>

              <div class="history-question">
                <span class="history-kicker">Question</span>
                <h3>{{ selectedHistory.question }}</h3>
              </div>
              <div class="history-answer markdown-body" v-html="renderHistoryAnswer(selectedHistory.answer)"></div>
              <answer-cards
                v-if="selectedHistory.ui"
                :ui="selectedHistory.ui"
                :sources="selectedHistory.trace ? selectedHistory.trace.sources || [] : []"
                :chapters="chapterTitles"
                @follow-up="askFollowUp"
              />
              <tool-trace
                v-if="selectedHistory.trace && selectedHistory.trace.trace && selectedHistory.trace.trace.length"
                :trace="selectedHistory.trace.trace"
                :duration-ms="selectedHistory.trace.durationMs || 0"
                compact
              />

              <div class="privacy-bar privacy-bar-detail">
                <div class="privacy-copy">
                  <lock-outlined v-if="!selectedHistory.shared" class="privacy-icon" />
                  <safety-certificate-outlined v-else class="privacy-icon is-accepted" />
                  <span v-if="!selectedHistory.shared">
                    这条问答默认<strong>仅自己可见</strong>，不会自动同步给老师。
                  </span>
                  <span v-else-if="selectedHistory.authoritative_answer">
                    已提交给老师，老师已回复；该问答会保留在课程记录中。
                  </span>
                  <span v-else>已提交给老师，老师可以查看并回复；老师回复前可撤回。</span>
                </div>
                <a-button
                  v-if="!selectedHistory.shared"
                  type="primary"
                  size="small"
                  :loading="sharingBusy"
                  @click="shareQuestionToTeacher(selectedHistory.id)"
                >
                  提交给老师
                </a-button>
                <a-button
                  v-else-if="!selectedHistory.authoritative_answer"
                  size="small"
                  :loading="sharingBusy"
                  @click="withdrawQuestionFromTeacher(selectedHistory.id)"
                >
                  撤回
                </a-button>
                <a-tag v-else color="green">老师已回复</a-tag>
              </div>
            </a-card>
          </transition>
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
                  <div class="message-actions">
                    <a-tag :color="item.status === 'replied' ? 'success' : 'warning'">
                      {{ item.status === 'replied' ? '已回复' : '待回复' }}
                    </a-tag>
                    <a-popconfirm
                      title="确定删除这条留言记录吗？"
                      ok-text="删除"
                      cancel-text="取消"
                      @confirm="deleteMessageRecord(item)"
                    >
                      <a-button type="text" danger size="small" @click.stop>
                        <template #icon><delete-outlined /></template>
                        删除
                      </a-button>
                    </a-popconfirm>
                  </div>
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
  </div>
</template>

<script>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { message as toast } from 'ant-design-vue'
import { CopyOutlined, DeleteOutlined, LockOutlined, MenuOutlined, PlusOutlined, SafetyCertificateOutlined, UploadOutlined } from '@ant-design/icons-vue'
import AnswerCards from '../components/cards/AnswerCards.vue'
import ToolTrace from '../components/ToolTrace.vue'
import CitationChips from '../components/cards/CitationChips.vue'
import StudentSidebar from '../components/StudentSidebar.vue'
import AnswerStylePanel from '../components/AnswerStylePanel.vue'
import { readEventStream, TOOL_LABELS } from '../utils/sse'
import { validateUI } from '../utils/uiCards'
import { createTypewriter } from '../utils/typewriter'

const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
const TEXT_EXTENSIONS = ['txt', 'md', 'markdown', 'csv', 'json', 'log']
const MAX_TEXT_CHARS = 12000
const MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024

const readFileAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (event) => resolve(event.target.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })

const readFileAsText = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (event) => resolve(event.target.result)
    reader.onerror = reject
    reader.readAsText(file)
  })

export default {
  name: 'StudentView',
  components: {
    CopyOutlined,
    DeleteOutlined,
    MenuOutlined,
    PlusOutlined,
    UploadOutlined,
    AnswerCards,
    ToolTrace,
    CitationChips,
    StudentSidebar,
    AnswerStylePanel
  },
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
    const uploadedFile = ref(null)
    const copyMode = ref('markdown')

    // 侧边栏 / 历史详情 / 学生插件
    const sidebarOpen = ref(false)
    const activePanel = ref('workspace')
    const selectedHistoryId = ref(null)
    const titleRequested = new Set()

    // 隐私边界：问答默认私密，只有学生主动提交后老师才能看到
    const currentQuestionId = ref(null)
    const sharingBusy = ref(false)

    const demoPlugins = [
      {
        glyph: '笔',
        name: '错题本整理器',
        description: '把每次提问中的错误与薄弱点整理进个人错题本，支持按章节回顾。',
        installed: true
      },
      {
        glyph: '式',
        name: '公式推导助手',
        description: '为数学、物理公式提供分步推导、单位校验和常见变式。',
        installed: false
      },
      {
        glyph: '图',
        name: '讲义截图解析',
        description: '读取课堂截图与讲义页面，提炼重点并生成复习卡片。',
        installed: false
      },
      {
        glyph: '划',
        name: '学习计划生成器',
        description: '根据错题记录与课程进度，自动生成一周复习计划。',
        installed: false
      }
    ]

    const selectedHistory = computed(
      () => history.value.find((item) => item.id === selectedHistoryId.value) || null
    )

    const agentUi = ref(null)
    const agentSources = ref([])
    const agentTrace = ref([])
    const agentDuration = ref(0)
    const agentStatus = ref('')
    const currentMode = ref('deep')
    const agentMeta = ref({ uiVersion: 1, modes: ['fast', 'deep'], chapters: [] })

    // 回答效果：模板 × 交流方式（localStorage 记住偏好）
    const ANSWER_MODE_STORAGE_KEY = 'xdwe-answer-mode'
    const DEFAULT_ANSWER_TEMPLATES = [
      { id: 'learn_new', label: '学习新知', description: '先辨析概念边界，再用最小例子和变式题检验理解' },
      { id: 'review_old', label: '复习旧知', description: '先自测回忆，再补易错点和记忆锚点' },
      { id: 'explore_new', label: '探索未知', description: '从已学知识引出未知问题，给延伸方向与资料线索' }
    ]
    const DEFAULT_ANSWER_STYLES = [
      { id: 'short_round', label: '逐轮短对话', description: '每轮只推进一小步，用问题引导你回答' },
      { id: 'long_form', label: '长对话', description: '一次给出尽量完整的知识结构' }
    ]
    const storedAnswerMode = (() => {
      try {
        return JSON.parse(window.localStorage.getItem(ANSWER_MODE_STORAGE_KEY) || 'null')
      } catch (error) {
        return null
      }
    })()
    const selectedTemplate = ref(storedAnswerMode?.template || 'learn_new')
    const selectedStyle = ref(storedAnswerMode?.style || 'long_form')
    const answerTemplates = computed(() => {
      const fromMeta = agentMeta.value.answerModes?.templates
      return Array.isArray(fromMeta) && fromMeta.length ? fromMeta : DEFAULT_ANSWER_TEMPLATES
    })
    const answerStyles = computed(() => {
      const fromMeta = agentMeta.value.answerModes?.styles
      return Array.isArray(fromMeta) && fromMeta.length ? fromMeta : DEFAULT_ANSWER_STYLES
    })
    const templateLabelById = computed(() =>
      Object.fromEntries(answerTemplates.value.map((item) => [item.id, item.label]))
    )
    const styleLabelById = computed(() =>
      Object.fromEntries(answerStyles.value.map((item) => [item.id, item.label]))
    )
    const templateLabel = (id) => templateLabelById.value[id] || '学习新知'
    const styleLabel = (id) => styleLabelById.value[id] || '长对话'

    watch([selectedTemplate, selectedStyle], ([template, style]) => {
      try {
        window.localStorage.setItem(ANSWER_MODE_STORAGE_KEY, JSON.stringify({ template, style }))
      } catch (error) {
        console.warn('保存回答效果偏好失败:', error)
      }
    })

    const chapterTitles = computed(() =>
      Object.fromEntries((agentMeta.value.chapters || []).map((chapter) => [chapter.id, chapter.title]))
    )

    const currentHistoryRecord = computed(
      () => history.value.find((item) => item.id === currentQuestionId.value) || null
    )
    const currentQuestionShared = computed(() => Boolean(currentHistoryRecord.value?.shared))
    const currentQuestionAnswered = computed(() => Boolean(currentHistoryRecord.value?.authoritative_answer))

    // 把网络突发到达的 token 平滑打印出来，避免“等几秒后整段出现”
    const typewriter = createTypewriter((chunk) => {
      streamingAnswer.value += chunk
    })

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

    const copyableAnswer = computed(() => sanitizeAnswer(answer.value || streamingAnswer.value || ''))

    const renderHistoryAnswer = (content) => {
      if (!content) return ''
      return marked(renderLatex(sanitizeAnswer(content)))
    }

    const markdownToPlainText = (content) => {
      const target = document.createElement('div')
      target.innerHTML = marked(renderLatex(sanitizeAnswer(content)))
      return (target.textContent || target.innerText || '').replace(/\n{3,}/g, '\n\n').trim()
    }

    const writeClipboard = async (text) => {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
        return
      }

      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }

    const copyAnswer = async () => {
      if (!copyableAnswer.value) return

      try {
        const text =
          copyMode.value === 'markdown'
            ? copyableAnswer.value
            : markdownToPlainText(copyableAnswer.value)
        await writeClipboard(text)
        toast.success(copyMode.value === 'markdown' ? '已复制 Markdown 回答' : '已复制纯文本回答')
      } catch (error) {
        console.error('复制回答失败:', error)
        toast.error('复制失败，请稍后重试')
      }
    }

    const handleFileUpload = (file) => {
      const extension = (file.name.split('.').pop() || '').toLowerCase()
      const isImage = IMAGE_EXTENSIONS.includes(extension) || (file.type || '').startsWith('image/')
      const isText = TEXT_EXTENSIONS.includes(extension) || (file.type || '').startsWith('text/')

      if (isImage) {
        return readFileAsDataUrl(file)
          .then((dataUrl) => {
            uploadedFile.value = {
              kind: 'image',
              name: file.name,
              size: file.size,
              dataUrl
            }
            return false
          })
          .catch((error) => {
            console.error('读取图片失败:', error)
            toast.error('图片读取失败，请重新选择')
            return false
          })
      }

      if (isText) {
        if (file.size > MAX_TEXT_FILE_BYTES) {
          toast.error(`文本文件过大，请上传小于 ${formatFileSize(MAX_TEXT_FILE_BYTES)} 的文件`)
          return false
        }

        return readFileAsText(file)
          .then((content) => {
            const truncated = content.length > MAX_TEXT_CHARS
            uploadedFile.value = {
              kind: 'text',
              name: file.name,
              size: file.size,
              text: truncated ? content.slice(0, MAX_TEXT_CHARS) : content
            }
            if (truncated) {
              toast.info(`文件较长，已截取前 ${MAX_TEXT_CHARS} 个字符交给 AI 分析`)
            }
            return false
          })
          .catch((error) => {
            console.error('读取文本文件失败:', error)
            toast.error('文件读取失败，请重试')
            return false
          })
      }

      toast.error('暂不支持该文件格式，请上传图片或 TXT / MD / CSV / JSON 文件')
      return false
    }

    const removeFile = () => {
      uploadedFile.value = null
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const units = ['B', 'KB', 'MB']
      let value = bytes
      let unitIndex = 0
      while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024
        unitIndex += 1
      }
      return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
    }

    const textPreview = computed(() => {
      if (uploadedFile.value?.kind !== 'text') return ''
      const content = uploadedFile.value.text
      return content.length > 260 ? `${content.slice(0, 260)}…` : content
    })

    const buildFilePayload = () => {
      if (uploadedFile.value?.kind !== 'text') return null
      return { name: uploadedFile.value.name, content: uploadedFile.value.text }
    }

    const resetAgentState = () => {
      typewriter.reset()
      currentQuestionId.value = null
      agentUi.value = null
      agentSources.value = []
      agentTrace.value = []
      agentDuration.value = 0
      agentStatus.value = ''
    }

    const consumeStream = async (response) => {
      let serverError = ''
      let completedEvent = null

      await readEventStream(response, (event) => {
        switch (event.type) {
          case 'start':
            agentStatus.value = event.mode === 'deep' ? '正在检索和思考…' : '正在生成回答…'
            break
          case 'status':
            agentStatus.value = event.message || ''
            break
          case 'tool_call':
            agentStatus.value = TOOL_LABELS[event.name] || '正在调用工具…'
            break
          case 'tool_result':
            agentStatus.value = event.summary || agentStatus.value
            break
          case 'answer_delta':
            typewriter.push(sanitizeAnswer(event.text || ''))
            break
          case 'answer_reset':
            typewriter.reset()
            streamingAnswer.value = ''
            break
          case 'ui':
            agentUi.value = event.ui || null
            break
          case 'complete':
            completedEvent = event
            break
          case 'done':
            if (event.messageId) currentQuestionId.value = event.messageId
            break
          case 'error':
            serverError = event.message || 'AI 服务暂时不可用'
            break
          default:
            break
        }
      })

      if (serverError) {
        typewriter.flush()
        throw new Error(serverError)
      }

      // 等打字机把缓冲吐完，再切到最终回答，避免最后一段“跳变”
      await typewriter.drained()

      if (completedEvent) {
        answer.value = completedEvent.answer || streamingAnswer.value
        agentSources.value = completedEvent.sources || []
        agentTrace.value = completedEvent.trace || []
        agentDuration.value = completedEvent.durationMs || 0
        if (agentUi.value) {
          const chapterSet = new Set(Object.keys(chapterTitles.value))
          agentUi.value = validateUI(agentUi.value, agentSources.value, chapterSet).ui
        }
      }
      if (!answer.value) answer.value = streamingAnswer.value
    }

    const analyzeFileOnly = async () => {
      const file = uploadedFile.value
      if (!file) return

      loading.value = true
      selectedHistoryId.value = null
      answer.value = ''
      streamingAnswer.value = ''
      resetAgentState()

      try {
        const isImage = file.kind === 'image'
        const response = await fetch(isImage ? '/api/multimodal/qa' : '/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isImage
              ? {
                  image: file.dataUrl.split(',')[1],
                  mode: 'fast',
                  uiVersion: 1,
                  template: selectedTemplate.value,
                  style: selectedStyle.value
                }
              : {
                  question: '',
                  file: buildFilePayload(),
                  mode: currentMode.value,
                  uiVersion: 1,
                  template: selectedTemplate.value,
                  style: selectedStyle.value
                }
          ),
          credentials: 'include'
        })

        await consumeStream(response)
        answer.value = streamingAnswer.value
        await fetchQuestionHistory()
      } catch (error) {
        // 保留已生成的部分回答，避免网络中断时内容凭空消失
        answer.value = streamingAnswer.value || ''
        console.error('文件分析失败:', error)
        alert(error.message || '文件分析失败，请稍后重试。')
      } finally {
        loading.value = false
        streamingAnswer.value = ''
      }
    }

    const submitQuestion = async () => {
      if (!question.value.trim() && !uploadedFile.value) return

      loading.value = true
      selectedHistoryId.value = null
      answer.value = ''
      streamingAnswer.value = ''
      resetAgentState()

      try {
        const file = uploadedFile.value
        const withImage = file?.kind === 'image'
        const payload = withImage
          ? {
              question: question.value,
              image: file.dataUrl.split(',')[1],
              mode: 'fast',
              uiVersion: 1,
              template: selectedTemplate.value,
              style: selectedStyle.value
            }
          : {
              question: question.value,
              mode: currentMode.value,
              uiVersion: 1,
              template: selectedTemplate.value,
              style: selectedStyle.value
            }
        const filePayload = buildFilePayload()
        if (filePayload) payload.file = filePayload

        const response = await fetch(withImage ? '/api/multimodal/qa' : '/api/qa', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          credentials: 'include'
        })

        await consumeStream(response)
        answer.value = streamingAnswer.value
        await fetchQuestionHistory()
        question.value = ''
        removeFile()
      } catch (error) {
        // 保留已生成的部分回答，避免网络中断时内容凭空消失
        answer.value = streamingAnswer.value || ''
        console.error('提问失败:', error)
        alert(error.message || '提问失败，请检查网络或稍后重试。')
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
        const chapterSet = new Set(Object.keys(chapterTitles.value))
        history.value = response.data.map((item) => {
          const trace = item.trace || null
          const sources = (trace && trace.sources) || []
          const validated = item.ui ? validateUI(item.ui, sources, chapterSet).ui : null
          return {
            id: item.id,
            question: item.question,
            title: item.title || '',
            answer: item.answer,
            timestamp: item.timestamp,
            mode: item.mode || 'fast',
            template: item.template || 'learn_new',
            style: item.style || 'long_form',
            authoritative_answer: item.authoritative_answer || '',
            shared: Boolean(item.shared),
            shared_at: item.shared_at || null,
            ui: validated,
            trace
          }
        })
        // 历史标题由 LLM 懒生成：缺失标题的记录在后台补全，不阻塞页面渲染
        backfillHistoryTitles()
      } catch (error) {
        console.error('加载提问历史失败:', error)
      }
    }

    // 旧记录 / 生成失败的记录：逐条请求后端用 LLM 补一个标题
    const backfillHistoryTitles = async () => {
      const pending = history.value
        .filter((item) => item.id && !item.title && !titleRequested.has(item.id))
        .slice(0, 12)

      for (const item of pending) {
        titleRequested.add(item.id)
        try {
          const response = await axios.post(`/api/questions/${item.id}/title`)
          const title = response.data?.title
          if (!title) continue
          item.title = title
          const current = history.value.find((record) => record.id === item.id)
          if (current) current.title = title
        } catch (error) {
          console.error('生成历史标题失败:', error)
        }
      }
    }

    const selectHistory = (item) => {
      if (!item || loading.value) return
      activePanel.value = 'workspace'
      selectedHistoryId.value = item.id
      closeSidebar()
      nextTick(() => {
        document.querySelector('.history-detail-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }

    const closeHistoryDetail = () => {
      selectedHistoryId.value = null
    }

    const closeSidebar = () => {
      sidebarOpen.value = false
    }

    const openWorkspace = () => {
      activePanel.value = 'workspace'
      closeSidebar()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const openPlugins = () => {
      activePanel.value = 'plugin'
      closeSidebar()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const startNewQuestion = () => {
      if (loading.value) {
        toast.info('正在生成回答，请稍候')
        return
      }
      activePanel.value = 'workspace'
      selectedHistoryId.value = null
      question.value = ''
      answer.value = ''
      streamingAnswer.value = ''
      resetAgentState()
      removeFile()
      closeSidebar()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const renameHistoryTitle = async (id, title) => {
      const item = history.value.find((record) => record.id === id)
      if (!item) return

      const previousTitle = item.title
      item.title = title
      try {
        const response = await axios.patch(`/api/questions/${id}/title`, { title })
        item.title = response.data?.title || title
        toast.success('标题已更新')
      } catch (error) {
        console.error('修改标题失败:', error)
        item.title = previousTitle
        toast.error(error.response?.data?.error || '标题更新失败，请稍后重试')
      }
    }

    const deleteHistoryRecord = async (item) => {
      if (!item?.id) return
      await deleteQuestionRecord(item)
      if (selectedHistoryId.value === item.id) selectedHistoryId.value = null
    }

    const showPluginHint = () => {
      toast.info('插件安装将在后续版本开放')
    }

    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data
      } catch (error) {
        console.error('加载留言历史失败:', error)
      }
    }

    const shareQuestionToTeacher = async (questionId) => {
      if (!questionId || sharingBusy.value) return
      sharingBusy.value = true
      try {
        const response = await axios.post(`/api/questions/${questionId}/share`)
        toast.success(response.data?.message || '已提交给老师')
        await fetchQuestionHistory()
      } catch (error) {
        console.error('提交给老师失败:', error)
        toast.error(error.response?.data?.error || '提交失败，请稍后重试')
      } finally {
        sharingBusy.value = false
      }
    }

    const withdrawQuestionFromTeacher = async (questionId) => {
      if (!questionId || sharingBusy.value) return
      sharingBusy.value = true
      try {
        const response = await axios.delete(`/api/questions/${questionId}/share`)
        toast.success(response.data?.message || '已撤回')
        await fetchQuestionHistory()
      } catch (error) {
        console.error('撤回失败:', error)
        toast.error(error.response?.data?.error || '撤回失败，请稍后重试')
      } finally {
        sharingBusy.value = false
      }
    }

    const deleteQuestionRecord = async (item) => {
      if (!item.id) return

      try {
        await axios.delete(`/api/questions/${item.id}`)
        history.value = history.value.filter((record) => record.id !== item.id)
        toast.success('提问记录已删除')
      } catch (error) {
        console.error('删除提问记录失败:', error)
        toast.error(error.response?.data?.error || '删除失败，请稍后重试')
      }
    }

    const deleteMessageRecord = async (item) => {
      if (!item.id) return

      try {
        await axios.delete(`/api/messages/${item.id}`)
        messages.value = messages.value.filter((record) => record.id !== item.id)
        toast.success('留言记录已删除')
      } catch (error) {
        console.error('删除留言记录失败:', error)
        toast.error(error.response?.data?.error || '删除失败，请稍后重试')
      }
    }

    const fetchAgentMeta = async () => {
      try {
        const response = await axios.get('/api/agent/meta')
        agentMeta.value = response.data || agentMeta.value
      } catch (error) {
        console.error('加载 Agent 配置失败:', error)
      }
    }

    const askFollowUp = async (prompt) => {
      if (!prompt) return
      question.value = prompt
      await submitQuestion()
    }

    onMounted(async () => {
      await fetchAgentMeta()
      await fetchQuestionHistory()
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
      uploadedFile,
      copyMode,
      UploadOutlined,
      CopyOutlined,
      DeleteOutlined,
      sidebarOpen,
      activePanel,
      selectedHistoryId,
      selectedHistory,
      demoPlugins,
      startNewQuestion,
      openWorkspace,
      openPlugins,
      selectHistory,
      closeHistoryDetail,
      renameHistoryTitle,
      deleteHistoryRecord,
      showPluginHint,
      submitQuestion,
      sendMessageToTeacher,
      handleFileUpload,
      removeFile,
      analyzeFileOnly,
      formatFileSize,
      textPreview,
      copyAnswer,
      deleteQuestionRecord,
      deleteMessageRecord,
      copyableAnswer,
      renderedAnswer,
      renderedStreamingAnswer,
      renderHistoryAnswer,
      agentUi,
      agentSources,
      agentTrace,
      agentDuration,
      agentStatus,
      currentMode,
      agentMeta,
      chapterTitles,
      askFollowUp,
      selectedTemplate,
      selectedStyle,
      answerTemplates,
      answerStyles,
      templateLabel,
      styleLabel,
      currentQuestionId,
      currentQuestionShared,
      currentQuestionAnswered,
      sharingBusy,
      shareQuestionToTeacher,
      withdrawQuestionFromTeacher
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

.file-preview {
  margin-top: 16px;
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.file-preview img {
  display: block;
  width: 100%;
  max-height: 240px;
  object-fit: contain;
  border-radius: 14px;
  margin-bottom: 8px;
}

.file-summary {
  margin-bottom: 8px;
}

.file-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 10px;
}

.file-name {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
  word-break: break-all;
}

.file-size {
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
}

.file-text-preview {
  max-height: 180px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.66);
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.answer-copy-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
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

.history-question {
  margin-bottom: 18px;
  min-width: 0;
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

.message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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
  .answer-copy-toolbar,
  .message-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
.mode-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.mode-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

/* ========================== 左侧边栏 / 历史详情 / 学生插件 ========================== */
.workspace-main {
  min-height: 100%;
}

.sidebar-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  background: rgba(15, 15, 16, 0.86);
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  cursor: pointer;
}

.sidebar-backdrop {
  position: fixed;
  inset: 76px 0 0 0;
  z-index: 25;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
}

.history-detail-panel :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.history-detail-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.38);
  font-size: 12px;
}

.history-detail-panel .history-question {
  margin-bottom: 0;
}

.plugin-page {
  padding-top: 14px;
}

.plugin-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 28px;
}

.plugin-hero h1 {
  margin: 0 0 12px;
  font-size: clamp(30px, 4.5vw, 52px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  animation: revealUp 0.88s ease both;
}

.plugin-hero p {
  max-width: 640px;
  margin: 0;
  color: rgba(255, 255, 255, 0.56);
  line-height: 1.8;
}

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.plugin-card {
  animation: revealUp 0.82s ease both;
}

.plugin-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
}

.plugin-card h3 {
  margin: 0;
  color: rgba(255, 255, 255, 0.95);
  font-size: 18px;
}

.plugin-card p {
  min-height: 66px;
  margin: 0;
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  line-height: 1.7;
}

.plugin-card-head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.plugin-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.06));
  color: #0b0b0b;
  font-weight: 600;
}

.plugin-card-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.plugin-add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 220px;
  padding: 24px;
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.015);
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease, transform 0.25s ease;
}

.plugin-add-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.8);
  transform: translateY(-3px);
}

@media (min-width: 1025px) {
  .workspace-page {
    padding-left: 280px;
  }
}

@media (max-width: 1024px) {
  .sidebar-toggle {
    display: inline-flex;
    position: fixed;
    top: 88px;
    left: 14px;
    z-index: 24;
  }

  .workspace-main {
    padding-top: 34px;
  }

  .plugin-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .sidebar-toggle {
    top: 84px;
  }
}
.privacy-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}

.privacy-bar-detail {
  margin-top: 16px;
}

.privacy-copy {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  font-size: 12px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.55);
}

.privacy-copy strong {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
}

.privacy-icon {
  flex: none;
  margin-top: 3px;
  color: rgba(255, 200, 120, 0.85);
}

.privacy-icon.is-accepted {
  color: rgba(140, 220, 160, 0.9);
}
</style>
