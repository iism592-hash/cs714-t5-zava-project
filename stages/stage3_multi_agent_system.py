"""
stage3_multi_agent_system.py
=============================================================================
PG Cert in AI - Stage 3: Hierarchical Multi-Agent System (MAS)
Course: CS714-T5 | Project: Zava DIY Retail System

TEAM COMPOSITION:
1. Supervisor Agent:    Analyzes user intent and breaks query into subtasks.
2. Inventory Specialist: Queries FastMCP (port 8000) for real products & prices.
3. Safety Specialist:    Evaluates hazards, PPE requirements, and OSHA guidelines.
4. Synthesizer Agent:   Combines data into a polished, professional customer plan.
=============================================================================
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List
from dotenv import load_dotenv

# Ensure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

# OpenAI SDK for live Azure Model
from openai import OpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Azure Configuration from .env
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY")
MODEL_NAME = os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-5.4-nano")
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
RLS_USER_ID = os.getenv("RLS_USER_ID", "00000000-0000-0000-0000-000000000000")

# Initialize OpenAI client targeting your Azure deployment
client = OpenAI(
    base_url=AZURE_ENDPOINT,
    api_key=AZURE_KEY
)


# =============================================================================
# HELPER: LLM INFERENCE WRAPPER
# =============================================================================
def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Calls your deployed Azure AI model with a specific persona."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_completion_tokens=max_tokens
    )
    return response.choices[0].message.content


# =============================================================================
# AGENT 1: SUPERVISOR (ORCHESTRATOR)
# =============================================================================
def supervisor_agent(user_query: str) -> Dict[str, Any]:
    """
    Supervisor Agent analyzes the project request and determines:
    1. Key hardware tools / materials to look up in inventory.
    2. The nature of the physical work to evaluate for safety hazards.
    """
    print("\n" + "=" * 70)
    print("👔 [AGENT 1: SUPERVISOR] Analyzing customer request...")
    print("=" * 70)

    system_prompt = (
        "You are the Lead Project Supervisor at Zava DIY Hardware. "
        "Analyze the customer's project request. Identify: "
        "1. The primary power tool or material to search for in our inventory (pick ONE specific keyword like 'Hammer Drill', 'Circular Saw', or 'Concrete Screws'). "
        "2. The physical task being performed. "
        "Output ONLY a valid JSON object with keys: 'search_term' and 'task_description'."
    )

    raw_output = call_llm(system_prompt, user_query)
    
    # Clean possible markdown fences
    clean_json = raw_output.replace("```json", "").replace("```", "").strip()
    try:
        plan = json.loads(clean_json)
    except Exception:
        # Fallback if model wraps in text
        plan = {"search_term": "Hammer Drill", "task_description": user_query}

    print(f"  --> Identified Target Tool to Search: '{plan.get('search_term')}'")
    print(f"  --> Identified Project Task:         '{plan.get('task_description')}'")
    return plan


# =============================================================================
# AGENT 2: INVENTORY SPECIALIST (FAST-MCP CLIENT)
# =============================================================================
async def inventory_specialist_agent(search_term: str) -> str:
    """
    Inventory Specialist connects directly to the live FastMCP server on port 8000
    and queries PostgreSQL for live stock, price, and aisle locations.
    """
    print("\n" + "=" * 70)
    print("📦 [AGENT 2: INVENTORY SPECIALIST] Querying live database via FastMCP...")
    print("=" * 70)

    headers = {"X-RLS-User-ID": RLS_USER_ID}

    try:
        async with streamablehttp_client(MCP_SERVER_URL, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print(f"  --> Calling FastMCP tool: get_products_by_name(product_name='{search_term}')")
                result = await session.call_tool(
                    name="get_products_by_name",
                    arguments={"product_name": search_term, "max_rows": 3}
                )
                
                inventory_data = ""
                for item in result.content:
                    if item.type == "text":
                        inventory_data += item.text

                print("  --> Real database records received!")
                return inventory_data

    except Exception as e:
        print(f"  ⚠️ Error connecting to MCP server: {e}")
        return f"Database query failed: {str(e)}"


# =============================================================================
# AGENT 3: DIY SAFETY SPECIALIST
# =============================================================================
def safety_specialist_agent(task_description: str) -> str:
    """
    Safety Specialist evaluates project hazards, silica dust, noise levels,
    and mandatory Personal Protective Equipment (PPE) per OSHA standards.
    """
    print("\n" + "=" * 70)
    print("🦺 [AGENT 3: SAFETY SPECIALIST] Evaluating project risks & PPE...")
    print("=" * 70)

    system_prompt = (
        "You are the Chief Safety Officer at Zava DIY. "
        "Evaluate the customer's proposed project for safety hazards. "
        "Provide: "
        "1. Critical Safety Hazards (e.g. electrical cables in wall, silica dust inhalation, eye injury). "
        "2. Required Personal Protective Equipment (PPE) (e.g., N95 respirator, impact safety goggles, ear protection). "
        "3. Crucial Pre-Drilling Step (e.g., use a stud/wire detector). "
        "Keep it concise, bulleted, and authoritative."
    )

    safety_advice = call_llm(system_prompt, f"Project task: {task_description}")
    print("  --> Safety guidelines and PPE checklist compiled!")
    return safety_advice


# =============================================================================
# AGENT 4: RESPONSE SYNTHESIZER
# =============================================================================
def synthesizer_agent(user_query: str, inventory_info: str, safety_info: str) -> str:
    """
    Synthesizer Agent takes the inventory data and safety checklist
    and weaves them into an organized, customer-ready DIY Project Blueprint.
    """
    print("\n" + "=" * 70)
    print("📝 [AGENT 4: SYNTHESIZER] Merging data into cohesive project guide...")
    print("=" * 70)

    system_prompt = (
        "You are the Senior Customer Project Advisor at Zava DIY. "
        "Synthesize the findings from our Inventory Specialist and Safety Officer into a "
        "complete, structured, beautiful response for the customer. "
        "Include: "
        "1. Project Overview & Recommendation. "
        "2. Recommended Tools & In-Stock Availability (cite real prices and stock from the inventory report). "
        "3. Mandatory Safety Precautions & PPE Checklist. "
        "4. Step-by-Step Execution Advice. "
        "Format with clean Markdown, bold headers, and bullet points."
    )

    user_context = (
        f"Customer Question: {user_query}\n\n"
        f"Real Inventory Report from Database:\n{inventory_info}\n\n"
        f"Safety Officer Guidelines:\n{safety_info}"
    )

    final_guide = call_llm(system_prompt, user_context, max_tokens=800)
    return final_guide


# =============================================================================
# MULTI-AGENT ORCHESTRATOR PIPELINE
# =============================================================================
async def run_multi_agent_pipeline(customer_query: str):
    print("\n" + "#" * 75)
    print(f"🚀 LAUNCHING MULTI-AGENT ORCHESTRATION PIPELINE")
    print(f"Customer Question: \"{customer_query}\"")
    print("#" * 75)

    # 1. Supervisor Plans
    plan = supervisor_agent(customer_query)

    # 2. Parallel / Specialist Execution
    search_term = plan.get("search_term", "Hammer Drill")
    task_desc = plan.get("task_description", customer_query)

    # Run inventory lookup (I/O bound over MCP)
    inventory_data = await inventory_specialist_agent(search_term)

    # Run safety analysis
    safety_data = safety_specialist_agent(task_desc)

    # 3. Synthesizer Weaves Output
    final_output = synthesizer_agent(customer_query, inventory_data, safety_data)

    print("\n" + "=" * 75)
    print("🎉 FINAL MULTI-AGENT OUTPUT DELIVERED TO CUSTOMER:")
    print("=" * 75)
    print(final_output)
    print("=" * 75)


if __name__ == "__main__":
    query = (
        "I need to drill into a solid concrete foundation wall to mount a heavy garage storage rack. "
        "What tools do I need, do you have them in stock, and what safety steps should I follow?"
    )
    asyncio.run(run_multi_agent_pipeline(query))
