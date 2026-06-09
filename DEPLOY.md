# 🚀 部署指南：阿里云函数计算 Function AI

> 智能舆情监测平台 — Serverless 一键部署，无需管理服务器。

---

## 🎯 为什么选这个方案

| 对比项 | 阿里云 FC | CloudBase | Render/Vercel |
|--------|----------|-----------|---------------|
| 支付方式 | ✅ 支付宝/微信 | ✅ 微信 | ❌ 需信用卡 |
| 管理服务器 | ❌ 不需要 | ❌ 不需要 | ❌ 不需要 |
| Python 后端 | ✅ Web 服务模式 | ⚠️ 云托管要付费 | ⚠️ 有限制 |
| SQLite | ✅ 临时存储够用 | ✅ | ⚠️ |
| SSE 流式 | ✅ 支持 | ✅ | ⚠️ 部分支持 |
| GitHub 自动部署 | ✅ | ✅ | ✅ |
| 国内访问速度 | ⚡ 快 | ⚡ 快 | 🐢 慢/被墙 |

---

## 📋 前置准备

| 准备项 | 说明 |
|--------|------|
| 阿里云账号 | 需实名认证（支付宝扫码即可） |
| GitHub 仓库 | `helenzhan0302-maker/intelligent-sentiment-monitor` |
| Serper API Key | https://serper.dev → 免费注册 |
| DeepSeek API Key | https://platform.deepseek.com → 注册充值 ¥1 |

---

## 🖥 第一步：部署后端（函数计算 FC）

### 1.1 进入 Function AI 控制台

1. 打开 https://fc-next.console.aliyun.com
2. 左侧导航 → **Function AI** → **项目列表**
3. 点击 **创建项目** → 选择 **空白项目**
4. 项目名称填 `sentiment-monitor`

### 1.2 创建 Web 服务

进入项目 → 点击 **新建服务** → 选择 **Web 服务**，填写：

#### 基础配置

| 字段 | 值 |
|------|-----|
| 服务名称 | `sentiment-backend` |
| 运行环境 | **Python 3.10**（选最接近 3.11 的版本） |
| 代码仓库 | 连接 GitHub → 选 `helenzhan0302-maker/intelligent-sentiment-monitor` |
| 分支 | `master` |
| 根目录 | `backend` |

#### 构建 & 启动命令

| 字段 | 值 |
|------|-----|
| 构建命令 | `pip install -r requirements.txt` |
| 启动命令 | `uvicorn index:app --host 0.0.0.0 --port 8080` |
| 监听端口 | `8080` |

#### 环境变量

| 变量名 | 值 |
|--------|-----|
| `SERPER_API_KEY` | 你的 Serper Key |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key |
| `JWT_SECRET` | 自定义随机字符串（如 `myMonitor2026!`） |

### 1.3 部署

1. 点击 **预览 & 部署**
2. 等待构建完成（约 2-3 分钟）
3. 部署成功后，点击 **服务详情** → 复制 **公网访问地址**

验证后端：浏览器打开 `https://你的地址/api/health`

```json
{"status":"ok","version":"v0.4.0"}
```

> 📝 记下后端地址，如 `https://xxx.cn-hangzhou.fc.aliyuncs.com`

---

## 🌐 第二步：部署前端（OSS 静态托管）

### 2.1 本地构建

```bash
cd /home/haili/project/vibecoding/query/frontend

# ⚠️ 替换成你的后端地址！
export VITE_API_URL=https://你的后端地址/api

npm install
npx vite build
```

构建产物在 `frontend/dist/`。

### 2.2 上传到 OSS

1. 打开 https://oss.console.aliyun.com
2. 创建 Bucket（如已有则跳过）：
   - Bucket 名称：`sentiment-frontend`
   - 区域：和 FC 服务同区域（如杭州）
   - 读写权限：**公共读**
3. 进入 Bucket → **文件管理** → **上传文件**
4. 把 `dist/` 里的所有文件上传
5. 设置 **静态页面**：
   - 默认首页：`index.html`
   - 默认 404 页：`index.html`（SPA 路由回退）

### 2.3 绑定域名（可选）

1. OSS 控制台 → **传输管理** → **域名管理**
2. 绑定自定义域名 + 开启 CDN 加速
3. 或直接用 OSS 提供的默认域名

---

## ✅ 第三步：验证

打开前端地址，完整测试：

1. 注册（邀请码 `DEMO2026`）
2. 登录
3. 搜索关键词 → 看 SSE 进度条
4. 生成综合报告 → 下载 Markdown

---

## 🔄 更新部署

代码推送到 GitHub `master` 分支后，FC 自动重新部署。

```bash
git add . && git commit -m "描述" && git push
```

---

## 🔧 注意事项

### SQLite 存储
- FC 环境下 SQLite 文件存储在临时磁盘
- 服务缩容到 0 或重新部署时 **数据会丢失**
- 演示环境可接受（用户重新注册即可）
- 如需持久化：后续迁移到阿里云 RDS MySQL

### 唤醒延迟
- 无请求时服务可能缩容
- 首次请求有 2-5 秒冷启动延迟
- 客户演示前先访问一次 `/api/health` 预热

---

## 🆘 问题排查

| 现象 | 排查方向 |
|------|---------|
| 部署失败 | 检查构建日志 → 确认 `requirements.txt` 依赖版本兼容 |
| `/api/health` 502 | 检查启动命令 → 确认 `index:app` 语法正确 |
| 搜索报错 | 检查环境变量 → 确认 API Key 已填 |
| 前端空白 | 检查 `VITE_API_URL` → 确认地址正确且以 `/api` 结尾 |
| 注册 422 | 后端没正常启动 → 先访问 `/api/health` |
