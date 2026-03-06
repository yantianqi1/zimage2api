# ZImage API Server

将 zimage.run 的图像生成功能包装为通用 API 服务。

## 架构

- **后端**: FastAPI + Playwright
- **认证**: API Key
- **会话**: Cookie持久化 + 定时刷新
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

# 会话配置
COOKIE_FILE=./cookies.json
SESSION_REFRESH_INTERVAL=3600
```

### 4. 首次启动（人工验证）

```bash
# 以非headless模式启动，完成Cloudflare验证
python scripts/init_session.py
```

浏览器会打开，手动完成人机验证，完成后按回车保存会话。

### 5. 启动API服务

```bash
python main.py
# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000
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
  "width": 1024,
  "height": 1024,
  "num_images": 1
}
```

响应:
```json
{
  "success": true,
  "task_id": "task_xxx",
  "images": [
    "https://files.zimage.run/xxx.jpg"
  ]
}
```

### 查询任务状态

**GET** `/api/v1/tasks/{task_id}`

### 获取模型列表

**GET** `/api/v1/models`

## Docker 部署

```bash
# 构建镜像
docker build -t zimage-api .

# 运行（首次需要挂载显示进行验证）
docker run -p 8000:8000 -v $(pwd)/cookies.json:/app/cookies.json zimage-api
```

## 注意事项

1. **Cloudflare验证**: 会话会过期，需要定期刷新或重新验证
2. **频率限制**: 建议添加请求队列避免触发风控
3. **免费额度**: 文生图免费，但有并发限制

## License

MIT
