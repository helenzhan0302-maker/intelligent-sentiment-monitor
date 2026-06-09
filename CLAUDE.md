# 智能舆情监测平台 (Intelligent Sentiment Monitoring Platform)

> **通用主题监测分析平台** — 输入任意关键词，搜索最新新闻，5维规则评分排序，按需生成综合深度报告。

## 当前版本：v0.4.0

已实现：搜索 + 评分 + SSE 实时推送 + 综合报告 + JWT 认证 + SQLite 搜索历史。

---

## 项目结构

```
query/
├── CLAUDE.md                    # 本文件
├── backend/
│   ├── main.py                  # API 端点 + 搜索/评分/报告逻辑 (~550行)
│   ├── auth.py                  # JWT 认证 + SQLite DB + 搜索历史 (~180行)
│   ├── data.db                  # SQLite 数据库（自动生成，不提交）
│   ├── .env                     # API keys + JWT_SECRET
│   └── requirements.txt         # fastapi, uvicorn, httpx, python-dotenv, pyjwt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # 单文件前端 (~530行)：Dashboard + AuthModal + HistoryPanel
│   │   ├── main.jsx             # React 入口
│   │   └── index.css            # TailwindCSS 基础样式
│   ├── index.html               # 单页 HTML, title: "智能舆情监测"
│   ├── vite.config.js           # Vite 配置, proxy /api → localhost:8000
│   ├── tailwind.config.js
│   └── package.json
└── venv/                        # Python virtual environment
```

## 架构原则

- **双文件后端**：`main.py` 业务逻辑 + `auth.py` 认证/数据库，无 ORM，无重型框架
- **单文件前端**：`App.jsx` 包含全部 UI（Dashboard + AuthModal + HistoryPanel），React Hooks 管理状态
- **SQLite 持久化**：`sqlite3` stdlib，3 张表（users, invite_codes, search_history）
- **评分不用 LLM**：规则引擎即时计算，保证搜索响应 < 5s
- **LLM 仅用于**：DeepSeek fallback 搜索、按需综合报告生成

## 技术栈

| 层 | 技术 | 备注 |
|----|------|------|
| 后端框架 | FastAPI + Uvicorn | Python 3.14 |
| 数据库 | SQLite3 (stdlib) | WAL 模式，外键约束 |
| 认证 | JWT HS256 + pbkdf2_hmac | 7天过期，stdlib 密码哈希 |
| 前端框架 | React 18 + Vite 6 | 无 TypeScript |
| 样式 | TailwindCSS 3 | 暗色主题 (slate-900) |
| 搜索 API | Serper.dev (主) + Bing News API | 并行调用，DeepSeek fallback |
| LLM API | DeepSeek (Anthropic-compatible) | `https://api.deepseek.com/anthropic/v1/messages` |
| 实时推送 | SSE (Server-Sent Events) | `StreamingResponse` + `EventSource` |
| 进程通信 | Vite proxy | `/api` → `http://localhost:8000` |

## 预置邀请码

| 邀请码 | 状态 |
|--------|------|
| `DEMO2026` | 可复用 |
| `VIBECODE` | 可复用 |
| `MONITOR01` | 可复用 |

邀请码仅用于注册验证，不限使用次数，适合内测分发。

## API 端点 (v0.4.0)

### 公开端点

| Method | Path | 描述 |
|--------|------|------|
| `GET` | `/api/health` | 健康检查，返回版本和 API key 配置状态 |
| `POST` | `/api/auth/register` | 注册。Body: `{username, password, invite_code}` |
| `POST` | `/api/auth/login` | 登录。Body: `{username, password}` → `{token, user_id, username}` |

### 需认证端点 (Header: `Authorization: Bearer <token>`)

| Method | Path | 描述 |
|--------|------|------|
| `POST` | `/api/search` | 同步搜索+评分 → 自动保存历史 |
| `GET` | `/api/search/stream?keywords=...&token=...` | SSE 流式搜索（EventSource 通过 query param 传 token） |
| `POST` | `/api/reports/generate` | 单条报告。Body: `{id, title, source, snippet}` |
| `POST` | `/api/reports/generate-combined` | 综合报告。Body: `{items: [{id, title, source, snippet}, ...]}` |
| `GET` | `/api/history` | 搜索历史列表 → `{items, total}` |
| `GET` | `/api/history/{id}` | 历史详情（含完整搜索结果） |

### SSE 事件流

```
search_start → search_status(可选) → search_done → scoring_start → complete (含 history_id)
```

### 关键词分词规则

前后端统一：`.split(/[,，、]+/)` — **逗号、中文顿号分隔，空格不拆分**（"claude code" 是一个关键词）。

## 5维评分规则（纯规则，不调 LLM）

| 维度 | 权重 | 评分逻辑 | 分数范围 |
|------|------|----------|----------|
| 权威性 🏛 | 25% | 域名白名单匹配 (`DOMAIN_AUTHORITY` dict) | 3-10 |
| 时效性 ⏱ | 20% | 发布时间距今小时数 | 2-10 |
| 重要性 📌 | 25% | 标题长度 + 摘要丰富度 + 权威性加成 | 1-10 |
| 影响度 💥 | 20% | 关键词命中 + 冲击力关键词匹配 | 1-10 |
| 相关性 🎯 | 10% | 关键词在标题+摘要中出现次数 | 1-10 |

总分 = Σ(维度分 × 权重)，保留 2 位小数。

## 前端状态机

```
未登录 → 🔑 登录按钮 → AuthModal 弹窗（登录/注册切换）
已登录 → 输入关键词 → 搜索 → SSE 实时进度 → 结果 + Top 5 颜色分层
                                                          ↓
                                            📝 一键生成综合报告 → 📥 下载 Markdown
```

- `auth`：`{token, username}` 存 localStorage，页面刷新保持登录
- `combinedReport`：`{loading, report, error}` 综合报告状态
- `abortRef`：SSE EventSource 引用，用于取消

### AuthModal
- 登录模式：username + password
- 注册模式：username + password + invite_code
- 401 时自动弹出

### HistoryPanel
- 右侧滑入面板，列出最近 20 条搜索
- 点击可重新加载历史结果
- 每次搜索自动保存（SSE complete 事件触发）

## 数据库表结构

```sql
-- users: 用户表
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,         -- pbkdf2:sha256:100000$salt$dk
    created_at TEXT DEFAULT (datetime('now'))
);

-- invite_codes: 邀请码表（预置种子数据）
CREATE TABLE invite_codes (
    code TEXT PRIMARY KEY,
    is_used INTEGER DEFAULT 0,
    used_by TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- search_history: 搜索历史（results_json 缓存完整响应）
CREATE TABLE search_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    keywords TEXT NOT NULL,              -- JSON array
    results_json TEXT NOT NULL,          -- JSON: 完整 SearchResponse
    created_at TEXT DEFAULT (datetime('now'))
);
```

## 启动命令

```bash
# 后端（从 backend/ 目录启动）
cd query/backend
source ../venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端（从 frontend/ 目录启动）
cd query/frontend
npx vite --host 0.0.0.0
```

## 端口占用处理

```bash
fuser -k 8000/tcp    # 杀掉占用 8000 端口的进程
```

## DeepSeek API 注意事项

- Anthropic-compatible 端点，使用 `v1/messages`
- 响应格式：`content` 数组，每个元素 `{type: "text", text: "..."}`
- 必须传 `"thinking": {"type": "disabled"}` 降低延迟
- `max_tokens`：搜索 fallback 用 4096，报告生成用 3072，综合报告用 4096

## 已验证问题及修复

| 问题 | 根因 | 修复 |
|------|------|------|
| 分析一直卡住 | `task_queue.submit()` 传了函数引用 | 内联 `_run_pipeline()` |
| DeepSeek JSON truncated | `max_tokens=2048` 不够 | 改为 4096 |
| "claude code" 拆成两个词 | split regex 包含 `\s` | 去掉 `\s`，只用 `[,，、]` |
| 显示 "Invalid Date" | 日期解析未校验有效性 | `isNaN(d.getTime())` 检查 |
| 54s 才出结果（demo 体感差） | 报告嵌入主流程 | v0.3.1 分离为独立接口 |
| 注册/api/api/auth/register 404 | endpoint 重复 `/api` 前缀 | 改为 `/auth/register` |
| 邀请码 DEMO2026 "已被使用" | `is_used` 限制一次 | 改为可复用 |

## 迭代路线

| Phase | 内容 | 状态 |
|-------|------|------|
| v0.1 | 极简 MVP：搜索 + 评分 + 展示 | ✅ 完成 |
| v0.2 | SSE 流式推送 | ✅ 完成 |
| v0.3 | 深度报告（Top 3，LLM 生成） | ✅ 完成 |
| v0.3.1 | 报告生成独立化（按需触发） | ✅ 完成 |
| v0.4.0 | JWT 认证 + SQLite + 搜索历史 | ✅ 完成 |
| v0.5 | 定时监测调度 | ⏳ 待开发 |
