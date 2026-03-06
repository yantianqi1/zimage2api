"""数据模型定义"""
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ImageModel(str, Enum):
    """支持的模型列表"""
    TURBO = "turbo"
    BEYOND_REALITY = "beyond-reality"
    REDCRAFT = "redcraft"
    DARK_BEAST = "dark-beast"
    FLUX2_KLEIN = "flux2-klein"


class ImageSize(str, Enum):
    """支持的图片尺寸"""
    SQUARE = "1024x1024"      # 1:1
    PORTRAIT = "1024x1536"    # 2:3
    LANDSCAPE = "1536x1024"   # 3:2
    WIDE = "1920x1080"        # 16:9
    MOBILE = "1080x1920"      # 9:16


class GenerateRequest(BaseModel):
    """生图请求"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="提示词")
    negative_prompt: Optional[str] = Field(None, max_length=500, description="负面提示词")
    model: ImageModel = Field(default=ImageModel.TURBO, description="模型")
    size: ImageSize = Field(default=ImageSize.SQUARE, description="图片尺寸")
    num_images: int = Field(default=1, ge=1, le=4, description="生成数量")
    seed: Optional[int] = Field(None, description="随机种子")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "一只可爱的猫咪，趴在窗台上晒太阳，写实风格",
                "negative_prompt": "模糊，低质量，变形",
                "model": "turbo",
                "size": "1024x1024",
                "num_images": 1
            }
        }


class GenerateResponse(BaseModel):
    """生图响应"""
    success: bool
    task_id: str
    message: str
    images: List[str] = []
    estimated_time: int = 0  # 预估等待时间(秒)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"       # 排队中
    PROCESSING = "processing" # 生成中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败
    TIMEOUT = "timeout"       # 超时


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    status: TaskStatus
    prompt: str
    model: str
    progress: int = 0  # 进度 0-100
    images: List[str] = []
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    description: str
    supports_size: List[str]
    is_free: bool


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    browser_ready: bool
    queue_size: int
    version: str = "1.0.0"
