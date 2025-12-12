import os
import logging
from llama_index.core import SQLDatabase, VectorStoreIndex, Settings
from llama_index.core.objects import (
    SQLTableNodeMapping,
    ObjectIndex,
    SQLTableSchema,
)
from llama_index.core.query_engine import SQLTableRetrieverQueryEngine
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from src.db_utils import get_engine
from sqlalchemy import inspect


logger = logging.getLogger("INFERENCE_ENGINE")

def get_chat_engine():
    logger.info("Initializing Inference Engine...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Google API Key is missing in .env")
    
    Settings.llm = GoogleGenAI(
        model="models/gemini-1.5-pro", 
        api_key=api_key,
        temperature=0.1
    )
    
    Settings.embed_model = GoogleGenAIEmbedding(
        model="models/text-embedding-004", 
        api_key=api_key
    )

    engine = get_engine()
    sql_database = SQLDatabase(engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    logger.info(f"Found {len(table_names)} tables in database: {table_names}")
    
    table_schema_objs = [SQLTableSchema(table_name=t) for t in table_names]
    table_node_mapping = SQLTableNodeMapping(sql_database)
    
    logger.info("Building Object Index for schemas...")
    table_schema_index = ObjectIndex.from_objects(
        table_schema_objs,
        table_node_mapping,
        VectorStoreIndex,
    )

    query_engine = SQLTableRetrieverQueryEngine(
        sql_database,
        table_schema_index.as_retriever(similarity_top_k=5),
    )
    
    logger.info("Query Engine ready.")
    return query_engine