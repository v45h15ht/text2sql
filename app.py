import streamlit as st
from src.inference import get_chat_engine
import os

st.set_page_config(page_title="Data Chatbot", layout="wide")

st.title("Chat with your Knowledge Base")
st.markdown("Query your CSV data using natural language.")

# Initialize the Chat Engine once and cache it
@st.cache_resource
def load_agent():
    return get_chat_engine()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Load engine
try:
    agent = load_agent()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle User Input
if prompt := st.chat_input("Ask a question (e.g., 'Total salary by department?'):"):
    # 1. Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing tables and generating SQL..."):
            try:
                # The agent retrieves relevant tables -> Writes SQL -> Executes -> Summarizes
                response = agent.query(prompt)
                st.markdown(response.response)
                
                # Optional: Show the SQL used (good for debugging)
                if hasattr(response, "metadata") and "sql_query" in response.metadata:
                    with st.expander("View generated SQL"):
                        st.code(response.metadata["sql_query"], language="sql")
                
                st.session_state.messages.append({"role": "assistant", "content": response.response})
            except Exception as e:
                st.error(f"An error occurred: {e}")