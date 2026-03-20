import sqlite3
import os

db_path = "ai_advisor.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking for preferred_data_source column...")
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "preferred_data_source" not in columns:
        print("Adding preferred_data_source column to users table...")
        # Add column with default value 'ALPHA_VANTAGE'
        cursor.execute("ALTER TABLE users ADD COLUMN preferred_data_source VARCHAR DEFAULT 'ALPHA_VANTAGE'")
        conn.commit()
        print("Successfully added column.")
    else:
        print("Column preferred_data_source already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error migrating database: {e}")
