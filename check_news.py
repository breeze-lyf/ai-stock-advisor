
import sqlite3
import os

db_path = "backend/ai_advisor.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, title, link FROM stock_news ORDER BY publish_time DESC LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Ticker: {row[0]}, Title: {row[1]}, Link: {row[2]}")
    conn.close()
else:
    print("Database not found")
