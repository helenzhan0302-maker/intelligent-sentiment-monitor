# 🔍 智能舆情监测平台

> 通用主题监测分析平台 — 输入任意关键词，搜索最新新闻，5 维规则评分排序，按需生成综合深度报告。

[![Version](https://img.shields.io/badge/version-v0.4.0-blue)](https://github.com/helenzhan0302-maker/intelligent-sentiment-monitor)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ 功能特性

- **🔎 双源搜索** — Serper.dev + Bing News API 并行搜索，DeepSeek fallback 智能补全
- **📊 5 维规则评分** — 权威性、时效性、重要性、影响度、相关性，纯规则引擎 < 1s 出结果
- **📡 SSE 实时推送** — 搜索进度实时可见（搜索中 → 评分中 → 完成）
- **📝 综合深度报告** — LLM 生成 Top 3 综合报告，跨事件影响分析 + 趋势预判，支持下载 Markdown
- **🔐 JWT 认证** — 注册/登录，邀请码白名单，7 天会话保持
- **📋 搜索历史** — SQLite 持久化，随时回溯查看过往分析
- **🎨 暗色主题** — TailwindCSS 暗色 UI（slate-900），Top 5 金银铜蓝紫颜色区分
- **🤖 LLM 按需调用** — 搜索评分不调 LLM，仅报告生成时使用 DeepSeek

---

## 🏗️ 系统架构

```
┌──────────────┐          ┌──────────────────┐          ┌───────────────┐
│  React 18    │  SSE     │  FastAPI         │  HTTP    │  Serper.dev   │
│  Vite 6      │◄────────►│  Uvicorn         │─────────►│  Bing News    │
│  TailwindCSS │  REST    │  Python 3.14     │          │  DeepSeek LLM │
└──────────────┘          └────────┬─────────┘          └───────────────┘
                                   │
                            ┌──────▼──────┐
                            │   SQLite3   │
                            │  (3 张表)   │
                            └─────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- Serper.dev API Key（[免费额度 2500次/月](https://serper.dev)）
- DeepSeek API Key（[控制台获取](https://platform.deepseek.com)）

### 1. 克隆项目

```bash
git clone git@github.com:helenzhan0302-maker/intelligent-sentiment-monitor.git
cd intelligent-sentiment-monitor
```

### 2. 配置后端

```bash
cd backend
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt

# 编辑 .env（首次运行会自动生成 JWT_SECRET，此项为自动）
cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
SERPER_API_KEY=your_serper_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
EOF
```

### 3. 启动后端

```bash
cd backend
source ../venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 http://localhost:8000 ，访问 `/docs` 查看 Swagger API 文档。

### 4. 启动前端

```bash
cd frontend
npm install
npx vite --host 0.0.0.0
```

前端运行在 http://localhost:5173 ，默认代理 `/api` 到后端 `localhost:8000`。

---

## 📡 API 概览

### 公开端点

| Method | Path | 描述 |
|--------|------|------|
| `GET` | `/api/health` | 健康检查，返回版本和 API key 配置状态 |
| `POST` | `/api/auth/register` | 注册 `{username, password, invite_code}` |
| `POST` | `/api/auth/login` | 登录 `{username, password}` → `{token, user_id, username}` |

### 需认证端点 `Authorization: Bearer <token>`

| Method | Path | 描述 |
|--------|------|------|
| `POST` | `/api/search` | 同步搜索 + 评分 → 自动保存历史 |
| `GET` | `/api/search/stream?keywords=...&token=...` | SSE 流式搜索（EventSource 通过 query param 传 token） |
| `POST` | `/api/reports/generate` | 单条报告 `{id, title, source, snippet}` |
| `POST` | `/api/reports/generate-combined` | 综合报告 `{items: [{id, title, source, snippet}, ...]}` |
| `GET` | `/api/history` | 搜索历史列表 → `{items, total}` |
| `GET` | `/api/history/{id}` | 历史详情（含完整搜索结果） |

### SSE 事件流

```
search_start → search_status(可选) → search_done → scoring_start → complete (含 history_id)
```

### 关键词分词规则

前后端统一：`.split(/[,，、]+/)` — **逗号、中文顿号分隔，空格不拆分**
> "claude code" 是一个关键词，不会被拆成两个词。

---

## 📊 5 维评分规则

| 维度 | 权重 | 评分逻辑 | 分数范围 |
|------|------|----------|----------|
| 🏛 **权威性** | 25% | 域名白名单匹配（CNN、BBC、澎湃新闻等 50+ 媒体） | 3–10 |
| ⏱ **时效性** | 20% | 发布时间距今小时数 | 2–10 |
| 📌 **重要性** | 25% | 标题长度 + 摘要丰富度 + 权威性加成 | 1–10 |
| 💥 **影响度** | 20% | 关键词命中 + 冲击力关键词匹配 | 1–10 |
| 🎯 **相关性** | 10% | 关键词在标题 + 摘要中出现次数 | 1–10 |

> 总分 = Σ(维度分 × 权重)，保留 2 位小数。**纯规则计算，不调 LLM，< 1s 完成。**

---

## 📁 项目结构

```
intelligent-sentiment-monitor/
├── README.md                   # 本文件
├── CLAUDE.md                   # 开发文档（API 细节 + 已知问题）
├── .gitignore
├── backend/
│   ├── main.py                 # API 端点 + 搜索/评分/报告逻辑 (~827行)
│   ├── auth.py                 # JWT 认证 + SQLite + 搜索历史 (~233行)
│   ├── data.db                 # SQLite 数据库（自动生成）
│   ├── .env                    # API keys + JWT_SECRET
│   └── requirements.txt        # Python 依赖
└── frontend/
    ├── src/
    │   ├── App.jsx             # 单文件前端 (~693行)：Dashboard + Auth + History
    │   ├── main.jsx            # React 入口
    │   └── index.css           # TailwindCSS 基础样式
    ├── index.html              # 单页 HTML
    ├── vite.config.js          # Vite 配置 (proxy /api → localhost:8000)
    ├── tailwind.config.js
    └── package.json
```

---

## 🛠️ 技术栈

| 层 | 技术 | 备注 |
|----|------|------|
| 后端框架 | FastAPI + Uvicorn | Python 3.14 |
| 数据库 | SQLite3 (stdlib) | WAL 模式，外键约束 |
| 认证 | JWT HS256 + pbkdf2_hmac | 7 天过期，stdlib 密码哈希 |
| 前端框架 | React 18 + Vite 6 | 无 TypeScript，Hooks 管理状态 |
| 样式 | TailwindCSS 3 | 暗色主题 (slate-900) |
| 搜索 API | Serper.dev + Bing News | 并行调用，DeepSeek fallback |
| LLM API | DeepSeek | Anthropic-compatible `/v1/messages` 端点 |
| 实时推送 | SSE | `StreamingResponse` + `EventSource` |
| 进程通信 | Vite proxy | `/api` → `http://localhost:8000` |

---

## 🔑 预置邀请码

| 邀请码 | 说明 |
|--------|------|
| `DEMO2026` | 演示用，可重复使用 |
| `VIBECODE` | 内测用，可重复使用 |
| `MONITOR01` | 备用，可重复使用 |

> 邀请码仅用于注册验证，不限使用次数，适合内测分发。

---

## 🗺️ 迭代路线

| Phase | 内容 | 状态 |
|-------|------|------|
| v0.1 | 极简 MVP：搜索 + 评分 + 展示 | ✅ 完成 |
| v0.2 | SSE 流式推送 | ✅ 完成 |
| v0.3 | 深度报告（Top 3，LLM 生成） | ✅ 完成 |
| v0.3.1 | 报告生成独立化（按需触发） | ✅ 完成 |
| v0.4.0 | JWT 认证 + SQLite + 搜索历史 | ✅ 完成 |
| v0.5 | 定时监测调度 | ⏳ 待开发 |

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ using FastAPI + React + Claude Code</sub>
</p>
