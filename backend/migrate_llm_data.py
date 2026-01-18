import sqlite3
import os

db_path = "ai_advisor.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables to update
    tables_to_update = {
        "stocks": [
            ("industry", "VARCHAR"),
            ("market_cap", "FLOAT"),
            ("pe_ratio", "FLOAT"),
            ("forward_pe", "FLOAT"),
            ("eps", "FLOAT"),
            ("dividend_yield", "FLOAT"),
            ("beta", "FLOAT"),
            ("fifty_two_week_high", "FLOAT"),
            ("fifty_two_week_low", "FLOAT")
        ],
        "market_data_cache": [
            ("ma_50", "FLOAT"),
            ("ma_200", "FLOAT"),
            ("macd_val", "FLOAT"),
            ("macd_signal", "FLOAT"),
            ("macd_hist", "FLOAT")
        ]
    }

    for table, columns in tables_to_update.items():
        print(f"Checking table: {table}")
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        for col_name, col_type in columns:
            if col_name not in existing_columns:
                print(f"Adding column {col_name} to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists in {table}.")
    
    # Handle the 'exchange' column replacement in stocks if it existed
    cursor.execute("PRAGMA table_info(stocks)")
    existing_stocks_cols = [column[1] for column in cursor.fetchall()]
    # Actually, we can just leave 'exchange' alone or it might have been removed in model
    # SQLite doesn't support dropping columns easily (before 3.35), so we just add new ones.

    conn.commit()
    conn.close()
    print("Migration completed successfully.")
except Exception as e:
    print(f"Error during migration: {e}")
