import os
import logging
import sqlite3
import re
import pandas as pd
from neo4j import GraphDatabase
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import utils as gemini_utils
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
SQLITE_DB = os.getenv("SQLITE_DB", "knowledge_base.db")
API_KEY = os.getenv("GOOGLE_API_KEY")

logger = logging.getLogger("HYBRID_ENGINE")
logger.setLevel(logging.INFO)

# --- PATCH ---
original_chat_from_gemini_response = gemini_utils.chat_from_gemini_response
def patched_chat_from_gemini_response(response, chat_history):
    if response.candidates and response.candidates[0].content:
        if response.candidates[0].content.role is None:
            response.candidates[0].content.role = "model"
    return original_chat_from_gemini_response(response, chat_history)
gemini_utils.chat_from_gemini_response = patched_chat_from_gemini_response

class HybridQueryEngine:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        self.llm = GoogleGenAI(model="models/gemini-2.5-pro", api_key=API_KEY, temperature=0.0)
        self.embed_model = GoogleGenAIEmbedding(model="models/text-embedding-004", api_key=API_KEY)

    def _retrieve_context(self, user_query):
        logger.info(f"[1/3] Hybrid Search (Vector + BM25) for: '{user_query}'")
        
        query_embedding = self.embed_model.get_text_embedding(user_query)
        
        relevant_ddl = []
        
        with self.neo4j_driver.session() as session:
            # --- HYBRID CYPHER QUERY ---
            # CHANGED: Renamed $query to $bm25_term to avoid Python keyword collision
            cypher = """
            CALL {
                CALL db.index.vector.queryNodes('table_embeddings', 5, $embedding)
                YIELD node AS t, score
                RETURN t, score, 'vector' as source
                
                UNION
                
                CALL db.index.fulltext.queryNodes('table_keywords', $bm25_term)
                YIELD node AS t, score
                RETURN t, score, 'bm25' as source
            }
            
            WITH t, max(score) as max_score, collect(source) as sources
            
            OPTIONAL MATCH (t)-[:RELATED_TO]-(neighbor:Table)
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            
            RETURN 
                distinct t.name as table, 
                collect(distinct c.name) as cols, 
                collect(distinct neighbor.name) as neighbors, 
                max_score,
                sources
            ORDER BY max_score DESC
            LIMIT 5
            """
            
            bm25_query = user_query.replace(" ", " OR ")
            
            # CHANGED: Passed as 'bm25_term' instead of 'query'
            result = session.run(cypher, embedding=query_embedding, bm25_term=bm25_query)
            
            seen = set()
            for r in result:
                t = r["table"]
                if t in seen: continue
                seen.add(t)
                
                logger.info(f"   --> Found '{t}' via {r['sources']} (Score: {r['max_score']:.2f})")
                
                cols = ", ".join([f"{c} TEXT" for c in r["cols"]])
                relevant_ddl.append(f"CREATE TABLE {t} ({cols}); -- Related to: {r['neighbors']}")

        if not relevant_ddl:
            return "ALL TABLES (No matches found)"
            
        return "\n".join(relevant_ddl)

    def query(self, user_question):
        # Step 1: Retrieval
        schema_context = self._retrieve_context(user_question)
        
        # Step 2: SQL Gen
        prompt = f"""
        Write a SQLite query.
        Schema Context:
        {schema_context}
        Question: {user_question}
        Output ONLY raw SQL.
        """
        response = self.llm.complete(prompt)
        sql_query = re.sub(r"```sql|```", "", response.text).strip()
        logger.info(f"[2/3] SQL: {sql_query}")

        # Step 3: Execution
        try:
            conn = sqlite3.connect(SQLITE_DB)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            json_data = df.to_dict(orient="records")
            logger.info(f"[3/3] Retrieved {len(json_data)} rows.")
            
            return SimpleResponse(
                f"Found {len(json_data)} records.", 
                metadata={"schema_context": schema_context, "sql_query": sql_query, "json_data": json_data}
            )
        except Exception as e:
            return SimpleResponse(f"Error: {str(e)}", metadata={"error": str(e)})

class SimpleResponse:
    def __init__(self, response, metadata=None):
        self.response = response
        self.metadata = metadata or {}

def get_chat_engine():
    return HybridQueryEngine()