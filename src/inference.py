import os
import logging
import sqlite3
import re
import pandas as pd
from neo4j import GraphDatabase
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.google_genai import utils as gemini_utils
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
SQLITE_DB = os.getenv("SQLITE_DB", "knowledge_base.db")
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing! Check your .env file.")

# Get Logger
logger = logging.getLogger("HYBRID_ENGINE")
logger.setLevel(logging.INFO)

# --- PATCH: Fix 'KeyError: None' ---
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

    def _retrieve_context(self, user_query):
        logger.info(f"[1/3] Searching Knowledge Graph for: '{user_query}'")
        
        # 1. Keyword Extraction
        extract_prompt = f"Identify the database entities (nouns) in this query: '{user_query}'. Return comma-separated list."
        keywords = self.llm.complete(extract_prompt).text.split(",")
        keywords = [k.strip().lower() for k in keywords]
        
        relevant_ddl = []
        
        # 2. Graph Traversal
        with self.neo4j_driver.session() as session:
            cypher = """
            UNWIND $keywords AS kw
            MATCH (t:Table) WHERE toLower(t.name) CONTAINS kw
            OPTIONAL MATCH (t)-[:RELATED_TO]-(neighbor:Table)
            OPTIONAL MATCH (t)-[:HAS_COLUMN]->(c:Column)
            RETURN distinct t.name as table, collect(c.name) as cols, collect(neighbor.name) as neighbors
            """
            result = session.run(cypher, keywords=keywords)
            
            seen = set()
            for r in result:
                t = r["table"]
                if t in seen: continue
                seen.add(t)
                cols = ", ".join([f"{c} TEXT" for c in r["cols"]])
                relevant_ddl.append(f"CREATE TABLE {t} ({cols}); -- Related to: {r['neighbors']}")

        if not relevant_ddl:
            logger.warning("Graph search found nothing. Returning fallback.")
            return "ALL TABLES"
            
        context_str = "\n".join(relevant_ddl)
        logger.info(f"[Context Retrieved]:\n{context_str}")
        return context_str

    def query(self, user_question):
        # Step 1: Get Context
        schema_context = self._retrieve_context(user_question)
        
        # Step 2: Generate SQL
        prompt = f"""
        Write a SQLite query.
        
        Schema Context:
        {schema_context}
        
        Question: {user_question}
        
        Output ONLY raw SQL. No markdown.
        """
        response = self.llm.complete(prompt)
        sql_query = re.sub(r"```sql|```", "", response.text).strip()
        
        logger.info(f"[2/3] Generated SQL:\n{sql_query}")

        # Step 3: Execute SQL
        try:
            conn = sqlite3.connect(SQLITE_DB)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            json_data = df.to_dict(orient="records")
            logger.info(f"[3/3] Execution Success. Retrieved {len(json_data)} rows.")
            logger.debug(f"Sample Data: {json_data[:3]}") # Log first 3 rows
            
            return SimpleResponse(
                f"Found {len(json_data)} records.", 
                metadata={
                    "schema_context": schema_context,
                    "sql_query": sql_query, 
                    "json_data": json_data
                }
            )
        except Exception as e:
            logger.error(f"Execution Failed: {e}")
            return SimpleResponse(f"Error: {str(e)}", metadata={"error": str(e)})

class SimpleResponse:
    def __init__(self, response, metadata=None):
        self.response = response
        self.metadata = metadata or {}

def get_chat_engine():
    return HybridQueryEngine()