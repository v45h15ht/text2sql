import sqlite3
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

load_dotenv()

# --- CONFIGURATION ---
SQLITE_DB = os.getenv("SQLITE_DB", "knowledge_base.db")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
API_KEY = os.getenv("GOOGLE_API_KEY")

def load_schema_hybrid():
    print("Building Hybrid Graph (Vector + Keyword)...")
    
    embed_model = GoogleGenAIEmbedding(model="models/text-embedding-004", api_key=API_KEY)
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()

    print("Clearing old data...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        
        # 1. Create Vector Index (Semantic Search)
        try:
            session.run("""
                CREATE VECTOR INDEX table_embeddings IF NOT EXISTS
                FOR (t:Table) ON (t.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 768,
                    `vector.similarity_function`: 'cosine'
                }}
            """)
        except Exception: pass

        # 2. Create Fulltext Index (BM25 Keyword Search) <-- NEW
        try:
            session.run("""
                CREATE FULLTEXT INDEX table_keywords IF NOT EXISTS
                FOR (t:Table) ON EACH [t.description]
            """)
        except Exception: pass

    # 3. Process Tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]

    print(f"Processing {len(tables)} tables...")
    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}')")
        cols = [col[1] for col in cursor.fetchall()]
        col_text = ", ".join(cols)
        
        # This description is what both Vector and BM25 will search against
        semantic_text = f"Table: {table}. Columns: {col_text}"
        
        print(f"   -> Embedding '{table}'...")
        embedding = embed_model.get_text_embedding(semantic_text)
        
        with driver.session() as session:
            # Store Node with Embedding AND Description
            session.run("""
                MERGE (t:Table {name: $name})
                SET t.embedding = $embedding
                SET t.description = $desc
            """, name=table, embedding=embedding, desc=semantic_text)
            
            # Create Column Nodes
            for col in cols:
                session.run("""
                    MATCH (t:Table {name: $t})
                    MERGE (c:Column {name: $c})
                    MERGE (t)-[:HAS_COLUMN]->(c)
                """, t=table, c=col)

        # Foreign Keys
        cursor.execute(f"PRAGMA foreign_key_list('{table}')")
        for fk in cursor.fetchall():
            target = fk[2]
            with driver.session() as session:
                session.run("""
                    MATCH (t1:Table {name: $t1}), (t2:Table {name: $t2})
                    MERGE (t1)-[:RELATED_TO]->(t2)
                """, t1=table, t2=target)

    driver.close()
    conn.close()
    print("Hybrid Knowledge Graph Built!")

if __name__ == "__main__":
    load_schema_hybrid()