# 🚀 部署指南：阿里云函数计算 FC 3.0

> 智能舆情监测平台 — Web 函数一键部署，无需管理服务器。

---

## 🎯 最终方案

| 层 | 平台 | 说明 |
|----|------|------|
| 🖥 后端 | 阿里云函数计算 FC 3.0 Web 函数 | Serverless，支付宝/微信支付 |
| 🌐 前端 | 阿里云 OSS 静态托管 | CDN 加速，国内访问快 |

---

## 📋 前置准备

| 准备项 | 说明 |
|--------|------|
| 阿里云账号 | 支付宝实名认证 |
| Serper API Key | https://serper.dev → 免费注册 |
| DeepSeek API Key | https://platform.deepseek.com → 注册充值 ¥1 |

---

## 🖥 第一步：部署后端（FC Web 函数）

### 1.1 进入控制台

打开 https://fc.console.aliyun.com → 左侧菜单：

```
函数管理 → 函数列表 → 创建函数 → 类型选「Web 函数」
```

### 1.2 配置参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 函数名称 | `sentiment-backend` | 自定义 |
| 实例类型 | 弹性实例 | 默认 |
| vCPU | 0.35 | 默认，演示够用 |
| 内存 | 0.5 GB | 默认 |
| 磁盘 | 512 MB | 默认 |
| **最小实例数** | **0** | 🔑 无请求缩容到零，省钱 |
| 单实例并发度 | 20 | 默认 |
| 运行环境 | **Python 3.10**（Debian 11） | 自带 Python，不用自己装 |
| 超时时间 | **300 秒** | SSE 长连接需要 |

### 1.3 上传代码

- **代码上传方式**：选择「**通过文件夹上传代码**」
- 将以下文件放入一个文件夹后拖拽上传：
  ```
  auth.py  index.py  main.py  requirements.txt
  ```
  不要包含 `data.db`、`__pycache__/`、`node_modules/`。

### 1.4 启动命令

```
uvicorn index:app --host 0.0.0.0 --port 9000
```

### 1.5 环境变量

在创建页面「环境变量」区域，用 **表单编辑** 模式添加：

| Key | Value |
|-----|-------|
| `SERPER_API_KEY` | 你的 Serper Key |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key |
| `JWT_SECRET` | 自定义随机字符串 |
| `TZ` | `Asia/Shanghai` |

### 1.6 部署 & 验证

1. 点击 **创建** → 等待 2-3 分钟
2. 进入函数详情 → **触发器管理** → 复制 HTTP 触发器的公网地址
3. 浏览器打开 `https://你的地址/api/health`

```json
{"status":"ok","version":"v0.4.0"}
```

---

## 🌐 第二步：部署前端

### 2.1 本地构建

```bash
cd frontend

# 替换为你的后端地址
export VITE_API_URL=https://你的FC地址/api

npm install
npx vite build
```

### 2.2 上传到 OSS

1. 阿里云 OSS 控制台 → 创建 Bucket（公共读）
2. 把 `dist/` 目录所有文件上传
3. 设置静态页面：默认首页 `index.html`，404 页 `index.html`

---

## ✅ 第三步：验证全流程

1. 打开 OSS 前端域名
2. 注册（邀请码 `DEMO2026`）→ 登录 → 搜索 → 生成报告

---

## 🔄 更新部署

代码改了之后，进 FC 函数详情 → 重新上传 `backend/` 文件夹即可。

---

## 🆘 问题排查

| 现象 | 排查 |
|------|------|
| `/api/health` 打不开 | 检查触发器是否启用 + 环境变量 |
| 搜索超时 | 超时时间确认设了 300 秒 |
| 注册失败 | JWT_SECRET 环境变量确认已填 |
| 前端空白 | VITE_API_URL 检查域名和 /api 后缀 |
