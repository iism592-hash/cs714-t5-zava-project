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

# Add agents package, MCP server, and src/python to path
SRC_PYTHON_DIR = Path(__file__).resolve().parent.parent
AGENTS_DIR = SRC_PYTHON_DIR / "agents"
CUSTOMER_SALES_DIR = SRC_PYTHON_DIR / "mcp_server" / "customer_sales"

for p in [SRC_PYTHON_DIR, AGENTS_DIR, CUSTOMER_SALES_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from supervisor import SupervisorAgent
from inventory_specialist import InventorySpecialistAgent
from safety_officer import SafetyOfficerAgent
from synthesizer import SynthesizerAgent, SYNTHESIZER_SYSTEM_PROMPT

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.llm_config import get_azure_or_openai_client, get_model_name

# Environment Variables
MODEL_NAME = get_model_name()
SYNTHESIZER_MODEL_NAME = os.getenv("B2C_SYNTHESIZER_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")
SYNTHESIZER_TOKEN_BUDGET = int(os.getenv("B2C_SYNTHESIZER_MAX_COMPLETION_TOKENS", "4096"))
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
RLS_USER_ID = os.getenv("RLS_USER_ID", "00000000-0000-0000-0000-000000000000")

# Initialize OpenAI client using unified config
client = get_azure_or_openai_client(is_async=False)

app = FastAPI(title="Zava DIY Multi-Agent Backend Service")

# Allow CORS for local web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2500) -> str:
    """Helper to execute inference on deployed Azure AI model."""
    kwargs = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    if "gpt-5" in MODEL_NAME or "o1" in MODEL_NAME or "o3" in MODEL_NAME:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def synthesizer_request_options() -> dict:
    """Keep synthesis model and reasoning allowance separate from other roles."""
    options = {"model": SYNTHESIZER_MODEL_NAME}
    if "gpt-5" in SYNTHESIZER_MODEL_NAME or "o1" in SYNTHESIZER_MODEL_NAME or "o3" in SYNTHESIZER_MODEL_NAME:
        options["max_completion_tokens"] = SYNTHESIZER_TOKEN_BUDGET
        if SYNTHESIZER_MODEL_NAME == "gpt-5-mini":
            options["reasoning_effort"] = "low"
    else:
        options["max_tokens"] = SYNTHESIZER_TOKEN_BUDGET
    return options


def call_synthesizer_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
    """Use the same synthesis settings for the non-streaming fallback."""
    response = client.chat.completions.create(
        **synthesizer_request_options(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError("Synthesizer returned an empty response")
    return content


# Initialize specialized agents
supervisor = SupervisorAgent(call_llm)
inventory_specialist = InventorySpecialistAgent(mcp_url=MCP_SERVER_URL, rls_user_id=RLS_USER_ID)
safety_officer = SafetyOfficerAgent(call_llm)
synthesizer = SynthesizerAgent(call_synthesizer_llm)


def sse_event(payload: dict) -> str:
    """Format dictionary as Server-Sent Event (SSE) string."""
    return f"data: {json.dumps(payload)}\n\n"


def is_cart_intent(text: str) -> bool:
    """Detect if the user is confirming adding items to the cart."""
    clean = text.strip().lower().rstrip(".!?,")
    cart_keywords = ["yes", "yeah", "yep", "sure", "ok", "okay", "add", "add to cart", "add them", "add all", "yes please", "please add", "please add them"]
    if clean in cart_keywords:
        return True
    if ("add" in clean or "put" in clean) and "cart" in clean:
        return True
    return False


# =============================================================================
# STREAMING MULTI-AGENT PIPELINE
# =============================================================================
async def multi_agent_stream(user_query: str) -> AsyncGenerator[str, None]:
    """
    Executes the 4 agents sequentially, streaming their actions and final
    synthesis directly to web_app.py as Server-Sent Events (SSE).
    """
    try:
        # Check if user is confirming adding items to cart
        if is_cart_intent(user_query):
            cart_confirmation = (
                "🛒 **Items Added to Your Shopping Cart!**\n\n"
                "I've added the recommended tools, materials, and safety gear to your shopping cart. "
                "You can review your items in the cart widget at the top-right of your screen.\n\n"
                "Would you like me to walk you through the step-by-step installation instructions, or do you need assistance with anything else?"
            )
            yield sse_event({"content": cart_confirmation, "action": "add_all_to_cart"})
            yield sse_event({"done": True})
            return

        # Step 1: Agent 1 - Supervisor
        msg_1 = "👔 **Supervisor:** Analyzing your project requirements...\n\n"
        yield sse_event({"content": msg_1})
        await asyncio.sleep(0.3)

        plan = supervisor.plan_project(user_query)
        search_terms = plan.get("search_terms") or [plan.get("search_term", "Hammer Drill")]
        task_desc = plan.get("task_description", user_query)

        terms_preview = ", ".join([f"`{t}`" for t in search_terms[:5]])
        msg_plan = f"📋 **Supervisor Plan:** Target tools & supplies: {terms_preview}. Task: *{task_desc}*\n\n"
        yield sse_event({"content": msg_plan})
        await asyncio.sleep(0.3)

        # Step 2: Agent 2 - Inventory Specialist (MCP + pgvector) for ALL items in parallel
        msg_inv = f"📦 **Inventory Specialist:** Querying live database for {len(search_terms)} project items via FastMCP...\n\n"
        yield sse_event({"content": msg_inv})

        # Concurrently lookup all items in the database
        inv_tasks = [inventory_specialist.query_inventory(term) for term in search_terms[:6]]
        inv_results = await asyncio.gather(*inv_tasks, return_exceptions=True)

        combined_inventory = []
        for term, res in zip(search_terms[:6], inv_results):
            if isinstance(res, str) and res.strip() and "row_count\": 0" not in res:
                combined_inventory.append(f"### Live Inventory Grounding for '{term}':\n{res}")
            elif isinstance(res, str) and res.strip():
                combined_inventory.append(f"### Search for '{term}':\n{res}")

        inventory_data = "\n\n".join(combined_inventory) if combined_inventory else "No direct inventory records found."

        # Step 3: Agent 3 - Safety Specialist
        msg_safety = "🦺 **Safety Officer:** Evaluating OSHA protocols, silica hazards & PPE requirements...\n\n"
        yield sse_event({"content": msg_safety})
        await asyncio.sleep(0.3)

        safety_data = safety_officer.evaluate_safety(task_desc)

        # Step 4: Agent 4 - Response Synthesizer
        msg_synth = "📝 **Synthesizer:** Generating your comprehensive DIY Project Blueprint...\n\n---\n\n"
        yield sse_event({"content": msg_synth})
        await asyncio.sleep(0.1)

        print(f"[Synthesizer] Synthesizing blueprint for query: {user_query}", flush=True)
        user_context = (
            f"Customer Question: {user_query}\n\n"
            f"Real Inventory Report from Database:\n{inventory_data}\n\n"
            f"Safety Officer Guidelines:\n{safety_data}"
        )

        full_blueprint = ""
        try:
            # Stream tokens directly so the HTTP connection is never idle
            stream_kwargs = {
                **synthesizer_request_options(),
                "messages": [
                    {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_context}
                ],
                "stream": True
            }
            response_stream = client.chat.completions.create(**stream_kwargs)
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    delta_text = chunk.choices[0].delta.content
                    full_blueprint += delta_text
                    yield sse_event({"content": delta_text})
                    await asyncio.sleep(0.005)
            if not full_blueprint.strip():
                raise RuntimeError("Synthesizer stream returned an empty response")
        except Exception as stream_err:
            print(f"[Synthesizer] Stream error: {stream_err}, falling back to non-streaming", flush=True)
            if not full_blueprint:
                full_blueprint = synthesizer.synthesize_blueprint(user_query, inventory_data, safety_data)
                yield sse_event({"content": full_blueprint})

        # Ensure call-to-action is present if truncated
        if full_blueprint and "Would you like me to add these items to your shopping cart?" not in full_blueprint:
            cta = "\n\n**Would you like me to add these items to your shopping cart?**\n"
            yield sse_event({"content": cta})

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
        "agent_models": {
            "supervisor": MODEL_NAME,
            "inventory_specialist": None,
            "safety_officer": MODEL_NAME,
            "synthesizer": SYNTHESIZER_MODEL_NAME,
        },
        "mcp_endpoint": MCP_SERVER_URL
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 STARTING MULTI-AGENT BACKEND SERVICE ON PORT 8006")
    print("   Endpoint: http://127.0.0.1:8006/chat/stream")
    print("   Health:   http://127.0.0.1:8006/health")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8006)
