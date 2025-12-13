import streamlit as st
import json
import logging
from src.inference import get_chat_engine

# --- LOGGING SETUP ---
# Create a File Handler to save logs to 'system_trace.log'
file_handler = logging.FileHandler("system_trace.log", mode='a', encoding='utf-8')
console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler] # Log to BOTH file and terminal
)

logger = logging.getLogger("APP")

st.set_page_config(page_title="GraphRAG SQL Bot", layout="wide")
st.title("GraphRAG SQL Bot")

if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def load_agent():
    return get_chat_engine()

agent = load_agent()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "metadata" in msg:
            meta = msg["metadata"]
            if "schema_context" in meta:
                with st.expander("Step 1: Context"): st.code(meta["schema_context"], language="sql")
            if "sql_query" in meta:
                with st.expander("Step 2: SQL"): st.code(meta["sql_query"], language="sql")
            if "json_data" in meta:
                with st.expander("Step 3: Result"): st.json(meta["json_data"])

# Handle Input
if prompt := st.chat_input("Ask a question..."):
    # Log User Input
    logger.info(f"USER QUERY: {prompt}")
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Running Hybrid Pipeline..."):
            try:
                response = agent.query(prompt)
                
                # UI Display
                schema = response.metadata.get("schema_context", "No context")
                with st.expander("Step 1: Knowledge Graph Retrieval (Context)", expanded=True):
                    st.code(schema, language="sql")

                sql = response.metadata.get("sql_query", "No SQL")
                with st.expander("Step 2: SQL Generation", expanded=True):
                    st.code(sql, language="sql")

                data = response.metadata.get("json_data", [])
                with st.expander(f"Step 3: Data Execution ({len(data)} rows)", expanded=True):
                    st.json(data)

                st.markdown(response.response)

                # Log Final Output
                logger.info(f"FINAL ANSWER: {response.response}")
                logger.info("-" * 50) # Separator in log file

                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response.response,
                    "metadata": response.metadata
                })

            except Exception as e:
                logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
                st.error(f"Error: {e}")