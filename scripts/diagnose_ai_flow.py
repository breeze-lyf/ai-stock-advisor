
import os
import sys
import time
import asyncio
import json
import logging
from datetime import datetime
from typing import Any

# 确保可以导入 app 模块
sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv
load_dotenv(dotenv_path="backend/.env")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.user import User
from app.services.market_data import MarketDataService
from app.services.macro_service import MacroService
from app.services.ai_service import AIService
from app.core.prompts import build_stock_analysis_prompt
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnose_ai_flow")

async def diagnose(ticker: str, user_email: str = "test@qq.com"):
    # 1. 数据库设置
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print(f"\n{'='*20} AI 深度分析全链路诊断 {'='*20}")
    print(f"目标股票: {ticker}")
    print(f"模拟用户: {user_email}")
    print(f"{'='*60}\n")

    timing = {}
    
    async with AsyncSessionLocal() as db:
        # 获取用户
        stmt = select(User).where(User.email == user_email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            print(f"错误: 找不到用户 {user_email}")
            return

        repo = AnalysisRepository(db)
        
        # --- Step 1: 市场数据抓取 ---
        start = time.time()
        market_data_obj = await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
        timing["1. 市场数据抓取 (Market Data)"] = time.time() - start
        
        # --- Step 2: 新闻获取 ---
        start = time.time()
        news_articles = await repo.get_latest_stock_news(ticker, limit=5)
        news_data = [
            {"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()}
            for n in news_articles
        ]
        timing["2. 个股新闻获取 (News)"] = time.time() - start
        
        # --- Step 3: 宏观上下文 ---
        start = time.time()
        radar_topics = await MacroService.get_latest_radar(db)
        global_news = await MacroService.get_latest_news(db, limit=5)
        macro_context = ""
        if radar_topics:
            macro_context += "### 宏观热点雷达:\n"
            for topic in radar_topics[:3]:
                macro_context += f"- {topic.title}: {topic.summary}\n"
        timing["3. 宏观上下文检索 (Macro)"] = time.time() - start
        
        # --- Step 4: 历史分析加载 ---
        start = time.time()
        last_report = await repo.get_latest_report(user.id, ticker)
        prev_context = None
        if last_report:
            prev_context = {
                "summary_status": last_report.summary_status,
                "sentiment_score": last_report.sentiment_score,
                "immediate_action": last_report.immediate_action,
            }
        timing["4. 历史记录加载 (History)"] = time.time() - start
        
        # --- Step 5: 构造 Prompt ---
        start = time.time()
        # 准备基础面数据
        fundamental_data = {
            "sector": "Technology", # 简化模拟
            "industry": "Software",
            "market_cap": "N/A",
            "pe_ratio": "N/A",
            "forward_pe": "N/A",
            "beta": "1.0",
        }
        # 准备行情字典
        market_data_dict = {
            "current_price": market_data_obj.current_price if hasattr(market_data_obj, 'current_price') else 0,
            "change_percent": market_data_obj.change_percent if hasattr(market_data_obj, 'change_percent') else 0,
            "rsi_14": getattr(market_data_obj, 'rsi_14', 50),
            "ma_200": getattr(market_data_obj, 'ma_200', 0),
        }
        
        prompt = build_stock_analysis_prompt(
            ticker=ticker,
            market_data=market_data_dict,
            portfolio_data={},
            fundamental_data=fundamental_data,
            news_data=news_data,
            macro_context=macro_context,
            previous_analysis=prev_context
        )
        timing["5. Prompt 构建 (Prompt Building)"] = time.time() - start
        
        # 输出 Prompt 供用户拷贝
        prompt_file = "tmp/last_prompt.txt"
        os.makedirs("tmp", exist_ok=True)
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        
        print(f"👉 确切的 Prompt 已保存至: {os.path.abspath(prompt_file)}")
        print(f"你可以直接打开该文件并将内容发送给大模型。\n")
        
        # --- Step 6: AI 调用 ---
        preferred_model = user.preferred_ai_model or "gemini-1.5-flash"
        print(f"🚀 正在调用 AI 模型: {preferred_model} ... (请耐心等待)")
        
        start = time.time()
        try:
            ai_response = await AIService.generate_analysis(
                ticker=ticker,
                market_data=market_data_dict,
                portfolio_data={},
                news_data=news_data,
                macro_context=macro_context,
                fundamental_data=fundamental_data,
                previous_analysis=prev_context,
                model=preferred_model,
                db=db,
                user_id=user.id
            )
            timing["6. AI 接口响应 (AI Inference)"] = time.time() - start
            print(f"\n✅ AI 响应成功 (长度: {len(ai_response)} 字符)")
        except Exception as e:
            timing["6. AI 接口响应 (AI Inference - FAILED)"] = time.time() - start
            print(f"\n❌ AI 响应失败: {str(e)}")

    # --- 最终耗时统计 ---
    print(f"\n{'='*20} 各环节耗时统计 {'='*20}")
    total_time = 0
    for step, duration in timing.items():
        print(f"{step:<35}: {duration:>7.2f}s")
        total_time += duration
    print(f"{'-'*60}")
    print(f"{'总计总耗时':<35}: {total_time:>7.2f}s")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NBIS"
    asyncio.run(diagnose(ticker))
