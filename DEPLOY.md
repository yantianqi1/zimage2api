# ZImage API Server 部署指南

## 服务器环境要求

- **系统**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **内存**: 最低 2GB，推荐 4GB+
- **CPU**: 2核+
- **磁盘**: 10GB+ 可用空间
- **网络**: 能够访问 zimage.run

## 部署步骤

### 1. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

# 安装Chrome依赖（Playwright需要）
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm-dev libxkbcommon-dev \
    libgbm-dev libasound-dev libatspi2.0-0 libxshmfence-dev
```

### 2. 部署应用

```bash
# 克隆/上传代码到服务器
cd /opt
mkdir zimage-api && cd zimage-api

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 3. 初始化会话（关键步骤）

由于Cloudflare验证，你需要在服务器上完成首次验证：

```bash
# 方法1: 如果有图形界面（桌面环境）
python scripts/init_session.py

# 方法2: 本地完成验证后上传cookie文件
# 在本地运行 init_session.py 完成验证
# 然后将 cookies.json 上传到服务器的 /opt/zimage-api/

# 方法3: 使用 X11 转发（需要SSH -X）
export DISPLAY=:0
python scripts/init_session.py
```

### 4. 配置环境变量

```bash
cp .env.example .env
nano .env
```

修改以下配置：
```
API_KEY=你的强密码密钥
PORT=8000
HOST=0.0.0.0
HEADLESS=true
COOKIE_FILE=./cookies.json
```

### 5. 启动服务

**方式1: 直接运行（测试）**
```bash
python main.py
```

**方式2: 使用 systemd**

创建服务文件：
```bash
sudo nano /etc/systemd/system/zimage-api.service
```

内容：
```ini
[Unit]
Description=ZImage API Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/zimage-api
Environment="PATH=/opt/zimage-api/venv/bin"
Environment="API_KEY=your-secret-key"
Environment="HEADLESS=true"
Environment="COOKIE_FILE=/opt/zimage-api/cookies.json"
ExecStart=/opt/zimage-api/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable zimage-api
sudo systemctl start zimage-api
sudo systemctl status zimage-api
```

**方式3: 使用 Docker**

```bash
# 构建镜像
docker-compose build

# 确保cookie文件存在
touch ./data/cookies.json

# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 6. 配置Nginx反向代理（推荐）

```bash
sudo nano /etc/nginx/sites-available/zimage-api
```

配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/zimage-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. 配置HTTPS（可选但推荐）

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 维护

### 查看日志

```bash
# systemd方式
sudo journalctl -u zimage-api -f

# docker方式
docker-compose logs -f

# 直接运行方式
tail -f /opt/zimage-api/api.log
```

### 重启服务

```bash
# systemd
sudo systemctl restart zimage-api

# docker
docker-compose restart
```

### 更新代码

```bash
cd /opt/zimage-api
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart zimage-api
```

### 刷新会话

当遇到验证失败时，需要重新获取cookie：

1. 停止服务
2. 运行 `python scripts/init_session.py` 完成验证
3. 重新启动服务

## 故障排查

### 1. 浏览器启动失败

```bash
# 检查依赖
playwright install-deps chromium

# 检查权限
ls -la ~/.cache/ms-playwright/
```

### 2. Cloudflare验证失败

- 检查cookie文件是否存在且有效
- 尝试本地完成验证后上传cookie
- 检查IP是否被Cloudflare标记

### 3. 内存不足

```bash
# 添加swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 4. 服务无法访问

```bash
# 检查端口
netstat -tlnp | grep 8000

# 检查防火墙
sudo ufw status
sudo ufw allow 8000
```

## API使用示例

```bash
# 测试接口
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的猫咪",
    "model": "turbo",
    "size": "1024x1024",
    "num_images": 1
  }'
```
