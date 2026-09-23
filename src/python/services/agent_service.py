"""
agent_service.py
=============================================================================
PG Cert in AI - Stage 4: Multi-Agent Streaming Backend Service (Port 8006)
Course: CS714-T5 | Project: Zava DIY Retail Multi-Agent System

This service connects:
- Web App UI (Port 8005) <--> Agent Backend (Port 8006) <--> FastMCP (Port 8000)
- Streams real-time thoughts and actions of the 4 specialist agents to the web client.
=============================================================================
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator
from dotenv import load_dotenv

# Ensure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Root path resolution
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

# Add agents package and MCP server to path
AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
CUSTOMER_SALES_DIR = Path(__file__).resolve().parent.parent / "mcp_server" / "customer_sales"

for p in [AGENTS_DIR, CUSTOMER_SALES_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from supervisor import SupervisorAgent
from inventory_specialist import InventorySpecialistAgent
from safety_officer import SafetyOfficerAgent
from synthesizer import SynthesizerAgent

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# OpenAI SDK for live Azure Model
from openai import OpenAI

# Environment Variables
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY")
MODEL_NAME = os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-5.4-nano")
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
RLS_USER_ID = os.getenv("RLS_USER_ID", "00000000-0000-0000-0000-000000000000")

# Initialize OpenAI client
client = OpenAI(
    base_url=AZURE_ENDPOINT,
    api_key=AZURE_KEY
)

app = FastAPI(title="Zava DIY Multi-Agent Backend Service")

# Allow CORS for local web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Helper to execute inference on deployed Azure AI model."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_completion_tokens=max_tokens
    )
    return response.choices[0].message.content


# Initialize specialized agents
supervisor = SupervisorAgent(call_llm)
inventory_specialist = InventorySpecialistAgent(mcp_url=MCP_SERVER_URL, rls_user_id=RLS_USER_ID)
safety_officer = SafetyOfficerAgent(call_llm)
synthesizer = SynthesizerAgent(call_llm)


def sse_event(payload: dict) -> str:
    """Format dictionary as Server-Sent Event (SSE) string."""
    return f"data: {json.dumps(payload)}\n\n"


# =============================================================================
# STREAMING MULTI-AGENT PIPELINE
# =============================================================================
async def multi_agent_stream(user_query: str) -> AsyncGenerator[str, None]:
    """
    Executes the 4 agents sequentially, streaming their actions and final 
    synthesis directly to web_app.py as Server-Sent Events (SSE).
    """
    try:
        # Step 1: Agent 1 - Supervisor
        msg_1 = "👔 **Supervisor:** Analyzing your project requirements...\n\n"
        yield sse_event({"content": msg_1})
        await asyncio.sleep(0.3)

        plan = supervisor.plan_project(user_query)
        search_term = plan.get("search_term", "Hammer Drill")
        task_desc = plan.get("task_description", user_query)

        msg_plan = f"📋 **Supervisor Plan:** Target tool: `{search_term}`. Task: *{task_desc}*\n\n"
        yield sse_event({"content": msg_plan})
        await asyncio.sleep(0.3)

        # Step 2: Agent 2 - Inventory Specialist (MCP + pgvector)
        msg_inv = f"📦 **Inventory Specialist:** Querying live database for `{search_term}` via FastMCP...\n\n"
        yield sse_event({"content": msg_inv})
        inventory_data = await inventory_specialist.query_inventory(search_term)

        # Step 3: Agent 3 - Safety Specialist
        msg_safety = "🦺 **Safety Officer:** Evaluating OSHA protocols, silica hazards & PPE requirements...\n\n"
        yield sse_event({"content": msg_safety})
        await asyncio.sleep(0.3)

        safety_data = safety_officer.evaluate_safety(task_desc)

        # Step 4: Agent 4 - Response Synthesizer
        msg_synth = "📝 **Synthesizer:** Generating your comprehensive DIY Project Blueprint...\n\n---\n\n"
        yield sse_event({"content": msg_synth})
        await asyncio.sleep(0.3)

        final_guide = synthesizer.synthesize_blueprint(user_query, inventory_data, safety_data)

        # Stream the synthesized output
        yield sse_event({"content": final_guide})

        # Signal completion to web_app.py
        yield sse_event({"done": True})

    except Exception as e:
        yield sse_event({"error": f"Agent error: {str(e)}"})
        yield sse_event({"done": True})


# =============================================================================
# ENDPOINTS
# =============================================================================
@app.post("/chat/stream")
async def chat_stream_endpoint(request: Request):
    """Streaming endpoint called by web_app.py."""
    data = await request.json()
    user_message = data.get("message", "")
    
    return StreamingResponse(
        multi_agent_stream(user_message),
        media_type="text/event-stream"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint called by web_app.py."""
    return {
        "status": "healthy",
        "service": "multi_agent_backend",
        "model": MODEL_NAME,
        "mcp_endpoint": MCP_SERVER_URL
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 STARTING MULTI-AGENT BACKEND SERVICE ON PORT 8006")
    print("   Endpoint: http://127.0.0.1:8006/chat/stream")
    print("   Health:   http://127.0.0.1:8006/health")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8006)
