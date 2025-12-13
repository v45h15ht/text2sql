import sqlite3
import os
from neo4j import GraphDatabase

# CONFIGURATION
SQLITE_DB = "knowledge_base.db"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password123")

class SchemaLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        
    def close(self):
        self.driver.close()

    def load_schema(self):
        """
        Reads SQLite metadata and builds a Knowledge Graph of the Schema.
        Nodes: Table, Column
        Edges: HAS_COLUMN, LINKS_TO (Foreign Keys)
        """
        if not os.path.exists(SQLITE_DB):
            print(f"SQLite DB '{SQLITE_DB}' not found. Run setup_db.py first.")
            return

        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()

        # 1. Clean existing graph
        print("Clearing old schema graph...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        # 2. Get All Tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]

        print(f"Building Graph for {len(tables)} tables...")

        for table in tables:
            # Create Table Node
            with self.driver.session() as session:
                session.run("MERGE (t:Table {name: $name})", name=table)

            # 3. Get Columns for this Table
            # Returns: (cid, name, type, notnull, dflt_value, pk)
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[1]
                col_type = col[2]
                
                with self.driver.session() as session:
                    # Create Column Node and Link to Table
                    query = """
                    MATCH (t:Table {name: $table_name})
                    MERGE (c:Column {name: $col_name, type: $col_type})
                    MERGE (t)-[:HAS_COLUMN]->(c)
                    """
                    session.run(query, table_name=table, col_name=col_name, col_type=col_type)

            # 4. Infer Foreign Keys (Naive Name Matching)
            # In a real scenario, parse DDL or PRAGMA foreign_key_list
            # Here we use a heuristic: if column is "user_id", link to "users" table
            cursor.execute(f"PRAGMA foreign_key_list('{table}')")
            fks = cursor.fetchall()
            
            # (id, seq, table, from, to, on_update, on_delete, match)
            for fk in fks:
                target_table = fk[2]
                from_col = fk[3]
                
                with self.driver.session() as session:
                    # Create a direct schema link between tables
                    link_query = """
                    MATCH (t1:Table {name: $t1}), (t2:Table {name: $t2})
                    MERGE (t1)-[:RELATED_TO {key: $key}]->(t2)
                    """
                    session.run(link_query, t1=table, t2=target_table, key=from_col)
                    print(f"Linked '{table}' -> '{target_table}' via {from_col}")

        conn.close()
        print("Schema Graph Built Successfully!")

if __name__ == "__main__":
    loader = SchemaLoader()
    loader.load_schema()
    loader.close()