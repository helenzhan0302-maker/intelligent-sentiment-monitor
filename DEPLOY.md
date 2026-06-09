# 🚀 部署指南：从零到上线

> 智能舆情监测平台 — 零部署经验也能看懂的操作手册。

---

## 🗺️ 先看结论：选哪个平台？

我对比了市面上所有免费的部署方案，帮你筛好了：

| 平台 | 免费程度 | 要信用卡？ | 要实名？ | 国内速度 | 适合我吗？ |
|------|---------|-----------|---------|---------|-----------|
| **腾讯云 CloudBase** ⭐ | ¥0 起步 | ❌ | 需微信实名 | ⚡ 快 | ✅ **首选** |
| Alwaysdata（法国） | 永久 100MB | ❌ | ❌ | 🐢 可能慢 | 备选 |
| PythonAnywhere | 512MB | ❌ | ❌ | 🐢 | ❌ 无 HTTPS |
| Fly.io | 3台免费 | ✅ 要信用卡 | ❌ | 可能被墙 | ❌ |
| Render | 750h/月 | ✅ 要信用卡 | ❌ | 一般 | ❌ |
| 自己电脑 + 隧道 | 完全免费 | ❌ | ❌ | 取决于网络 | ❌ 不能关机 |

> **结论：用 CloudBase，唯一门槛是微信实名认证（国内平台都这样）。**
> 
> 如果实在没法实名 → 跳到文末「备选方案：Alwaysdata」。

---

## 📋 你需要准备

| 准备项 | 说明 | 去哪弄 |
|--------|------|--------|
| 微信实名账号 | CloudBase 注册用 | 你肯定有 |
| Serper API Key | 搜索新闻用 | https://serper.dev → 免费注册（2500次/月） |
| DeepSeek API Key | AI 生成报告用 | https://platform.deepseek.com → 注册充值 ¥1 |
| GitHub 账号 | 代码托管 | 你已有了 |

---

## 🎯 方案一：CloudBase（推荐）

> 腾讯云开发平台，后端用「云托管」跑容器，前端用「静态托管」放网页。
> 一个平台搞定全部，国内打开飞快。

### 第 1 步：开通 CloudBase

1. 浏览器打开 https://console.cloud.tencent.com/tcb
2. 微信扫码登录 → 完成实名认证（按提示操作，约 2 分钟）
3. 点击 **新建环境**，填写：

```
环境名称：sentiment-monitor（随便起）
计费方式：按量计费  ← 放心选，不产生费用不扣钱
区域：    上海（ap-shanghai）
```

4. 点 **立即开通** → 喝口水等 1 分钟初始化

> 📝 记下你的「环境 ID」，类似 `sentiment-monitor-1a2b3c`

---

### 第 2 步：部署后端（容器）

这就是把我们的 Python 代码跑在云端。

1. 左侧菜单 → **云托管** → 点 **新建服务**
2. 服务名填 `sentiment-backend`，点确定
3. 进入服务 → 点 **新建版本**，配置：

| 配置项 | 值 |
|--------|-----|
| **代码来源** | GitHub |
| **仓库** | `helenzhan0302-maker/intelligent-sentiment-monitor` |
| **分支** | `master` |
| **Dockerfile 路径** | `backend/Dockerfile` |

> 首次使用需授权 CloudBase 访问你的 GitHub 仓库，点一下就行。

4. 往下滑，**资源配置**：

| 配置 | 值 | 为什么 |
|------|-----|--------|
| CPU | 0.25 核 | 演示够用，省钱 |
| 内存 | 0.5 GB | Python 程序够用 |
| 最小实例数 | **0** | 🔑 没请求时自动关机，省钱关键！ |
| 最大实例数 | 2 | 防止意外跑飞 |

5. **环境变量**（这一步很重要！）：

```
SERPER_API_KEY    = 你的 Serper Key
DEEPSEEK_API_KEY  = 你的 DeepSeek Key
JWT_SECRET        = 随便打一串字母数字（比如 abc123xyz你的名字）
PYTHONUNBUFFERED  = 1
```

> BING_API_KEY 可不填，系统会自动用 DeepSeek 补搜索结果。

6. 点击 **部署** → 等着（约 3-5 分钟构建）

**怎么知道成功了？**

构建完成后，点 **访问服务** → 开启 **公网访问** → 你会得到一个域名：
```
https://sentiment-backend-xxxxx.run.tcloudbase.com
```
浏览器打开 `https://你的域名/api/health`，看到这个就对了：
```json
{"status":"ok","version":"v0.4.0"}
```

> 📝 把这个域名记下来，下一步用。

---

### 第 3 步：部署前端（网页）

#### 3.1 在你电脑上构建

打开终端，执行：

```bash
# 进入前端目录
cd /home/haili/project/vibecoding/query/frontend

# 设置后端地址（⚠️ 替换成你第 2 步拿到的域名！）
export VITE_API_URL=https://sentiment-backend-xxxxx.run.tcloudbase.com/api

# 安装依赖 + 构建
npm install
npm run build   # 等于 npx vite build
```

构建完会在 `frontend/dist/` 生成文件。

#### 3.2 上传到 CloudBase

1. CloudBase 控制台 → 左侧 **静态网站托管** → 开通
2. 点 **上传文件** → 把 `dist/` 里的所有文件拖进去
3. 上传后你会得到一个域名：`https://sentiment-monitor-xxxxx.tcloudbaseapp.com`

#### 3.3 配 SPA 路由

静态托管 → **基础配置** → 找到 **错误页面**：
- 设为 `index.html`（React 单页应用必须配这个，否则刷新页面会 404）

---

### 第 4 步：验证

用浏览器打开前端域名，走一遍完整流程：

1. 注册（邀请码 `DEMO2026`）
2. 登录
3. 输入关键词搜索 → 看 SSE 进度条
4. 点「生成 Top 3 综合深度报告」
5. 下载 Markdown 报告

全部通过 → 🎉 部署成功！把前端域名发给客户就行。

---

## 🔄 以后更新代码怎么办？

1. 代码改好 → `git push` 到 GitHub
2. **后端**：云托管 → 新建版本 → 选最新 commit → 部署（旧版本自动替换）
3. **前端**：本地重新 `npm run build` → 上传新的 `dist/` 文件覆盖旧的

---

## 🆘 遇到问题？

| 现象 | 大概率原因 | 怎么查 |
|------|-----------|--------|
| 打开前端是空白页 | `VITE_API_URL` 没设对 | 浏览器 F12 → Network 看 API 请求 URL |
| 搜索一直转圈 | 后端环境变量 API Key 没填 | 云托管 → 版本详情 → 环境变量检查 |
| 后端访问 502 | 容器构建失败或启动报错 | 云托管 → 版本详情 → 查看构建日志 |
| 注册提示 422 | 后端没正确启动 | 先访问 `/api/health` 确认后端正常 |
| 刷新页面 404 | SPA 路由没配 | 静态托管 → 基础配置 → 错误页设为 index.html |

---

## 🔌 备选方案：Alwaysdata

> 法国老牌免费主机，无需信用卡、无需实名，永久免费 100MB。
> 适合实在没法做 CloudBase 实名的情况，但国内访问会慢一些。

### 后端部署步骤

1. 打开 https://alwaysdata.com → 注册（邮箱就行，不用信用卡）
2. 进入管理面板 → **Web** → **Sites** → **Add a site**
3. 配置：

```
Type:        Python WSGI
Address:     你的用户名.alwaysdata.net
Python版本:  3.11
Application: ASGI: app
Working dir: /www/backend
```

4. **SSH 上传代码**：

```bash
# 生成 SSH key（如果没有）
ssh-keygen -t ed25519

# 查看公钥，复制到 alwaysdata SSH 设置里
cat ~/.ssh/id_ed25519.pub

# 上传代码
scp -r backend/ 你的用户名@ssh-alwaysdata.net:/www/backend/
```

5. **配置环境变量**：在 alwaysdata → **Environment** 中设置：
```
SERPER_API_KEY=你的key
DEEPSEEK_API_KEY=你的key
```

6. **安装依赖**：SSH 登录后：
```bash
cd /www/backend
pip install -r requirements.txt
```

### 前端部署

前端可以用 **Vercel**（免费）承载静态文件，设置 `VITE_API_URL` 指向 Alwaysdata 后端域名。

---

## 💡 零经验避坑指南

1. **环境变量是新手最容易错的地方** — API Key 少一个字母都不行，复制粘贴后检查有没有多余空格
2. **最小实例数一定要设 0** — 这是免费不花钱的关键，忘了设的话容器一直跑一直扣费
3. **构建日志要多看** — 部署失败了别慌，点进去看红色报错信息，一般就是环境变量没填或端口没写对
4. **先在电脑上跑通再部署** — 本地 `python main.py` 能正常搜索了，再推到云端
5. **演示前先预热** — 免费版容器在没请求时会休眠，客户演示前先打开一次后端地址让它「醒过来」
