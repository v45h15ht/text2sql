import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set in .env")
    
    # check_same_thread=False is required for SQLite in Streamlit
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    
    return create_engine(db_url, connect_args=connect_args)