import sys
import asyncio
import streamlit as st
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework import MCPStdioTool
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

st.set_page_config(page_title="Zava AI Analyst", page_icon="📊", layout="wide")
st.title("📊 Zava Enterprise AI Analyst")
st.markdown("Ask me anything about Zava's inventory, sales, or customer data!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def ask_agent(user_input, history_context):
    provider = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Tool 1: Customer Sales (Quick lookups)
    mcp_sales = MCPStdioTool(
        name="zava_customer_sales",
        command=sys.executable,
        args=["src/python/mcp_server/customer_sales/customer_sales.py", "--stdio"],
        description="Quick lookups for product prices and inventory.",
        tool_name_prefix="sales_"
    )

    # Tool 2: Sales Analysis (Deep SQL)
    mcp_analysis = MCPStdioTool(
        name="zava_sales_analysis",
        command=sys.executable,
        args=["src/python/mcp_server/sales_analysis/sales_analysis.py", "--stdio"],
        description="Deep database analysis by writing and executing SQL queries.",
        tool_name_prefix="analysis_"
    )

    # Tool 3: Enterprise Intelligence (Weather, Competitors, Macroeconomics, Sentiment)
    mcp_enterprise = MCPStdioTool(
        name="zava_enterprise_intel",
        command=sys.executable,
        args=["src/python/mcp_server/enterprise/enterprise_mcp.py", "--stdio"],
        tool_name_prefix="enterprise_"
    )

    async with mcp_sales, mcp_analysis, mcp_enterprise:
        agent = provider.as_agent(
            name="ZavaAIAnalyst",
            instructions=(
                "You are an expert Data Analyst and Supply Chain Strategist for the Zava DIY retail store. "
                "You have access to THREE MCP servers: "
                "1. sales_analysis: Use this to query the PostgreSQL database for inventory, products, orders, and stores. "
                "2. customer_sales: Use this for simple customer lookups. "
                "3. enterprise_intel: Use this to get weather, logistics delays, competitor pricing, social sentiment, and macroeconomic indicators. "
                "CRITICAL INSTRUCTION: If a user asks a business question that involves external factors (weather, competitors, sentiment), YOU MUST check the enterprise_intel tools FIRST, and then query the database to find the impacted inventory or stores."
                "Do not answer general programming or unrelated questions."
            ),
            tools=[mcp_sales, mcp_analysis, mcp_enterprise]
        )
        
        full_prompt = f"Conversation History:\n{history_context}\n\nUser's New Question: {user_input}"
        
        response = await agent.run(full_prompt)
        return str(response)

if prompt := st.chat_input("Ask a business question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🧠 Analyst is thinking and querying the database..."):
            history_context = ""
            for msg in st.session_state.messages[:-1]:
                role = "User" if msg["role"] == "user" else "AI"
                history_context += f"{role}: {msg['content']}\n"
            
            response = asyncio.run(ask_agent(prompt, history_context))
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
