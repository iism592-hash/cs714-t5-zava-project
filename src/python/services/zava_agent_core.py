import sys
import os
import asyncio
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework import MCPStdioTool

# Import unified LLM config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.llm_config import get_model_name

async def get_agent_response(user_input: str, history_context: str = "") -> str:
    """
    Core Single-Agent logic for Zava AI Analyst.
    """
    
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if azure_key and azure_endpoint:
        provider = OpenAIChatCompletionClient(
            model=get_model_name(),
            api_key=azure_key,
            base_url=azure_endpoint
        )
    else:
        provider = OpenAIChatCompletionClient(
            model=get_model_name(),
            api_key=openai_key
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
