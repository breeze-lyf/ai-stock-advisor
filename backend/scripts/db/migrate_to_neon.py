import asyncio
import sqlite3
import json
import os
from datetime import datetime
from app.core.config import settings
from sqlalchemy import text, inspect
from app.core.database import engine, Base

async def migrate():
    # 获取连接信息
    db_host = settings.DATABASE_URL.split("@")[-1].split("/")[0]
    print(f"🚀 Target: Neon PostgreSQL ({db_host})")

    # 1. 连接源头
    sqlite_path = "/Users/breeze/Dev/ai-stock-advisor/backend/ai_advisor.db"
    src_conn = sqlite3.connect(sqlite_path)
    src_conn.row_factory = sqlite3.Row
    src_cursor = src_conn.cursor()

    # 2. 清理目标库
    async with engine.begin() as conn:
        print("🧹 Cleaning tables...")
        tables = ["analysis_reports", "portfolios", "market_data_cache", "stock_news", "ai_model_configs", "stocks", "users"]
        for table in tables:
            try: await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except: pass

    # 3. 核心迁移逻辑
    async def migrate_table(table_name):
        # 获取源列
        src_cursor.execute(f"PRAGMA table_info({table_name})")
        src_cols = [c['name'] for c in src_cursor.fetchall()]
        
        # 获取目标列和类型
        def get_target_info(sync_conn):
            inst = inspect(sync_conn)
            cols = inst.get_columns(table_name)
            return {c['name']: str(c['type']).upper() for c in cols}
        
        async with engine.connect() as conn:
            target_types = await conn.run_sync(get_target_info)
        
        valid_cols = [c for c in src_cols if c in target_types]
        print(f"📦 {table_name}: Synchronizing {len(valid_cols)} valid columns.")

        src_cursor.execute(f"SELECT * FROM {table_name}")
        rows = src_cursor.fetchall()
        if not rows: return

        # 准备数据
        data_list = []
        for row in rows:
            data = {k: row[k] for k in valid_cols}
            # 过滤孤儿记录 (如果是 report 表)
            if table_name == "analysis_reports":
                # 简单抽查是否有股票关联
                src_cursor.execute("SELECT 1 FROM stocks WHERE ticker = ?", (data['ticker'],))
                if not src_cursor.fetchone(): continue

            # 类型修正
            for col, val in data.items():
                if val is None: continue
                t_type = target_types.get(col, "")
                if "BOOL" in t_type: data[col] = bool(val)
                elif "TIMESTAMP" in t_type or "DATETIME" in t_type:
                    if isinstance(val, str):
                        try:
                            dt_str = val.replace('Z', '+00:00')
                            data[col] = datetime.fromisoformat(dt_str) if '.' in dt_str or '+' in dt_str else datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                        except: pass
                elif "JSON" in t_type:
                    if val:
                        # 对于 JSON 字段，Postgres 驱动希望接收字符串，由 DB 自己解析为 JSONB
                        if not isinstance(val, str):
                            data[col] = json.dumps(val)
                        else:
                            # 如果是合法的 JSON 字符串就保留，如果是乱码则转空 JSON
                            try: json.loads(val); data[col]=val
                            except: data[col] = "{}"
                    else:
                        data[col] = "{}"

            data_list.append(data)

        # 写入
        if not data_list: return
        
        cols_str = ", ".join(data_list[0].keys())
        vals_str = ", ".join([f":{k}" for k in data_list[0].keys()])
        sql = text(f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str})")

        try:
            # 优先尝试批量写入
            async with engine.begin() as conn:
                await conn.execute(sql, data_list)
            print(f"✅ {table_name}: {len(data_list)} rows migrated (Batch).")
        except Exception as e:
            print(f"⚠️ {table_name}: Batch failed, falling back to row-by-row...")
            success_count = 0
            async with engine.connect() as conn:
                for item in data_list:
                    try:
                        async with conn.begin():
                            await conn.execute(sql, item)
                        success_count += 1
                    except Exception as row_e:
                        if success_count == 0: # 只打印第一个错误防止刷屏
                            print(f"❌ Row Error in {table_name}: {row_e}")
            print(f"✅ {table_name}: {success_count}/{len(data_list)} rows migrated.")

    # 4. 按序执行
    for t in ["users", "stocks", "stock_news", "market_data_cache", "portfolios", "analysis_reports", "ai_model_configs"]:
        try: await migrate_table(t)
        except Exception as e: print(f"🔥 Table {t} failed: {e}")

    # 验证
    async with engine.connect() as conn:
        print("\n📊 --- FINAL SYNC REPORT ---")
        for t in ["users", "stocks", "portfolios", "analysis_reports", "stock_news"]:
            r = await conn.execute(text(f"SELECT count(*) FROM {t}"))
            print(f"{t:18}: {r.scalar()}")

if __name__ == "__main__":
    asyncio.run(migrate())
