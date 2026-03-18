<template>
  <a-layout class="teacher-container">
    <a-layout-content>
      <a-row :gutter="[16, 16]" style="padding: 24px;">
        <!-- 左侧：问答情况 -->
        <a-col :xs="24" :lg="16">
          <!-- 数据概览卡片 -->
          <a-row :gutter="[16, 16]" style="margin-bottom: 16px;">
            <a-col :xs="12" :sm="12">
              <a-card>
                <a-statistic 
                  title="总提问数" 
                  :value="stats.total_questions || 0"
                  :value-style="{ color: '#3f8600' }"
                />
              </a-card>
            </a-col>
            <a-col :xs="12" :sm="12">
              <a-card>
                <a-statistic 
                  title="活跃学生数" 
                  :value="Object.keys(stats.questions_by_student || {}).length"
                  :value-style="{ color: '#1890ff' }"
                />
              </a-card>
            </a-col>
          </a-row>
          
          <!-- AI总结报告 -->
          <a-card v-if="stats.summary" title="📊 AI 学习情况总结" style="margin-bottom: 16px;">
            <div class="summary-content">
              {{ stats.summary }}
            </div>
          </a-card>
          
          <!-- 权威答案管理 -->
          <a-card title="📝 权威答案管理" style="margin-bottom: 16px;">
            <template #extra>
              <a-button type="primary" size="small" @click="fetchPendingQuestions">
                刷新
              </a-button>
            </template>
            
            <a-empty v-if="pendingQuestions.length === 0" description="暂无待处理问题" />
            
            <a-collapse v-else v-model:activeKey="activeQuestionKeys" accordion>
              <a-collapse-panel 
                v-for="item in pendingQuestions" 
                :key="item.id" 
                :header="`来自: ${item.student_name} - ${item.content.substring(0, 30)}...`"
              >
                <p><strong>问题:</strong> {{ item.content }}</p>
                
                <a-divider orientation="left">AI初步答案</a-divider>
                <div class="answer-content">{{ item.ai_answer }}</div>
                
                <div v-if="item.authoritative_answer" style="margin-top: 16px;">
                  <a-divider orientation="left">✅ 已设权威答案</a-divider>
                  <div class="answer-content">{{ item.authoritative_answer }}</div>
                </div>
                
                <div v-else style="margin-top: 16px;">
                  <a-divider orientation="left">提交权威答案</a-divider>
                  <a-form layout="vertical">
                    <a-form-item label="权威答案">
                      <a-textarea
                        v-model:value="item.newAuthAnswer"
                        placeholder="在此输入您的权威答案..."
                        :rows="3"
                      />
                    </a-form-item>
                    <a-form-item>
                      <a-button 
                        type="primary" 
                        @click="submitAuthAnswer(item)"
                        :disabled="!item.newAuthAnswer || !item.newAuthAnswer.trim()"
                      >
                        提交为权威答案
                      </a-button>
                    </a-form-item>
                  </a-form>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </a-card>
          
          <!-- 学生提问详情 -->
          <a-card title="👨‍🎓 学生学习情况分析">
            <a-empty v-if="!stats.questions_by_student || Object.keys(stats.questions_by_student).length === 0" description="暂无学生提问数据" />
            
            <a-collapse v-else v-model:activeKey="activeStudentKeys" accordion>
              <a-collapse-panel 
                v-for="(questions, studentName) in stats.questions_by_student" 
                :key="studentName" 
                :header="`${studentName} (提问次数: ${questions.length})`"
              >
                <div class="student-summary">
                  <strong>AI 学习情况分析：</strong>
                  <p v-if="stats.student_summaries && stats.student_summaries[studentName]">
                    {{ stats.student_summaries[studentName] }}
                  </p>
                  <p v-else>暂无分析</p>
                </div>
                
                <a-divider orientation="left">提问记录</a-divider>
                <a-list
                  item-layout="horizontal"
                  :data-source="questions"
                >
                  <template #renderItem="{ item, index }">
                    <a-list-item>
                      <a-list-item-meta
                        :description="item.question"
                      >
                        <template #title>
                          <span>Q{{ index + 1 }}</span>
                        </template>
                      </a-list-item-meta>
                    </a-list-item>
                  </template>
                </a-list>
              </a-collapse-panel>
            </a-collapse>
          </a-card>
        </a-col>

        <!-- 右侧：留言管理 -->
        <a-col :xs="24" :lg="8">
          <a-card title="💬 学生留言与回复">
            <a-empty v-if="messages.length === 0" description="暂无学生留言" />
            
            <a-list v-else
              item-layout="vertical"
              :data-source="messages"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-card size="small">
                    <template #title>
                      <span>{{ item.sender }} 留言</span>
                    </template>
                    <template #extra>
                      <span style="font-size: 12px; color: #999;">{{ item.timestamp }}</span>
                    </template>
                    <p>{{ item.content }}</p>
                    
                    <div v-if="item.reply_content" style="margin-top: 12px;">
                      <a-divider style="margin: 8px 0;" />
                      <p><strong>您的回复:</strong> {{ item.reply_content }}</p>
                    </div>
                    
                    <div v-else style="margin-top: 12px;">
                      <a-textarea
                        v-model:value="item.newReply"
                        placeholder="输入回复内容..."
                        :rows="2"
                        style="margin-bottom: 8px;"
                      />
                      <a-button 
                        type="primary" 
                        size="small"
                        @click="replyToMessage(item)"
                        :disabled="!item.newReply || !item.newReply.trim()"
                      >
                        发送回复
                      </a-button>
                    </div>
                  </a-card>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
      
      <!-- 加载和错误状态 -->
      <a-spin v-if="loading" tip="数据加载中..." style="display: block; text-align: center; margin: 24px 0;">
      </a-spin>
      <a-alert 
        v-if="error" 
        type="error" 
        message="错误" 
        :description="error"
        show-icon
        style="margin: 24px;"
      />
    </a-layout-content>
  </a-layout>
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
    const activeQuestionKeys = ref([])
    const activeStudentKeys = ref([])

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
        pendingQuestions.value = response.data.map(q => ({ ...q, newAuthAnswer: '' }))
      } catch (err) {
        console.error('获取问题列表失败:', err)
      }
    }

    const submitAuthAnswer = async (question) => {
      if (!question.newAuthAnswer || !question.newAuthAnswer.trim()) {
        return
      }
      try {
        await axios.post(`/api/questions/${question.id}/authoritative`, {
          answer: question.newAuthAnswer
        })
        question.authoritative_answer = question.newAuthAnswer
        question.newAuthAnswer = ''
      } catch (err) {
        console.error('提交失败:', err)
      }
    }

    const fetchMessages = async () => {
      try {
        const response = await axios.get('/api/messages')
        messages.value = response.data.map(m => ({ ...m, newReply: '' }))
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
        console.error('回复失败:', err)
      }
    }

    const logout = async () => {
      try {
        await axios.post('/api/logout')
      } catch (error) {
        console.error('老师登出失败:', error)
      } finally {
        router.push('/login')
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
  min-height: 100vh;
  background: #0a0a0a;
}

.summary-content {
  line-height: 1.6;
  color: #e0e0e0;
  font-size: 16px;
  white-space: pre-wrap;
}

.answer-content {
  line-height: 1.6;
  color: #e0e0e0;
  font-size: 14px;
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: #141414;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.student-summary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.student-summary strong {
  color: #fff;
  font-size: 14px;
}

.student-summary p {
  margin: 12px 0 0 0;
  color: #a0a0a0;
  line-height: 1.6;
}
</style>
