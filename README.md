<div align="center">

# 词页 CiYe

**把单词背成一页会留下痕迹的书。**

一个文艺书房风格的英语背单词 Web 应用，支持间隔重复记忆、词书管理、发音播放、ECDICT 本地词典。

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?logo=vue.js)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## 功能特性

### 学习系统
- **间隔重复算法** — 四级反馈（不认识 / 模糊 / 认识 / 很熟），自动安排复习间隔
- **每日学习计划** — 设定每天新词数量，系统自动混合新词 + 到期复习词
- **进度持久化** — 今日学习计划存入数据库，刷新页面不会丢失进度
- **单词详情** — 中文释义、英文释义、音标、例句、发音、记忆配图
- **例句点击查词** — 例句中每个单词可点击查询释义并播放发音

### 词书管理
- **书架式 UI** — 每本书以实体书样式展示在书架上，带学习进度
- **词书切换** — 点击书架上的书，确认后切换，支持设置每日词数
- **CSV 导入** — 支持 CSV / TSV / 纯文本导入，自动识别表头
- **AI 整理提示词** — 一键复制提示词，配合 ChatGPT 整理非标准单词资料

### 发音与图片
- **真实发音优先** — Free Dictionary API 提供真人发音音频
- **浏览器 TTS 兜底** — 音频不可用时自动使用浏览器语音朗读
- **记忆配图** — Pexels API 为具体名词提供辅助记忆图片

### 词典查询
- **ECDICT 本地词典** — 810MB 离线英汉词典，查询速度快
- **Free Dictionary API** — 在线查询音标、英文释义、例句、发音

### 学习统计
- **数据概览** — 总词数、待学习、学习中、已掌握
- **学习量图表** — 最近 14 天每日学习量柱状图

### 测试工具
- **日期模拟** — 调整虚拟日期，测试不同日期的复习调度
- **重置今日学习** — 清除今日学习记录，方便反复测试
- **重置词书进度** — 将某本词书的全部进度归零

---

## 快速开始

### 环境要求

- **Node.js** 18+
- **Python** 3.10+
- **ECDICT 词典**（可选，首次使用需下载）

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/EarlySleep0913/ciye.git
cd ciye

# 2. 安装前端依赖
npm install

# 3. 构建前端
npm run build

# 4. 下载 ECDICT 词典（可选，约 810MB）
# 将 ecdict.db 放入 data/ 目录

# 5. 启动服务
python run.py
```

浏览器打开 http://127.0.0.1:8765

### 配置 Pexels API（可选）

1. 前往 [pexels.com/api](https://www.pexels.com/api/) 注册获取 API Key
2. 在应用的 **设置页面** 填入 API Key

---

## 项目结构

```
ciye/
├── run.py                    # 启动入口
├── package.json              # 前端依赖配置
├── vite.config.js            # Vite 构建配置
├── index.html                # 入口 HTML
├── import_cet4.py            # CET-4 词表导入脚本
│
├── server/                   # Python 后端
│   ├── app.py                # HTTP 服务器 + API 路由
│   ├── db.py                 # 数据库连接池 + 缓存 + 索引
│   ├── dict.py               # ECDICT + Free Dictionary 查询
│   └── pexels.py             # Pexels 图片搜索 + 状态缓存
│
├── src/                      # Vue 3 前端
│   ├── main.js               # 应用入口
│   ├── App.vue               # 根组件
│   ├── styles/main.css       # 全局样式（文艺书房风格）
│   ├── composables/
│   │   ├── useApi.js         # API 请求封装
│   │   └── useAudio.js       # 发音播放封装
│   └── components/
│       ├── NavRail.vue       # 侧边导航
│       ├── StudyCard.vue     # 学习卡片主区域
│       ├── BookShelf.vue     # 词书架 + 导入
│       ├── StatsPanel.vue    # 学习统计
│       ├── SettingsPanel.vue # 设置页面
│       ├── PdfWordlist.vue   # PDF 词表
│       ├── SidePanel.vue     # 计划侧栏
│       ├── WordImport.vue    # 词书导入（备用）
│       └── LookupPopover.vue # 查词浮窗
│
└── data/                     # 数据目录（gitignore）
    ├── app.db                # 业务数据库（自动生成）
    └── ecdict.db             # ECDICT 词典（需手动下载）
```

---

## 技术架构

```
浏览器
  ↕
Vue 3 前端（Vite 构建，输出到 public/）
  ↕ fetch('/api/...')
Python HTTP Server（标准库，零第三方依赖）
  ↕
SQLite（WAL 模式，连接池复用）
  + ECDICT 本地词典（LRU 缓存）
  + Free Dictionary API（在线查词）
  + Pexels API（记忆配图，状态缓存 5 分钟）
```

### 数据库优化

- **连接池** — 单例连接复用，避免反复打开/关闭数据库
- **WAL 模式** — 读写并行，不互相阻塞
- **索引优化** — `progress(status, due_date)`、`words(book_id, word)`、`events(created_at)`
- **ECDICT 缓存** — 词典连接 LRU 缓存，重复查词直接从内存返回
- **Pexels 状态缓存** — API 状态检查结果缓存 5 分钟
- **每日学习计划** — `daily_session` 表持久化今日队列，刷新不丢失

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/books` | 词书列表（含学习进度） |
| GET | `/api/settings` | 获取设置 |
| GET | `/api/today` | 今日学习队列 |
| GET | `/api/stats` | 学习统计 |
| GET | `/api/lookup?word=xxx` | 查词（ECDICT + Free Dictionary） |
| GET | `/api/pdf-words` | PDF 词表 |
| POST | `/api/settings` | 更新设置 |
| POST | `/api/books/activate` | 切换词书 + 设置每日词数 |
| POST | `/api/books/reset` | 重置词书学习进度 |
| POST | `/api/progress` | 提交学习反馈 |
| POST | `/api/favorite` | 切换收藏 |
| POST | `/api/reset-today` | 重置今日学习 |
| POST | `/api/pexels-key` | 保存 Pexels API Key |
| POST | `/api/import/preview` | 预览导入词书 |
| POST | `/api/books` | 创建词书 |
| POST | `/api/pdf-words/mark` | PDF 单词划线标记 |

---

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `books` | 词书 |
| `words` | 单词（含释义、音标、例句、音频、图片） |
| `progress` | 学习进度（状态、熟悉度、复习日期） |
| `daily_session` | 每日学习计划（持久化队列） |
| `events` | 学习事件记录 |
| `settings` | 键值对设置 |
| `pdf_words` | PDF 词表数据 |
| `pdf_word_marks` | PDF 单词划线标记 |

---

## 设计风格

- **字体** — Cormorant Garamond（英文标题）、Noto Serif SC（中文）、ZCOOL XiaoWei（装饰）
- **配色** — 纸张米色 `#f4efe4`、墨绿 `#223b32`、暗红 `#8b3a3a`、金色 `#af8744`
- **布局** — 桌面端左侧导航栏 + 右侧内容区，移动端响应式自适应
- **质感** — 纸张纹理背景、书脊阴影、折角装饰、胶带便签效果

---

## 开源协议

MIT License
