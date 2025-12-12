import sqlite3
import pandas as pd
import os
import re

# Config
DB_NAME = "knowledge_base.db"
DATA_FOLDER = "data"
DDL_FILE = "schema.sql"

def parse_table_name(ddl):
    """Extract table name from CREATE TABLE statement."""
    pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?['\"`\[]?(\w+)['\"`\]]?"
    match = re.search(pattern, ddl, re.IGNORECASE)
    return match.group(1) if match else None

def build_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print(f"✅ Created database: {DB_NAME}")

    if not os.path.exists(DDL_FILE):
        print(f"❌ Error: {DDL_FILE} not found!")
        return

    with open(DDL_FILE, "r") as f:
        # Split by semicolon to get individual statements
        statements = [s.strip() for s in f.read().split(";") if s.strip()]

    for ddl in statements:
        if not ddl.upper().startswith("CREATE TABLE"):
            continue
            
        try:
            table_name = parse_table_name(ddl)
            if not table_name: continue

            # 1. Create Table
            cursor.execute(ddl)
            
            # 2. Load CSV (Filename must match table name)
            csv_path = os.path.join(DATA_FOLDER, f"{table_name}.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df.to_sql(table_name, conn, if_exists='append', index=False)
                print(f"🔹 Loaded {table_name}: {len(df)} rows")
            else:
                print(f"⚠️  Table created, but no CSV found: {csv_path}")

        except Exception as e:
            print(f"❌ Error on {table_name}: {e}")

    conn.commit()
    conn.close()
    print("🎉 Database setup complete.")

if __name__ == "__main__":
    build_database()