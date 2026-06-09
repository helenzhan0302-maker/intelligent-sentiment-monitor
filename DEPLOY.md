# 🚀 部署指南：阿里云函数计算 + OSS

> 智能舆情监测平台 — 后端 FC Web 函数 + 前端 OSS 静态托管。
> 已验证可用，每一步都经过实际部署确认。

---

## 📋 前置准备

| 准备项 | 说明 |
|--------|------|
| 阿里云账号 | 支付宝实名认证 |
| Serper API Key | https://serper.dev → 免费注册 |
| DeepSeek API Key | https://platform.deepseek.com → 注册充值 ¥1 |

---

## 🖥 第一步：部署后端（FC Web 函数）

### 1. 进入控制台

https://fc.console.aliyun.com → **函数管理 → 函数列表 → 创建函数** → 类型选 **[Web 函数]**

### 2. 基础配置

| 配置项 | 值 |
|--------|-----|
| 地域 | 华东1（杭州） |
| 函数名称 | `sentiment-backend` |
| 实例类型 | 弹性实例 |
| vCPU | 0.35（默认） |
| 内存 | 0.5 GB（默认） |
| 磁盘 | 512 MB（默认） |
| 最小实例数 | **0**（无请求缩容） |
| 单实例并发度 | 20（默认） |
| 运行环境 | **Python 3.13** |
| 超时时间 | **300 秒** |

### 3. 上传代码

因为 FC 不会自动装依赖，需要把依赖包和代码一起打包上传。

**方式一：使用已打包的文件夹**

桌面上已有 `backend-deploy` 文件夹（包含所有依赖 + 代码），直接拖拽上传。

**方式二：自己打包**

```bash
# 安装依赖（关键：必须指定 Python 3.13 + Linux 平台）
pip install --target ./pkg \
  --python-version 3.13 \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  -r requirements.txt

# 复制代码文件进去
cp *.py requirements.txt ./pkg/

# 上传 pkg/ 文件夹
```

> ⚠️ 不能在本机直接 `pip install` 然后上传，Python 版本不同会导致 C 扩展包无法加载。

### 4. 启动命令

```
python3 -m uvicorn index:app --host 0.0.0.0 --port 9000
```

> ⚠️ 必须用 `python3` 不是 `python`；必须用 `index:app` 不是 `main:app`

### 5. 环境变量

创建页面 → 环境变量（表单编辑模式）：

| Key | Value |
|-----|-------|
| `SERPER_API_KEY` | 你的 Serper Key |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key |
| `JWT_SECRET` | 自定义随机字符串 |
| `TZ` | `Asia/Shanghai` |

### 6. 检查层配置

函数创建后 → **配置** 标签 → 如果有自动挂载的 Flask/Python 层，**必须移除**，否则会冲突报错。

### 7. 触发器配置

**触发器** 标签 → 创建 HTTP 触发器：
- 认证方式：**无需认证**
- 请求方法：全部勾选

### 8. 获取后端地址

触发器详情中复制公网访问地址，验证：
```
https://你的地址/api/health
```
返回：
```json
{"status":"ok","version":"0.4.0"}
```

---

## 🌐 第二步：部署前端（OSS 静态托管）

### 1. 创建 Bucket

打开 https://oss.console.aliyun.com → **Bucket 列表 → 创建 Bucket**：

| 配置 | 值 |
|------|-----|
| Bucket 名称 | `sentiment-frontend` |
| 区域 | **华东1（杭州）** — 和后端同区域 |
| 存储类型 | **标准存储**（不要选冷归档） |
| 读写权限 | **公共读** |

### 2. 构建前端

```bash
cd frontend
export VITE_API_URL=https://你的后端地址/api
npm install
npx vite build
```

构建产物在 `frontend/dist/` 目录。

### 3. 上传文件

OSS Bucket → **文件管理** → 上传 `dist/` 文件夹内的全部文件：
- `index.html`
- `assets/index-xxx.js`
- `assets/index-xxx.css`

### 4. 配置静态网站

Bucket → **基础设置** → **静态页面**：

| 配置 | 值 |
|------|-----|
| 默认首页 | `index.html` |
| 默认 404 页 | **`index.html`** |

> ⚠️ 404 页必须设为 `index.html`，否则刷新页面会白屏（React SPA 路由）。

### 5. 获取前端地址

Bucket → **概览** → **访问域名** → 复制 OSS 外网域名。

---

## ✅ 第三步：验证全流程

打开 OSS 前端域名，完成以下测试：

1. 注册（邀请码 `DEMO2026`）
2. 登录
3. 搜索关键词 → SSE 进度条实时更新
4. 生成综合报告
5. 下载 Markdown

---

## 🔄 更新部署

**后端更新**：FC 函数详情 → **代码** → 重新上传 Python 文件 → 部署

**前端更新**：本地重新构建 → OSS 覆盖上传新文件

---

## 🆘 问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `/api/health` 502 | 函数启动失败 | 查看日志：FC → 函数 → 日志 |
| `pydantic_core` 报错 | C 扩展版本不匹配 | 重新用 Python 3.13 平台安装依赖 |
| `No module named 'click'` | 缺少依赖 | 确认上传文件夹包含所有 pip 包 |
| `CAFileNotFound` | 启动命令错了 | 确认用 `python3` 不是 `python` |
| 层冲突报错 | Flask 层挂载冲突 | 配置 → 移除自动挂载的层 |
| 前端刷新 404 | OSS 没配 SPA 路由 | 静态页面 404 页设为 index.html |
| 签名认证报错 | 触发器开了签名 | 认证方式改为「无需认证」 |
