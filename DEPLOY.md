# 🚀 部署指南：阿里云函数计算 FC 3.0 Web 函数

> 智能舆情监测平台 — 前后端一体部署，后端内嵌前端静态文件。
> 已验证可用，每一步都经过实际部署确认。

---

## 📋 前置准备

| 准备项 | 说明 |
|--------|------|
| 阿里云账号 | 支付宝实名认证 |
| Serper API Key | https://serper.dev → 免费注册 |
| DeepSeek API Key | https://platform.deepseek.com → 注册充值 ¥1 |

---

## 🖥 部署：FC Web 函数（前后端一体）

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

### 3. 构建前端 + 打包

```bash
cd query/frontend

# 关键：使用相对路径 /api，前后端同域部署
export VITE_API_URL=/api
npm install
npx vite build

# 把构建结果复制到后端 static 目录
cd ../backend
rm -rf static/
mkdir -p static/assets
cp ../frontend/dist/index.html static/
cp ../frontend/dist/assets/* static/assets/
```

### 4. 安装 Python 依赖（关键：必须指定 Python 3.13 + Linux 平台）

```bash
cd query/backend

pip install --target ./pkg \
  --python-version 3.13 \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  -r requirements.txt

# 复制代码 + 前端文件进去
cp *.py requirements.txt ./pkg/
cp -r static/ ./pkg/static/
```

> ⚠️ 不能在本机直接 `pip install` 然后上传，Python 版本不同会导致 C 扩展包无法加载。

### 5. 上传到 FC

FC 函数详情 → **代码** 标签 → 上传 `pkg/` 文件夹。

### 6. 启动命令

```
python3 -m uvicorn index:app --host 0.0.0.0 --port 9000
```

> ⚠️ 必须用 `python3` 不是 `python`；必须用 `index:app` 不是 `main:app`

### 7. 环境变量

创建页面 → 环境变量（表单编辑模式）：

| Key | Value |
|-----|-------|
| `SERPER_API_KEY` | 你的 Serper Key |
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key |
| `JWT_SECRET` | 自定义随机字符串 |
| `TZ` | `Asia/Shanghai` |

### 8. 检查层配置

函数创建后 → **配置** 标签 → 如果有自动挂载的 Flask/Python 层，**必须移除**，否则会冲突报错。

### 9. 触发器配置

**触发器** 标签 → 创建 HTTP 触发器：
- 认证方式：**无需认证**
- 请求方法：全部勾选

### 10. 获取访问地址

触发器详情中复制公网访问地址。一个地址同时提供前端页面和 API：

- 前端：`https://你的地址/`（直接看到登录页面）
- API：`https://你的地址/api/health`

返回：
```json
{"status":"ok","version":"0.4.0"}
```

---

## 🏗 架构

```
用户浏览器
    │
    └── https://xxx.fcapp.run
            │
            ├── /                    → index.html（React SPA）
            ├── /assets/*            → JS/CSS 静态文件
            └── /api/*               → FastAPI 后端接口
                        FastAPI + Uvicorn :9000
                        SQLite (临时存储，演示够用)
```

前端通过 `VITE_API_URL=/api` 构建，请求同域 `/api/*`，无需 CORS，无需 OSS。

---

## 🔄 更新部署

FC 函数详情 → **代码** → 重新打包上传 → 部署。

**只改前端**：本地重新构建 → 替换 `static/` 目录 → 重新上传。
**只改后端**：修改 `.py` 文件 → 重新上传。

---

## 🆘 问题排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `/api/health` 502 | 函数启动失败 | 查看日志：FC → 函数 → 日志 |
| `pydantic_core` 报错 | C 扩展版本不匹配 | 重新用 Python 3.13 平台安装依赖 |
| `No module named 'click'` | 缺少依赖 | 确认上传文件夹包含所有 pip 包 |
| `CAFileNotFound` | 启动命令错了 | 确认用 `python3` 不是 `python` |
| 层冲突报错 | Flask 层挂载冲突 | 配置 → 移除自动挂载的层 |
| 签名认证报错 | 触发器开了签名 | 认证方式改为「无需认证」 |
| 前端白屏 | 静态文件未打包 | 确认 `static/` 目录包含 `index.html` + `assets/` |
| 刷新后 404 | SPA fallback 未生效 | 确认 `main.py` 有 `/{full_path:path}` 兜底路由 |
