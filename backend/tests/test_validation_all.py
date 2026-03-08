import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.analysis import AnalysisReport
from app.schemas.analysis import AnalysisResponse
from sqlalchemy import select
from app.api.v1.endpoints.analysis import extract_entry_zone_fallback

async def main():
    async with SessionLocal() as db:
        # Fetch ALL reports
        stmt = select(AnalysisReport)
        result = await db.execute(stmt)
        reports = result.scalars().all()
        
        failed = 0
        for r in reports:
            snapshot = r.input_context_snapshot or {}
            
            # Handle if snapshot is somehow a string
            if isinstance(snapshot, str):
                import json
                try:
                    snapshot = json.loads(snapshot)
                except Exception as e:
                    snapshot = {}
                    
            market_data_snap = snapshot.get("market_data", {}) if isinstance(snapshot, dict) else {}
            snap_price = market_data_snap.get("current_price") if isinstance(market_data_snap, dict) else None
            
            try:
                item = {
                    "ticker": r.ticker,
                    "analysis": r.ai_response_markdown,
                    "sentiment_score": float(r.sentiment_score) if r.sentiment_score else None,
                    "summary_status": r.summary_status,
                    "risk_level": r.risk_level,
                    "technical_analysis": r.technical_analysis,
                    "fundamental_news": r.fundamental_news,
                    "action_advice": r.action_advice,
                    "investment_horizon": r.investment_horizon,
                    "confidence_level": r.confidence_level,
                    "immediate_action": r.immediate_action,
                    "target_price": r.target_price,
                    "stop_loss_price": r.stop_loss_price,
                    "entry_zone": r.entry_zone or extract_entry_zone_fallback(r.action_advice),
                    "entry_price_low": r.entry_price_low,
                    "entry_price_high": r.entry_price_high,
                    "rr_ratio": r.rr_ratio,
                    "scenario_tags": r.scenario_tags,
                    "thought_process": r.thought_process,
                    "is_cached": True,
                    "model_used": r.model_used,
                    "created_at": r.created_at,
                    "history_price": snap_price
                }
                response_obj = AnalysisResponse(**item)
            except Exception as e:
                failed += 1
                print(f"Validation FAILED for ID: {r.id}, Ticker: {r.ticker}")
                print(f"Error: {e}")
                
        print(f"Total reports: {len(reports)}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
