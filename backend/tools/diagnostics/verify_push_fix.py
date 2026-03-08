import asyncio
import sys
import os

# 路径对位
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.notification_service import NotificationService
from app.core.database import SessionLocal
from app.models.notification import NotificationLog
from sqlalchemy import delete

async def test_dedupe_logic():
    print("--- 开始飞书推送逻辑验证 ---")
    
    async with SessionLocal() as db:
        # 1. 清理测试数据
        await db.execute(delete(NotificationLog).where(NotificationLog.type.in_(["MACRO_SUMMARY", "HOURLY_NEWS_SUMMARY"])))
        await db.commit()
    
    print("1. 测试摘要类消息 (应绕过 24h 锁定)")
    # 第一次发送
    res1 = await NotificationService.send_feishu_card(
        title="[Test] 第一次摘要推送",
        content="这应该成功",
        msg_type="MACRO_SUMMARY"
    )
    print(f"首次推送结果: {res1}")
    
    # 立即第二次发送 (应被 1min 去重拦截)
    res2 = await NotificationService.send_feishu_card(
        title="[Test] 第二次摘要推送 (瞬时)",
        content="这应该被拦截",
        msg_type="MACRO_SUMMARY"
    )
    print(f"瞬时重复推送结果 (期望 False): {res2}")
    
    print("\n2. 测试本地降级逻辑 (模拟 Tavily 失败)")
    from app.services.macro_service import MacroService
    # 直接调用内部逻辑验证是否能正常跑通 (由于没有 mock tavily，我们观察日志是否出现 Fallback successful)
    topics = await MacroService.update_global_radar()
    print(f"雷达更新检测完成，探测到主题数: {len(topics)}")

if __name__ == "__main__":
    asyncio.run(test_dedupe_logic())
