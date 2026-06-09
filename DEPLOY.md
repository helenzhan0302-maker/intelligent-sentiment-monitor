# 🚀 部署指南：从零到上线

> 智能舆情监测平台 — 零部署经验也能看懂的操作手册。

---

## 🗺️ 选哪个平台？

| 层 | 平台 | 费用 | 信用卡 | 实名 |
|----|------|------|--------|------|
| 🖥 后端 | **Alwaysdata**（法国） | 永久免费 100MB | ❌ | ❌ |
| 🌐 前端 | **CloudBase 静态托管** | 免费 5GB + CDN | ❌ | 微信已认证 |

> ✅ Alwaysdata 永久免费，不用信用卡，不用实名，自带 HTTPS。
> ✅ CloudBase 静态托管已开通，国内访问快。

---

## 📋 你需要准备

| 准备项 | 去哪弄 |
|--------|--------|
| 邮箱地址 | Alwaysdata 注册用 |
| Serper API Key | https://serper.dev → 免费注册 2500次/月 |
| DeepSeek API Key | https://platform.deepseek.com → 注册充值 ¥1 即可 |

---

## 🖥 第一步：部署后端到 Alwaysdata

### 1.1 注册 Alwaysdata

1. 打开 https://www.alwaysdata.com → 点右上角 **Sign up**
2. 填邮箱 + 密码 → 注册
3. 去邮箱点确认链接 → 激活账号

### 1.2 创建后端站点

登录后进入管理面板（Admin），按以下操作：

1. 左侧菜单 → **Web** → **Sites**
2. 点击 **Add a site**，填写：

| 字段 | 值 | 说明 |
|------|-----|------|
| **Type** | User program | 运行任意命令行程序 |
| **Name** | `sentiment-backend` | 自定义 |
| **Addresses** | 勾选你的域名（如 `用户名.alwaysdata.net`） | |

> 域名格式：`https://你的用户名.alwaysdata.net`（注册时自动分配）

3. 点击 **Create** 创建站点

### 1.3 上传代码

打开你电脑的终端（WSL / 命令行）：

```bash
# 1. 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_alwaysdata
# 一路回车即可

# 2. 查看公钥，复制全部内容
cat ~/.ssh/id_ed25519_alwaysdata.pub
```

回到 Alwaysdata 网页：
- 右上角用户菜单 → **SSH Keys**
- 粘贴公钥 → **Add**

然后在终端上传代码：

```bash
# 3. 测试 SSH 连接（替换成你的用户名）
ssh 你的用户名@ssh-alwaysdata.net

# 4. 创建目录并上传代码
# 先退出 SSH（如果已登录），然后：
cd /home/haili/project/vibecoding/query
scp -r backend/ 你的用户名@ssh-alwaysdata.net:/www/backend/
```

### 1.4 安装依赖 + 配置启动命令

SSH 登录到 Alwaysdata：

```bash
ssh 你的用户名@ssh-alwaysdata.net

# 安装 Python 依赖
cd /www/backend
pip install --user -r requirements.txt

# 测试能否启动（Ctrl+C 退出）
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

测试成功后，回到 Alwaysdata 管理面板：

1. **Web** → **Sites** → 点击刚才创建的 `sentiment-backend`
2. 找到 **Command** 字段，填入：

```bash
cd /www/backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

3. 找到 **Working directory**，填：`/www/backend`

### 1.5 设置环境变量

1. Alwaysdata 面板 → **Environment**
2. 添加以下变量：

| 变量名 | 值 |
|--------|-----|
| `SERPER_API_KEY` | 你的 Serper Key |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key |
| `JWT_SECRET` | 随机字符串（比如 `myMonitorSecret2026`） |

3. 点击 **Save**

### 1.6 重启 + 验证

1. Alwaysdata → **Web** → **Sites** → 找到你的站点 → 点击 **Restart**
2. 等几秒后，浏览器打开：
```
https://你的用户名.alwaysdata.net/api/health
```
3. 看到这个就成功了：
```json
{"status":"ok","version":"v0.4.0"}
```

> 📝 记下 `https://你的用户名.alwaysdata.net`，这是后端地址。

---

## 🌐 第二步：部署前端到 CloudBase

前端直接用你已有的 CloudBase 环境。

### 2.1 本地构建

在终端执行：

```bash
cd /home/haili/project/vibecoding/query/frontend

# ⚠️ 替换成你 Alwaysdata 的真实域名！
export VITE_API_URL=https://你的用户名.alwaysdata.net/api

# 构建
npm install
npx vite build
```

构建产物在 `frontend/dist/` 目录。

### 2.2 上传到 CloudBase

1. 打开 https://console.cloud.tencent.com/tcb
2. 左侧 → **静态网站托管** → **上传文件**
3. 把 `dist/` 目录里所有文件拖进去上传
4. 设置 → **基础配置** → **错误页面** 设为 `index.html`

> ⚠️ 错误页面设为 `index.html` 很重要！否则用户刷新页面会 404。

### 2.3 获取前端域名

静态网站托管页面上方会显示域名：
```
https://sentiment-monitor-xxxxx.tcloudbaseapp.com
```
这就是你的演示地址，发给客户就行。

---

## ✅ 第三步：验证

打开前端域名，走一遍流程：

1. 📝 **注册**（邀请码 `DEMO2026`）
2. 🔑 **登录**
3. 🔍 搜索关键词 → 看 SSE 进度条实时更新
4. 📊 点击「生成 Top 3 综合深度报告」
5. 📥 下载 Markdown 报告

全通过 → 🎉 上线成功！

---

## 🔄 以后更新代码

**后端**：
```bash
cd /home/haili/project/vibecoding/query
scp -r backend/*.py 你的用户名@ssh-alwaysdata.net:/www/backend/
ssh 你的用户名@ssh-alwaysdata.net "systemctl --user restart uvicorn"
# 或去 Alwaysdata 面板点 Restart
```

**前端**：
```bash
cd /home/haili/project/vibecoding/query/frontend
export VITE_API_URL=https://你的用户名.alwaysdata.net/api
npx vite build
# 然后去 CloudBase 面板上传新的 dist/ 文件
```

**快捷方式**（全部更新）：
```bash
# 一次搞定后端+前端
cd /home/haili/project/vibecoding/query
scp -r backend/*.py 你的用户名@ssh-alwaysdata.net:/www/backend/
ssh 你的用户名@ssh-alwaysdata.net "systemctl --user restart uvicorn"
cd frontend && VITE_API_URL=https://你的用户名.alwaysdata.net/api npx vite build
# 再去 CloudBase 面板上传 dist/
```

---

## 🆘 问题排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| `/api/health` 打不开 | 站点没启动 | Alwaysdata → Sites → Restart |
| `/api/health` 502 | 启动命令报错 | SSH 登录手动跑一下 uvicorn 看报错 |
| 前端空白页 | `VITE_API_URL` 没设对 | 检查构建时的域名是否写对了 |
| 注册失败 | 环境变量没生效 | Alwaysdata → Environment 确认 + Restart |
| 搜索一直转圈 | Alwaysdata 网络问题 | 检查后端日志：SSH 登录后看 uvicorn 输出 |
| 刷新页面 404 | SPA 路由没配 | CloudBase 静态托管 → 错误页面设为 index.html |
| Alwaysdata 打不开 | 国内 DNS 解析慢 | 换个浏览器或 DNS 试试 |

---

## 💡 零经验提示

1. **SSH 是文件传输工具** — 把电脑上的代码传到服务器，`scp` = 文件传输，`ssh` = 远程登录
2. **环境变量优先级** — 代码里 `os.getenv("KEY")` 会读你在 Alwaysdata 面板设的值
3. **每次改环境变量后要重启** — Alwaysdata 点 Restart 按钮才能生效
4. **客户演示前先预热** — 免费主机长时间无请求可能变慢，演示前先打开一次 `/api/health`
5. **数据库是本地 SQLite 文件** — 部署更新 .py 代码不会覆盖 `data.db`，用户数据安全
