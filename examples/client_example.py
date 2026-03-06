"""
ZImage API 使用示例

此文件演示如何在你的项目中调用 ZImage API
"""
import requests
import time
import json


class ZImageAPI:
    """ZImage API 客户端"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def generate(
        self,
        prompt: str,
        model: str = "turbo",
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: str = "",
        wait: bool = True,
        timeout: int = 120
    ) -> dict:
        """
        生成图片

        Args:
            prompt: 提示词
            model: 模型名称
            size: 图片尺寸
            num_images: 生成数量
            negative_prompt: 负面提示词
            wait: 是否等待完成
            timeout: 最长等待时间(秒)

        Returns:
            {
                "success": bool,
                "images": [图片URL列表],
                "task_id": 任务ID
            }
        """
        # 1. 提交生成请求
        url = f"{self.base_url}/api/v1/generate"
        data = {
            "prompt": prompt,
            "model": model,
            "size": size,
            "num_images": num_images,
            "negative_prompt": negative_prompt
        }

        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()

        result = response.json()
        task_id = result["task_id"]

        print(f"任务已提交: {task_id}")

        if not wait:
            return result

        # 2. 等待任务完成
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            print(f"  状态: {status['status']}, 进度: {status.get('progress', 0)}%")

            if status["status"] == "completed":
                print(f"✓ 生成完成！获得 {len(status['images'])} 张图片")
                return {
                    "success": True,
                    "images": status["images"],
                    "task_id": task_id
                }
            elif status["status"] == "failed":
                print(f"✗ 生成失败: {status.get('error_message', '未知错误')}")
                return {
                    "success": False,
                    "error": status.get("error_message"),
                    "task_id": task_id
                }

            time.sleep(3)

        print("✗ 等待超时")
        return {
            "success": False,
            "error": "timeout",
            "task_id": task_id
        }

    def get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_models(self) -> list:
        """获取模型列表"""
        url = f"{self.base_url}/api/v1/models"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def download_image(self, image_url: str, save_path: str):
        """下载生成的图片"""
        response = requests.get(image_url)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        print(f"图片已保存: {save_path}")


# 使用示例
if __name__ == "__main__":
    # 配置
    API_URL = "http://localhost:8000"  # 你的API地址
    API_KEY = "your-secret-api-key"     # 你的API密钥

    # 创建客户端
    client = ZImageAPI(API_URL, API_KEY)

    # 示例1: 简单的文生图
    print("=" * 50)
    print("示例1: 文生图")
    print("=" * 50)

    result = client.generate(
        prompt="一只可爱的橘猫，趴在窗台上晒太阳，温暖的午后光线，写实风格，高清",
        model="turbo",
        size="1024x1024",
        num_images=1
    )

    if result["success"]:
        for i, img_url in enumerate(result["images"]):
            client.download_image(img_url, f"output_{i}.jpg")

    # 示例2: 指定负面提示词
    print("\n" + "=" * 50)
    print("示例2: 使用负面提示词")
    print("=" * 50)

    result = client.generate(
        prompt="美丽的天空之城，浮空岛屿，瀑布，梦幻场景",
        negative_prompt="模糊，低质量，变形，多余的手指，丑陋",
        model="beyond-reality",
        size="1024x1536",
        num_images=2
    )

    if result["success"]:
        for i, img_url in enumerate(result["images"]):
            client.download_image(img_url, f"fantasy_{i}.jpg")

    # 示例3: 列出可用模型
    print("\n" + "=" * 50)
    print("可用模型列表:")
    print("=" * 50)

    models = client.list_models()
    for model in models:
        print(f"- {model['id']}: {model['name']}")
        print(f"  {model['description']}")
        print(f"  免费: {'是' if model['is_free'] else '否'}")
        print()

    # 示例4: 异步调用（不等待结果）
    print("=" * 50)
    print("示例4: 异步调用")
    print("=" * 50)

    result = client.generate(
        prompt="未来城市夜景，霓虹灯，赛博朋克风格",
        model="dark-beast",
        wait=False  # 不等待完成
    )

    print(f"任务ID: {result['task_id']}")
    print("你可以稍后查询此任务的状态")
