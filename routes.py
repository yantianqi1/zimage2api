import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from models import (
    GenerateRequest, GenerateResponse, TaskInfo, TaskStatus,
    HealthResponse, ModelInfo, SessionStatusResponse
)
from auth import verify_api_key
from session_manager import SessionNotReadyError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def get_task_queue(request: Request):
    return request.app.state.task_queue


def get_session_manager(request: Request):
    return request.app.state.session_manager


@router.post("/generate", response_model=GenerateResponse)
async def generate_image(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    提交图片生成任务

    - **prompt**: 提示词，描述你想要生成的图片
    - **model**: 模型名称，可选 turbo, beyond-reality, redcraft, dark-beast
    - **size**: 图片尺寸，可选 1024x1024, 1024x1536, 1536x1024, 1920x1080, 1080x1920
    - **num_images**: 生成数量，1-4
    - **negative_prompt**: 负面提示词（可选）
    - **seed**: 随机种子（可选）
    """
    session_manager = get_session_manager(http_request)
    task_queue = get_task_queue(http_request)

    try:
        await session_manager.require_ready()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": getattr(exc, "code", "session_required"),
                "status": getattr(exc, "session_status", "needs_human"),
                "message": str(exc),
            },
        ) from exc

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    await task_queue.create_task(
        task_id=task_id,
        prompt=request.prompt,
        model=request.model.value,
        size=request.size.value,
        num_images=request.num_images,
        negative_prompt=request.negative_prompt or "",
        seed=request.seed
    )

    # 后台执行生成
    background_tasks.add_task(task_queue.execute_task, task_id)

    return GenerateResponse(
        success=True,
        task_id=task_id,
        message="任务已提交",
        estimated_time=30  # 预估30秒
    )


@router.get("/tasks/{task_id}", response_model=TaskInfo)
async def get_task_status(
    task_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """查询任务状态和结果"""
    task_queue = get_task_queue(request)
    task = await task_queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task


@router.get("/tasks/{task_id}/wait")
async def wait_for_task(
    task_id: str,
    request: Request,
    timeout: Optional[int] = 60,
    api_key: str = Depends(verify_api_key)
):
    """
    等待任务完成（轮询接口）

    - **timeout**: 最长等待时间（秒），默认60秒
    """
    task_queue = get_task_queue(request)
    task = await task_queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 轮询等待
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        task = await task_queue.get_task(task_id)

        if task.status == TaskStatus.COMPLETED:
            return {
                "success": True,
                "status": "completed",
                "images": task.images
            }
        elif task.status == TaskStatus.FAILED:
            return {
                "success": False,
                "status": "failed",
                "error": task.error_message
            }

        await asyncio.sleep(2)

    # 超时
    return {
        "success": False,
        "status": task.status.value,
        "message": "等待超时，请继续轮询查询"
    }


@router.get("/models", response_model=list[ModelInfo])
async def list_models(api_key: str = Depends(verify_api_key)):
    """获取支持的模型列表"""
    return [
        ModelInfo(
            id="turbo",
            name="Z-Image Turbo",
            description="最快的模型，适合日常使用",
            supports_size=["1024x1024", "1024x1536", "1536x1024"],
            is_free=True
        ),
        ModelInfo(
            id="beyond-reality",
            name="Beyond Reality",
            description="人像优化模型，擅长生成逼真人物",
            supports_size=["1024x1024", "1024x1536", "1536x1024"],
            is_free=True
        ),
        ModelInfo(
            id="redcraft",
            name="RedCraft (红潮造相)",
            description="艺术风格模型，适合创意作品",
            supports_size=["1024x1024", "1024x1536", "1536x1024"],
            is_free=True
        ),
        ModelInfo(
            id="dark-beast",
            name="Dark Beast (红潮黑兽)",
            description="暗黑/奇幻风格",
            supports_size=["1024x1024", "1024x1536", "1536x1024"],
            is_free=True
        ),
        ModelInfo(
            id="flux2-klein",
            name="FLUX2-Klein",
            description="FLUX2 模型",
            supports_size=["1024x1024", "1024x1536", "1536x1024", "1920x1080", "1080x1920"],
            is_free=True
        ),
    ]


@router.get("/session/status", response_model=SessionStatusResponse)
async def session_status(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """获取会话状态。"""
    session_manager = get_session_manager(request)
    return await session_manager.get_status()


@router.post("/session/handoff/start", response_model=SessionStatusResponse)
async def session_handoff_start(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """开始人工接管。"""
    session_manager = get_session_manager(request)
    return await session_manager.start_handoff()


@router.post("/session/handoff/complete", response_model=SessionStatusResponse)
async def session_handoff_complete(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """完成人工接管。"""
    session_manager = get_session_manager(request)
    return await session_manager.complete_handoff()


@router.post("/session/refresh", response_model=SessionStatusResponse)
async def session_refresh(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """刷新会话。"""
    session_manager = get_session_manager(request)
    return await session_manager.refresh()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """健康检查接口（无需认证）"""
    session_manager = get_session_manager(request)
    task_queue = get_task_queue(request)
    session = await session_manager.get_status()
    queue_info = await task_queue.get_queue_info()

    return HealthResponse(
        status="healthy" if session.ready else "degraded",
        browser_ready=session.ready,
        queue_size=queue_info["pending_count"],
        session_status=session.status.value,
    )
