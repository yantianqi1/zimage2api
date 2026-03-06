"""任务队列管理"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from models import TaskStatus, TaskInfo
from session_manager import SessionManager, SessionNotReadyError

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """内部任务类"""
    task_id: str
    prompt: str
    model: str
    size: str
    num_images: int
    negative_prompt: str
    seed: Optional[int]
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    images: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class TaskQueue:
    """任务队列管理器"""

    def __init__(self, session_manager: SessionManager):
        self.tasks: Dict[str, Task] = {}
        self.session_manager = session_manager

    async def create_task(
        self,
        task_id: str,
        prompt: str,
        model: str,
        size: str,
        num_images: int,
        negative_prompt: str = "",
        seed: Optional[int] = None
    ) -> Task:
        """创建新任务"""
        task = Task(
            task_id=task_id,
            prompt=prompt,
            model=model,
            size=size,
            num_images=num_images,
            negative_prompt=negative_prompt,
            seed=seed
        )
        self.tasks[task_id] = task
        logger.info(f"创建任务: {task_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return TaskInfo(
            task_id=task.task_id,
            status=task.status,
            prompt=task.prompt,
            model=task.model,
            progress=task.progress,
            images=task.images,
            error_message=task.error_message,
            created_at=task.created_at,
            completed_at=task.completed_at
        )

    async def execute_task(self, task_id: str):
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        try:
            task.status = TaskStatus.PROCESSING
            logger.info(f"开始执行任务: {task_id}")

            def on_progress(p: int):
                task.progress = p

            result = await self.session_manager.generate_image(
                prompt=task.prompt,
                model=task.model,
                size=task.size,
                num_images=task.num_images,
                negative_prompt=task.negative_prompt,
                seed=task.seed,
                progress_callback=on_progress
            )

            if result.get("success"):
                task.status = TaskStatus.COMPLETED
                task.images = result.get("images", [])
                task.progress = 100
                logger.info(f"任务完成: {task_id}, 生成 {len(task.images)} 张图片")
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result.get("error", "未知错误")
                logger.error(f"任务失败: {task_id}, 错误: {task.error_message}")

            task.completed_at = datetime.now().isoformat()

        except SessionNotReadyError as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now().isoformat()
        except Exception as exc:
            logger.error(f"执行任务异常: {exc}")
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now().isoformat()

    async def get_queue_info(self) -> dict:
        """获取队列信息"""
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        return {
            "pending_count": pending,
            "processing_count": processing,
            "completed_count": completed,
            "failed_count": failed,
            "total_count": len(self.tasks)
        }

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        now = datetime.now()
        to_remove = []

        for task_id, task in self.tasks.items():
            created = datetime.fromisoformat(task.created_at)
            if (now - created).total_seconds() > max_age_hours * 3600:
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]

        logger.info(f"清理了 {len(to_remove)} 个旧任务")
