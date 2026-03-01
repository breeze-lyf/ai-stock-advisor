import asyncio
import os
import sys

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notification_service import NotificationService

async def test_notifications():
    print("Testing NotificationService...")
    
    # 1. 测试基础卡片 (由于没有真正的 Webhook URL，此处仅验证逻辑是否报错)
    # 如果 FEISHU_WEBHOOK_URL 为空，代码应该打印警告并返回 False
    res1 = await NotificationService.send_feishu_card(
        title="Test Notification",
        content="This is a test content from antigravity agent."
    )
    print(f"Basic Card Result (expected False if no URL): {res1}")
    
    # 2. 测试宏观预警
    res2 = await NotificationService.send_macro_alert(
        title="测试宏观事件",
        summary="这是一个模拟的高热度宏观事件摘要。",
        heat_score=95.5
    )
    print(f"Macro Alert Result: {res2}")
    
    # 3. 测试价格预警
    res3 = await NotificationService.send_price_alert(
        ticker="AAPL",
        name="Apple Inc.",
        current_price=185.2,
        target_price=185.0,
        is_stop_loss=True
    )
    print(f"Price Alert Result: {res3}")

if __name__ == "__main__":
    asyncio.run(test_notifications())
