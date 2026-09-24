import asyncio
import streamlit as st
import os
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add src/python to path so we can import shared modules
SRC_PYTHON_DIR = Path(__file__).resolve().parent.parent
if str(SRC_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_PYTHON_DIR))

# Import our shared core logic
from services.zava_agent_core import get_agent_response

# Load environment variables from .env file
load_dotenv()

st.set_page_config(page_title="Zava AI Analyst", page_icon="??", layout="wide")
st.title("?? Zava Enterprise AI Analyst")
st.markdown("Ask me anything about Zava's inventory, sales, or customer data!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("?? Analyst is thinking and querying the database..."):
            history_context = ""
            for msg in st.session_state.messages[:-1]:
                role = "User" if msg["role"] == "user" else "AI"
                history_context += f"{role}: {msg['content']}\n"
            
            # Call the shared single-agent logic
            response = asyncio.run(get_agent_response(prompt, history_context))
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
