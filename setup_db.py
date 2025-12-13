import sqlite3
import pandas as pd
import os
import re

# CONFIGURATION
DB_NAME = "knowledge_base.db"
DATA_FOLDER = "data"
DDL_FILE = "schema.sql"

def parse_table_name(ddl):
    """Extract table name from a CREATE TABLE statement."""
    pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?['\"`\[]?(\w+)['\"`\]]?"
    match = re.search(pattern, ddl, re.IGNORECASE)
    return match.group(1) if match else None

def build_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print(f"Created clean database: {DB_NAME}")

    # 2. Read Schema
    if not os.path.exists(DDL_FILE):
        print(f"Error: {DDL_FILE} not found!")
        return

    with open(DDL_FILE, "r") as f:
        # Split by semicolon to handle multiple statements
        statements = [s.strip() for s in f.read().split(";") if s.strip()]

    print(f"Found {len(statements)} SQL statements in schema.sql")

    # 3. Create Tables & Load Data
    for ddl in statements:
        # We only care about CREATE TABLE statements
        if not ddl.upper().startswith("CREATE TABLE"):
            continue

        try:
            # A. Extract Table Name
            table_name = parse_table_name(ddl)
            if not table_name:
                continue

            # B. Create the Table Structure
            cursor.execute(ddl)
            
            # C. Look for matching CSV
            # checks for 'tablename.csv' inside 'data/' folder
            csv_path = os.path.join(DATA_FOLDER, f"{table_name}.csv")
            
            if os.path.exists(csv_path):
                # Load CSV
                # dtype=str prevents pandas from guessing wrong types (e.g. zip codes as ints)
                df = pd.read_csv(csv_path)
                
                # Write to SQLite
                df.to_sql(table_name, conn, if_exists='append', index=False)
                print(f"Table '{table_name}': Loaded {len(df)} rows from CSV.")
            else:
                print(f"Table '{table_name}': Created, but NO CSV found at {csv_path}")

        except sqlite3.Error as e:
            print(f"SQL Error on {table_name}: {e}")
        except Exception as e:
            print(f"Error processing {table_name}: {e}")

    conn.commit()
    conn.close()
    print("\nDatabase setup complete. You are ready to chat!")

if __name__ == "__main__":
    build_database()