"""
ZImage 会话初始化脚本 - 首次运行时使用
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from zimage_client import ZImageBrowser


async def main():
    print("=" * 50)
    print("ZImage 会话初始化工具")
    print("=" * 50)
    print()
    print("此脚本将打开浏览器并访问 zimage.run")
    print("请完成人机验证后，按回车保存会话")
    print()

    # 使用非headless模式以便人工验证
    browser = ZImageBrowser(
        cookie_file="./cookies.json",
        headless=False  # 必须可见才能完成验证
    )

    try:
        print("正在启动浏览器...")
        print("提示: 如果浏览器闪退，请确保系统允许运行 Chrome")
        await browser.init(slow_mo=500, timeout=60000)

        print()
        print("✓ 浏览器已打开")
        print("请完成以下操作：")
        print("1. 如果看到人机验证，请手动点击完成")
        print("2. 确保页面正常加载（能看到输入框）")
        print("3. 按回车键保存会话")
        print()

        # 等待用户按回车
        input("按回车键保存会话...")

        await browser.save_session()
        print()
        print("✓ 会话已保存到 cookies.json")
        print("✓ 现在可以使用 headless 模式启动 API 服务")

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        print("\n尝试解决方案:")
        print("1. 确保 Chrome 没有被系统阻止（系统设置 -> 隐私与安全性）")
        print("2. 手动关闭所有 Chrome 进程后重试")
        print("3. 重启电脑后重试")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await browser.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
