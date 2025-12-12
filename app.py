import streamlit as st
import pandas as pd
from src.inference import get_chat_engine
from src.db_utils import get_engine
import json
import logging
import os
import datetime


if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("APP_MAIN")
# -----------------------------------

st.set_page_config(page_title="Data Chatbot", layout="wide")
st.title("Chat with your Knowledge Base")

@st.cache_resource
def load_agent():
    logger.info("Attempting to load Chat Agent...")
    return get_chat_engine()

if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    agent = load_agent()
    logger.info("Chat Agent loaded successfully.")
except Exception as e:
    logger.critical(f"Failed to load agent: {e}", exc_info=True)
    st.error(f"Error loading database: {e}")
    st.stop()

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "json_data" in message:
            with st.expander("View JSON Result"):
                st.json(message["json_data"])

# Handle User Input
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    logger.info(f"USER QUERY: {prompt}")
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = agent.query(prompt)
                
                # --- LOGGING THE GENERATED SQL ---
                generated_sql = response.metadata.get("sql_query")
                if generated_sql:
                    logger.info(f"GENERATED SQL: {generated_sql}")
                else:
                    logger.warning("No SQL was generated for this query.")
                # ---------------------------------
                
                json_result = None
                
                if generated_sql:
                    engine = get_engine()
                    df = pd.read_sql(generated_sql, engine)
                    json_result = df.to_dict(orient="records")
                    
                    logger.info(f"EXECUTION SUCCESS: Retrieved {len(df)} rows.")
                    
                    final_text = f"{response.response}\n\n*I have generated a JSON response with {len(df)} records.*"
                else:
                    final_text = response.response

                st.markdown(final_text)
                
                if json_result:
                    st.json(json_result)
                    
                message_data = {"role": "assistant", "content": final_text}
                if json_result:
                    message_data["json_data"] = json_result
                
                st.session_state.messages.append(message_data)

            except Exception as e:
                logger.error(f"QUERY ERROR: {e}", exc_info=True)
                st.error(f"An error occurred: {e}")