# XDWe: Teacher-Augmented AI Learning System for Xidian University

<p style="text-align:center;">XDWe：一个 AI 驱动的师生交流互动平台，实现教学相长</p>

**Student Developers**
- 肖宗林 (Zonglin Xiao) - [xiaozonglin@stu.xidian.edu.cn](mailto:xiaozonglin@stu.xidian.edu.cn)
- 姚焱夫 (Yanfu Yao) - [YvesYao0209@foxmail.com](mailto:YvesYao0209@foxmail.com)
- 孟子钦 (Ziqin Meng) - [3862834578@qq.com](mailto:3862834578@qq.com)

---

**XDWe** (Xidian + We) is a collaborative, RAG-driven platform designed to transform Xidian University’s academic resources into an intelligent, teacher-verified knowledge network. It empowers students with instant, high-fidelity answers while ensuring educators retain full pedagogical control.

传统教育场景中，学生提问存在响应滞后、答案同质化严重、教师负担过重等问题。现有知识库缺乏针对性，无法有效沉淀教学过程中的个性化问题与解答。XDWe 尝试通过整合西安电子科技大学本地化学习资料（如课程讲义、实验文档、历年真题），结合大模型RAG技术，构建“学生提问-AI初答-教师审核-知识沉淀”的闭环生态，实现教学资源的智能化管理与个性化学习支持。

## 技术架构

采用前后端分离架构，各组件职责与交互关系如下：

- 前端：Vue.js 3.x 负责页面渲染与用户交互，通过 Axios 调用后端 RESTful API；
- 后端：Flask 框架提供 API 接口，SQLAlchemy 操作 MySQL 数据库；
- AI模型：基于 HuggingFace Transformers 实现 RAG 语义检索与流式回答。

## 目录结构

```txt
│  .env // 后端配置文件
│  environment.yml // Anaconda / Miniconda 环境配置
│  requirements.txt // pip 环境配置
│          
├─backend
│  │  API文档.md // 接口文档
│  │  main.py // 后端主文件
│  │  
│  ├─faiss_index // 由文档构建的向量数据库
│  │      index.faiss
│  │      index.pkl
│  │      
│  └─instance // 数据库
│          learning_assistant.db
│          
├─docs // 文档
│      
├─frontend
│  │  index.html
│  │  vite.config.js // 前端配置文件
│  │                 
│  ├─public
│  │      
│  └─src
│      │  App.vue
│      │  main.js
│      │  
│      ├─router // 路由
│      │      
│      ├─stores
│      │      
│      └─views // Vue 视图
│      
├─model_weights // 语言模型权重
│      
└─rag-embedding // embedding 模型
```

## 部署方法

### 前端

前端文件位于`./frontend`文件夹下，在该文件夹中运行`npm install & npm run dev`即可运行，可以使用`npm run build`构建生产环境的版本。

### 后端

后端文件位于`./backend`文件夹下，可使用 Anaconda / Miniconda 将项目根目录的`environment.yml`或通过`pip install -r requirements.txt`配置环境，随后可运行`cd backend & python main.py`代码来部署后端。

关于环境的配置：Pytorch 的安装可能存在一些问题，请安装带有合适版本 cuda 支持的 Pytorch。后端会在运行时自动检查环境并选用对应的配置。