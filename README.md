# ZImage API Server

将 `zimage.run` 的图像生成功能包装为通用 API 服务，并支持服务器端会话托管。

## 架构

- **后端**: FastAPI + Playwright
- **认证**: API Key
- **会话**: `storage_state` 持久化 + 服务器端 noVNC 人工接管
- **队列**: 异步任务处理

## 快速开始

### 1. 环境要求

- Python 3.9+
- Chrome/Chromium 浏览器
- Linux服务器（2核4G以上推荐）

### 2. 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 3. 配置

复制 `.env.example` 为 `.env`，填写配置：

```bash
# API配置
API_KEY=your-secret-api-key
PORT=8000

# 浏览器配置
HEADLESS=true
BROWSER_TIMEOUT=60000
BROWSER_LOCALE=zh-CN
BROWSER_TIMEZONE=UTC

# 会话配置
COOKIE_FILE=./data/cookies.json
STATE_FILE=./data/storage-state.json
HANDOFF_ENABLED=true
NOVNC_BASE_URL=http://<server-ip>:6080/vnc.html?autoconnect=true&resize=remote
```

### 4. 首次启动（服务器端人工接管）

```bash
# 启动完整服务栈
docker compose up --build -d
```

然后访问：

- API: `http://<server-ip>:8000/docs`
- noVNC 接管页: `http://<server-ip>:6080/vnc.html?autoconnect=true&resize=remote`

首次无状态文件时，会话状态会进入 `needs_human`。此时：

1. 调用 `POST /api/v1/session/handoff/start`
2. 打开返回的 `handoff_url`
3. 在服务器端浏览器中完成验证
4. 调用 `POST /api/v1/session/handoff/complete`

### 5. 启动API服务

```bash
docker compose up -d
```

## API 文档

### 生图接口

**POST** `/api/v1/generate`

Headers:
```
Authorization: Bearer your-api-key
Content-Type: application/json
```

请求体:
```json
{
  "prompt": "一只可爱的猫咪",
  "model": "turbo",
  "size": "1024x1024",
  "num_images": 1
}
```

响应:
```json
{
  "success": true,
  "task_id": "task_xxx",
  "message": "任务已提交",
  "estimated_time": 30
}
```

### 查询任务状态

**GET** `/api/v1/tasks/{task_id}`

### 获取模型列表

**GET** `/api/v1/models`

### 会话管理

- `GET /api/v1/session/status`
- `POST /api/v1/session/handoff/start`
- `POST /api/v1/session/handoff/complete`
- `POST /api/v1/session/refresh`

## Docker 部署

```bash
docker compose up --build -d
```

## 注意事项

1. **Cloudflare验证**: v1 不做自动绕过，首次或失效后需要服务器端人工接管
2. **会话文件**: `data/storage-state.json` 和 `data/cookies.json` 都保存在服务器卷内
3. **频率限制**: 当前仍是单浏览器串行执行

## License

MIT
