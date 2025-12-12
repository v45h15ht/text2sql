import os
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("DB_CONNECTOR")

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.critical("DATABASE_URL is missing!")
        raise ValueError("DATABASE_URL not set in .env")
    
    logger.info(f"Connecting to database at: {db_url}")
    
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    
    try:
        engine = create_engine(db_url, connect_args=connect_args)
        return engine
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e