"""ZImage API Server - 主入口"""
from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings, settings as default_settings
from routes import router as api_router
from session_manager import SessionManager
from task_queue import TaskQueue

logging.basicConfig(
    level=getattr(logging, default_settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def create_app(settings=None, session_manager=None, task_queue=None) -> FastAPI:
    """创建 FastAPI 应用。"""
    active_settings = settings or get_settings()
    active_session_manager = session_manager or SessionManager(active_settings)
    active_task_queue = task_queue or TaskQueue(active_session_manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = active_settings
        app.state.session_manager = active_session_manager
        app.state.task_queue = active_task_queue
        await active_session_manager.startup()
        try:
            yield
        finally:
            await active_session_manager.shutdown()

    app = FastAPI(
        title="ZImage API",
        description="ZImage.run 图像生成 API 服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.session_manager = active_session_manager
    app.state.task_queue = active_task_queue

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/")
    async def root():
        return {
            "name": "ZImage API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/health",
            "session": "/api/v1/session/status",
        }

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    logger.info(f"启动服务器: {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower()
    )
