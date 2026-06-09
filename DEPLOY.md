# 🚀 部署指南：腾讯云 CloudBase

> 智能舆情监测平台 — FastAPI 后端 + React 前端，免费演示环境部署。

---

## 📋 前置准备

| 事项 | 说明 |
|------|------|
| 腾讯云账号 | 需要实名认证（中国大陆身份证或企业认证） |
| API Keys | Serper.dev Key + DeepSeek API Key |
| GitHub 仓库 | `helenzhan0302-maker/intelligent-sentiment-monitor` |

---

## 第一步：开通 CloudBase 环境

1. 打开 https://console.cloud.tencent.com/tcb
2. 点击 **新建环境**
3. 配置：

| 选项 | 填写 |
|------|------|
| 环境名称 | `sentiment-monitor`（自定义） |
| 计费方式 | **按量计费**（新用户有免费额度，不产生费用时每月账单为 ¥0） |
| 区域 | **上海**（`ap-shanghai`） |
| 套餐版本 | **标准版** |

4. 点击 **立即开通** → 等待环境初始化（约 1 分钟）

> 📌 记下你的 **环境 ID**（格式如 `sentiment-monitor-xxxxx`），后续步骤会用到。

---

## 第二步：部署后端（云托管）

CloudBase 云托管 = 容器服务，完美支持 FastAPI + SQLite + SSE。

### 2.1 进入云托管

1. CloudBase 控制台 → 左侧菜单 → **云托管**
2. 点击 **新建服务**
3. 服务名称：`sentiment-backend`
4. 点击 **创建**

### 2.2 创建版本（部署）

1. 在服务详情页 → 点击 **新建版本**
2. 配置如下：

| 选项 | 填写 |
|------|------|
| 代码来源 | **GitHub**（首次需授权 CloudBase 访问仓库） |
| 仓库 | `helenzhan0302-maker/intelligent-sentiment-monitor` |
| 分支 | `master` |
| Dockerfile 路径 | `backend/Dockerfile`（自动检测） |
| 构建目录 | `backend` |

3. **资源配置**：

| 选项 | 填写 |
|------|------|
| CPU | 0.25 核 |
| 内存 | 0.5 GB |
| 最小实例数 | **0**（无请求时缩容，省钱） |
| 最大实例数 | 2 |
| 扩缩容条件 | CPU 使用率 > 60% |

4. **环境变量**（重要！）：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `SERPER_API_KEY` | 你的 Serper Key | 搜索 API |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key | LLM 报告生成 |
| `BING_API_KEY` | （可选）你的 Bing Key | 辅助搜索 |
| `JWT_SECRET` | 留空，首次启动自动生成 | 或自定义一个随机字符串 |
| `PYTHONUNBUFFERED` | `1` | 日志实时输出 |

5. 点击 **部署** → 等待构建（约 3-5 分钟）

### 2.3 获取后端域名

1. 版本部署完成后 → 点击 **访问服务**
2. 弹窗中开启 **公网访问**（外网域名）
3. 后端域名为：`https://sentiment-backend-xxxxx.run.tcloudbase.com`
4. 验证：浏览器打开 `https://<你的域名>/api/health` → 应返回 JSON：
   ```json
   {"status":"ok","version":"v0.4.0"}
   ```

> 📌 记下这个域名，前端部署需要用到。

---

## 第三步：部署前端（静态网站托管）

### 3.1 开通静态托管

1. CloudBase 控制台 → 左侧 → **静态网站托管**
2. 点击 **开通**（如未开通）
3. 记下默认域名：`https://sentiment-monitor-xxxxx.tcloudbaseapp.com`

### 3.2 本地构建前端

在你电脑上执行：

```bash
cd /path/to/intelligent-sentiment-monitor/frontend

# 设置后端 API 地址（替换为你的实际域名）
export VITE_API_URL=https://sentiment-backend-xxxxx.run.tcloudbase.com/api

# 构建
npm install
npx vite build
```

构建产物在 `frontend/dist/` 目录。

### 3.3 上传到静态托管

**方式一：控制台上传（推荐）**
1. 静态网站托管页面 → **上传文件**
2. 将 `dist/` 目录下的所有文件拖拽上传
3. 覆盖 `index.html` 和 `assets/` 目录

**方式二：CLI 上传（如果 CLI 登录成功）**
```bash
cd /path/to/intelligent-sentiment-monitor
tcb hosting deploy frontend/dist -e <你的环境ID>
```

### 3.4 配置单页应用路由

CloudBase 控制台 → 静态网站托管 → **基础配置**：
- **错误页面**：设置为 `index.html`（SPA 路由回退）
- **缓存配置**：默认即可

---

## 第四步：验证部署

打开前端域名 → 进行完整流程测试：

1. **注册**：输入用户名 + 密码 + 邀请码 `DEMO2026`
2. **登录**：用刚才注册的账号
3. **搜索**：输入关键词如 "AI,芯片" → 查看搜索结果和评分
4. **生成报告**：点击「生成 Top 3 综合深度报告」→ 查看 Markdown 报告
5. **搜索历史**：点击「📋 历史」查看之前的搜索记录

---

## 🔧 常见问题

### Q: 部署后访问 502？
- 检查云托管版本是否部署成功（构建日志是否有错误）
- 检查环境变量 `SERPER_API_KEY` 和 `DEEPSEEK_API_KEY` 是否正确

### Q: 搜索一直转圈？
- 打开浏览器开发者工具（F12）→ Network 标签
- 查看 `/api/search/stream` 请求状态
- 如果是 CORS 错误，检查后端 FastAPI 是否正常运行

### Q: 数据库（SQLite）数据会丢失吗？
- 云托管容器重启时数据保留（非重建）
- **重新部署**（构建新版本）时会丢失数据
- 演示环境可接受；如需持久化，后续可挂载 CloudBase 文件存储

### Q: 免费额度够用吗？
| 资源 | 免费额度 | 演示用量预估 |
|------|---------|-------------|
| 云托管 CPU | 按量计费 | 0.25核 × 少量请求 ≈ ¥0/月 |
| 静态托管存储 | 5 GB | < 1 MB |
| CDN 流量 | 5 GB/月 | 少量演示 ≈ 几十 MB |
| 云函数调用 | 10 万次/月 | 不使用 |

> 新用户通常有 ¥30-50 代金券，覆盖数月的演示开销。

---

## 📊 架构图（部署后）

```
用户浏览器
    │
    ├── https://xxx.tcloudbaseapp.com (前端 CDN)
    │       └── Vite 打包的 React SPA
    │
    └── https://xxx.run.tcloudbase.com/api (后端)
            └── CloudBase 云托管容器
                    ├── FastAPI + Uvicorn
                    ├── SQLite (容器内)
                    └── → Serper.dev / DeepSeek API
```

---

## 🔄 更新部署

代码更新后推送到 GitHub `master` 分支：

**后端更新**：
1. 云托管 → 服务详情 → **新建版本** → 选最新 commit → 部署
2. 新版本启动后自动替换旧版本（滚动更新）

**前端更新**：
1. 本地 `npm run build` 重新构建
2. 上传新的 `dist/` 文件到静态托管

---

## 📞 支持

- CloudBase 文档：https://docs.cloudbase.net
- 本项目文档：`CLAUDE.md`（API 参考 + 架构说明）
- GitHub Issues：https://github.com/helenzhan0302-maker/intelligent-sentiment-monitor/issues
