import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import axios from 'axios';
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 设置axios默认配置，确保每次请求都携带Cookie
axios.defaults.withCredentials = true;

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd)

app.mount('#app')
