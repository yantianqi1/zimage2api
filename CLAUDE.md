# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZImage API Server is a FastAPI-based service that wraps the image generation functionality of zimage.run (a Chinese AI image generation website) into a REST API. It uses Playwright to automate browser interactions with the target site.

## Architecture

### Core Components

- **FastAPI** (`main.py`): Web framework providing REST endpoints
- **ZImageBrowser** (`zimage_client.py`): Playwright-based browser automation for interacting with zimage.run
- **TaskQueue** (`task_queue.py`): Singleton task manager that handles image generation jobs asynchronously
- **Routes** (`routes.py`): API endpoints under `/api/v1` prefix

### Data Flow

1. Client sends POST `/api/v1/generate` with prompt and parameters
2. TaskQueue creates a task and triggers background execution
3. ZImageBrowser uses Playwright to:
   - Navigate to zimage.run/zh
   - Input prompt, select model/size/quantity
   - Click generate button
   - Poll for results by detecting image elements
4. Results are returned as CDN URLs from files.zimage.run

### Key Challenge: Cloudflare Verification

The target site uses Cloudflare Turnstile verification. The solution requires:
- First-time manual verification via `scripts/init_session.py` (opens browser, user completes captcha)
- Cookies are persisted to `cookies.json` and reused
- If verification expires, re-run the init script

## Development Commands

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (required)
playwright install chromium
playwright install-deps chromium  # Linux only
```

### Configuration

```bash
cp .env.example .env
# Edit .env - set API_KEY, HEADLESS, COOKIE_FILE
```

### First-time Session Initialization (Required)

```bash
# Must run this before starting the API server
# Opens browser for manual Cloudflare verification
python scripts/init_session.py
```

### Run Development Server

```bash
# After init_session.py completes and saves cookies
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment

```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/generate` | POST | Bearer | Submit image generation task |
| `/api/v1/tasks/{id}` | GET | Bearer | Get task status |
| `/api/v1/tasks/{id}/wait` | GET | Bearer | Poll until complete (blocking) |
| `/api/v1/models` | GET | Bearer | List available models |
| `/api/v1/health` | GET | None | Health check |

## Key Files

- `zimage_client.py`: Browser automation logic, handles anti-detection measures
- `task_queue.py`: Singleton pattern, manages browser lifecycle and task execution
- `models.py`: Pydantic models for request/response validation
- `scripts/init_session.py**: Must run first to establish authenticated session

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | required | Bearer token for API authentication |
| `HEADLESS` | true | Run browser without GUI (false for init_session.py) |
| `COOKIE_FILE` | ./cookies.json | Path to persisted session cookies |
| `BROWSER_TIMEOUT` | 60000 | Page load timeout (ms) |

## Troubleshooting

- **Browser fails to start**: Run `playwright install-deps chromium`
- **Cloudflare blocks requests**: Re-run `init_session.py`, cookies expired
- **Memory issues**: Requires 2GB+ RAM, Chrome is memory-intensive
