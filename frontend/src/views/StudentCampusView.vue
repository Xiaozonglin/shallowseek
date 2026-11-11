<template>
  <div class="campus-page">
    <div class="container campus-shell">
      <header class="campus-hero">
        <div>
          <div class="campus-eyebrow">Campus Info</div>
          <h1>我的校园信息</h1>
          <p>课表、宿舍电量与考试安排集中在这里，方便随时查看今天该带什么、该补什么。</p>
        </div>
        <a-button class="campus-back" @click="goBack">返回学习工作区</a-button>
      </header>

      <a-alert
        type="warning"
        show-icon
        message="演示页面：数据尚未接入"
        description="当前展示为示例数据，不是真实个人课表与电量。后续支持手动录入或学校官方接口接入，演示时会说明「后期接入」。"
        class="campus-alert"
      />

      <div class="campus-stats">
        <div class="campus-stat">
          <span>本周课程</span>
          <strong>12 节</strong>
          <small>示例数据</small>
        </div>
        <div class="campus-stat">
          <span>今日课程</span>
          <strong>3 门</strong>
          <small>周三</small>
        </div>
        <div class="campus-stat">
          <span>宿舍电量</span>
          <strong>43.2 度</strong>
          <small>预计可用 6 天</small>
        </div>
      </div>

      <a-card class="campus-card timetable-card" title="我的课表">
        <template #extra>
          <span class="campus-card-tag">第 12 周 · 示例</span>
        </template>

        <div class="timetable-scroll">
          <div class="timetable">
            <div class="tt-corner" />
            <div
              v-for="(day, index) in weekdays"
              :key="day"
              class="tt-day"
              :style="{ gridColumn: index + 2, gridRow: 1 }"
            >
              {{ day }}
            </div>
            <div
              v-for="(slot, index) in timeSlots"
              :key="slot.label"
              class="tt-slot"
              :style="{ gridColumn: 1, gridRow: index + 2 }"
            >
              <strong>{{ slot.label }}</strong>
              <span>{{ slot.period }}</span>
            </div>
            <article
              v-for="course in courses"
              :key="course.id"
              class="tt-course"
              :class="`course-${course.color}`"
              :style="{
                gridColumn: course.day + 1,
                gridRow: `${course.slot + 1} / span ${course.span}`
              }"
            >
              <strong>{{ course.name }}</strong>
              <span>{{ course.room }} · {{ course.teacher }}</span>
              <small>{{ course.weeks }}</small>
            </article>
          </div>
        </div>

        <p class="timetable-note">
          数据来源：待接入（后续可手动录入或粘贴课表 JSON）。当前为静态示例。
        </p>
      </a-card>

      <div class="campus-grid">
        <a-card class="campus-card" title="宿舍电量">
          <template #extra>
            <span class="campus-card-tag">待接入</span>
          </template>

          <div class="electricity-head">
            <div>
              <span class="electricity-label">当前剩余</span>
              <strong class="electricity-value">43.2<small>度</small></strong>
            </div>
            <div class="electricity-meta">
              <span>近 7 日平均 2.6 度/天</span>
              <span>预计可用 6 天</span>
            </div>
          </div>

          <div class="electricity-chart">
            <div v-for="item in electricityUsage" :key="item.label" class="electricity-bar">
              <div class="electricity-bar-track">
                <span :style="{ height: `${Math.round((item.value / maxElectricity) * 100)}%` }" />
              </div>
              <strong>{{ item.value }}</strong>
              <small>{{ item.label }}</small>
            </div>
          </div>

          <p class="electricity-note">
            数据来源：待接入（后续可对接宿舍电表查询或手动记录）。充值入口不在此页面提供。
          </p>
        </a-card>

        <a-card class="campus-card" title="近期考试">
          <template #extra>
            <span class="campus-card-tag">示例</span>
          </template>
          <ul class="exam-list">
            <li v-for="exam in exams" :key="exam.subject" class="exam-item">
              <div class="exam-date">
                <strong>{{ exam.day }}</strong>
                <small>{{ exam.time }}</small>
              </div>
              <div class="exam-info">
                <strong>{{ exam.subject }}</strong>
                <span>{{ exam.place }}</span>
              </div>
            </li>
          </ul>
          <p class="electricity-note">数据来源：待接入（后续可对接教务考试安排）。</p>
        </a-card>
      </div>

      <a-card class="campus-card" title="数据接入说明（后期接入）">
        <div class="access-grid">
          <section>
            <h4>课表</h4>
            <p>后续支持手动录入、粘贴 JSON 或学校官方接口导入；只保存上课需要的时间、地点与课程名。</p>
          </section>
          <section>
            <h4>宿舍电量</h4>
            <p>后续对接学校电表查询，或允许学生手动记录；不接入支付与充值能力。</p>
          </section>
          <section>
            <h4>隐私边界</h4>
            <p>这些信息仅学生本人可见，不会自动同步给教师；不会保存学校账号密码。</p>
          </section>
        </div>
        <div class="access-footer">
          <span>接入方式评估中（参考 xdyou 调研：优先手动导入，不建议服务端代登录）。</span>
          <a-button type="primary" disabled>申请接入（开发中）</a-button>
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const weekdays = ['周一', '周二', '周三', '周四', '周五']
const timeSlots = [
  { label: '1-2 节', period: '08:00-09:40' },
  { label: '3-4 节', period: '10:00-11:40' },
  { label: '5-6 节', period: '14:00-15:40' },
  { label: '7-8 节', period: '16:00-17:40' },
  { label: '9-10 节', period: '19:00-20:40' },
  { label: '11-12 节', period: '20:50-22:30' }
]

// 演示数据：只为展示页面结构，不代表真实课表
const courses = [
  { id: 1, name: '数据结构与算法', room: 'A-302', teacher: '王老师', day: 1, slot: 1, span: 1, weeks: '1-16 周', color: 'blue' },
  { id: 2, name: '大学英语', room: 'B-105', teacher: '李老师', day: 1, slot: 4, span: 1, weeks: '1-16 周', color: 'green' },
  { id: 3, name: '计算机组成原理', room: 'A-210', teacher: '张老师', day: 2, slot: 2, span: 1, weeks: '1-16 周', color: 'purple' },
  { id: 4, name: '高等数学', room: 'C-401', teacher: '刘老师', day: 3, slot: 1, span: 1, weeks: '1-12 周', color: 'orange' },
  { id: 5, name: '体育（篮球）', room: '东操场', teacher: '赵老师', day: 3, slot: 5, span: 1, weeks: '1-16 周', color: 'teal' },
  { id: 6, name: '操作系统', room: 'A-305', teacher: '陈老师', day: 4, slot: 2, span: 1, weeks: '1-16 周', color: 'blue' },
  { id: 7, name: '算法实验', room: '机房 3', teacher: '王老师', day: 4, slot: 5, span: 1, weeks: '2-16 双周', color: 'green' },
  { id: 8, name: '形势与政策', room: 'D-102', teacher: '杨老师', day: 5, slot: 1, span: 1, weeks: '1-8 周', color: 'orange' },
  { id: 9, name: '算法习题课', room: 'A-302', teacher: '王老师', day: 5, slot: 3, span: 1, weeks: '1-16 周', color: 'purple' }
]

const electricityUsage = [
  { label: '周一', value: 3.2 },
  { label: '周二', value: 2.4 },
  { label: '周三', value: 2.8 },
  { label: '周四', value: 1.9 },
  { label: '周五', value: 3.5 },
  { label: '周六', value: 2.2 },
  { label: '周日', value: 2.0 }
]
const maxElectricity = Math.max(...electricityUsage.map((item) => item.value))

const exams = [
  { subject: '数据结构与算法', day: '12-18', time: '09:00', place: 'A-302' },
  { subject: '计算机组成原理', day: '12-22', time: '14:30', place: 'A-210' },
  { subject: '高等数学', day: '01-05', time: '09:00', place: 'C-401' }
]

const goBack = () => router.push('/student')
</script>

<style scoped>
.campus-page {
  position: relative;
  padding: 28px 0 48px;
}

.campus-shell {
  position: relative;
  z-index: 1;
}

.campus-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.campus-eyebrow {
  margin-bottom: 10px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
}

.campus-hero h1 {
  margin: 0 0 10px;
  font-size: clamp(28px, 4vw, 44px);
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.95);
}

.campus-hero p {
  max-width: 680px;
  margin: 0;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.8;
}

.campus-back {
  flex: none;
}

.campus-alert {
  margin-bottom: 18px;
  border-radius: 14px;
}

.campus-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.campus-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}

.campus-stat span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.campus-stat strong {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.92);
}

.campus-stat small {
  font-size: 11px;
  color: rgba(120, 190, 255, 0.7);
}

.campus-card {
  margin-bottom: 18px;
  border-radius: 18px;
}

.campus-card-tag {
  font-size: 11px;
  color: rgba(120, 190, 255, 0.8);
}

.timetable-scroll {
  overflow-x: auto;
  padding-bottom: 4px;
}

.timetable {
  display: grid;
  grid-template-columns: 88px repeat(5, minmax(120px, 1fr));
  grid-template-rows: auto repeat(6, 84px);
  gap: 8px;
  min-width: 720px;
}

.tt-corner {
  grid-column: 1;
  grid-row: 1;
}

.tt-day {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}

.tt-slot {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 0 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.tt-slot strong {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.tt-course {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  overflow: hidden;
}

.tt-course strong {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
}

.tt-course span {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.tt-course small {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
}

.course-blue {
  border-color: rgba(120, 190, 255, 0.35);
  background: rgba(120, 190, 255, 0.08);
}

.course-green {
  border-color: rgba(140, 220, 160, 0.35);
  background: rgba(140, 220, 160, 0.08);
}

.course-purple {
  border-color: rgba(190, 160, 255, 0.35);
  background: rgba(190, 160, 255, 0.08);
}

.course-orange {
  border-color: rgba(255, 200, 120, 0.35);
  background: rgba(255, 200, 120, 0.08);
}

.course-teal {
  border-color: rgba(120, 220, 210, 0.35);
  background: rgba(120, 220, 210, 0.08);
}

.timetable-note,
.electricity-note {
  margin: 14px 0 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.campus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.electricity-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.electricity-label {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.electricity-value {
  font-size: 34px;
  color: rgba(255, 255, 255, 0.95);
}

.electricity-value small {
  margin-left: 4px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.electricity-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.42);
  text-align: right;
}

.electricity-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  height: 140px;
}

.electricity-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  height: 100%;
}

.electricity-bar-track {
  display: flex;
  align-items: flex-end;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  overflow: hidden;
}

.electricity-bar-track span {
  display: block;
  width: 100%;
  border-radius: 8px 8px 0 0;
  background: linear-gradient(180deg, rgba(120, 190, 255, 0.8), rgba(120, 190, 255, 0.2));
}

.electricity-bar strong {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.65);
}

.electricity-bar small {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
}

.exam-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.exam-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.exam-item:first-child {
  border-top: none;
}

.exam-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: none;
  width: 58px;
  padding: 6px 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}

.exam-date strong {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

.exam-date small {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

.exam-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.exam-info strong {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.88);
}

.exam-info span {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
}

.access-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.access-grid h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.88);
}

.access-grid p {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.5);
}

.access-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.38);
}

@media (max-width: 900px) {
  .campus-grid,
  .access-grid {
    grid-template-columns: 1fr;
  }

  .campus-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .campus-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .campus-stats {
    grid-template-columns: 1fr;
  }

  .electricity-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .electricity-meta {
    text-align: left;
  }

  .access-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
