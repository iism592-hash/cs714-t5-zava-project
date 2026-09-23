"""
stage1_react_agent_scratch.py
=============================================================================
PG Cert in AI - Module: Foundations of Autonomous AI Agents
Course: CS714-T5 | Project: Zava DIY Multi-Agent System

OBJECTIVE:
Build a complete ReAct (Reasoning + Acting) Agent from scratch using pure Python.
No LangChain, no LangGraph, no AutoGen. Pure understanding of the state machine.
=============================================================================
"""

import json
import os
import sys
from typing import Any, Callable, Dict, List
from dotenv import load_dotenv

# Ensure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()


# =============================================================================
# 1. TOOL DEFINITIONS (Actuators)
# =============================================================================
# These are the actual Python functions that interact with databases/APIs.
# In Zava DIY, these correspond to your PostgreSQL queries or FastMCP tools.

def search_products(query: str) -> str:
    """Searches the Zava product catalog by keyword."""
    # Simulated database lookup
    mock_catalog = [
        {"sku": "ZAV-HAM-01", "name": "DeWalt 20V Cordless Hammer Drill", "price": 129.99, "category": "Power Tools"},
        {"sku": "ZAV-BLD-04", "name": "Diablo 7-1/4 In. Circular Saw Blade", "price": 19.97, "category": "Accessories"},
        {"sku": "ZAV-SAF-09", "name": "3M N95 Respirator Mask (10-Pack)", "price": 24.50, "category": "Safety Equipment"},
    ]
    matches = [p for p in mock_catalog if query.lower() in p["name"].lower() or query.lower() in p["category"].lower()]
    return json.dumps(matches if matches else {"message": f"No products matching '{query}' found."})


def check_store_inventory(sku: str, store_name: str) -> str:
    """Checks the stock quantity of a specific SKU in a given Zava DIY store."""
    mock_inventory = {
        ("ZAV-HAM-01", "seattle"): {"in_stock": 14, "aisle": "Aisle 4, Bay B"},
        ("ZAV-HAM-01", "bellevue"): {"in_stock": 0, "aisle": "Aisle 3, Bay A"},
        ("ZAV-SAF-09", "seattle"): {"in_stock": 52, "aisle": "Safety Section, Shelf 1"},
    }
    key = (sku.upper(), store_name.lower())
    result = mock_inventory.get(key, {"in_stock": 0, "message": f"SKU {sku} not found or no stock at {store_name}."})
    return json.dumps(result)


# Tool registry mapping tool names to actual Python callables
TOOL_REGISTRY: Dict[str, Callable[..., str]] = {
    "search_products": search_products,
    "check_store_inventory": check_store_inventory,
}

# Tool schemas adhering to OpenAI / standard function calling specification
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Searches the Zava DIY catalog for products matching a query or keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search for, e.g. 'drill', 'saw', 'safety mask'"
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_store_inventory",
            "description": "Checks the stock quantity and aisle location for a given SKU in a specific store location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "The exact product SKU, e.g. 'ZAV-HAM-01'"
                    },
                    "store_name": {
                        "type": "string",
                        "description": "Store location name: 'Seattle', 'Bellevue', 'Tacoma', 'Spokane'"
                    }
                },
                "required": ["sku", "store_name"],
            },
        },
    }
]


# =============================================================================
# 2. SMART SIMULATION LLM ENGINE
# =============================================================================
class MockLLMResponse:
    """Simulates an LLM response object following the standard OpenAI format."""
    def __init__(self, content: str = None, tool_calls: List[Dict] = None):
        self.content = content
        self.tool_calls = tool_calls or []


def mock_llm_call(messages: List[Dict[str, Any]]) -> MockLLMResponse:
    """
    Simulates realistic LLM reasoning across different customer scenarios:
    1. Multi-Step Chaining (Search -> Check Stock)
    2. Stockout Handling & Cross-Store Recommendation (Bellevue is 0 -> Recommend Seattle)
    3. Zero-Tool Direct Response (General policy question)
    4. Error / Fault-Tolerance (Unknown SKU or DB issue)
    """
    user_query = ""
    for msg in messages:
        if msg["role"] == "user":
            user_query = msg["content"].lower()

    last_msg = messages[-1]

    # SCENARIO A: Direct Question (No Tools Needed)
    if "return policy" in user_query or "hours" in user_query:
        print("\n[LLM REASONING]: This is a general policy question. No database lookup required.")
        return MockLLMResponse(
            content="Zava DIY offers a **30-day return policy** with proof of purchase. "
                    "All physical stores are open Monday to Saturday from 7:00 AM to 8:00 PM."
        )

    # SCENARIO B: Hammer Drill in Bellevue (Stockout & Cross-Store Check)
    if "bellevue" in user_query:
        if last_msg["role"] == "user":
            print("\n[LLM REASONING]: User asked about hammer drills in Bellevue.")
            print("                 Step 1: Search catalog to find the SKU.")
            return MockLLMResponse(
                content=None,
                tool_calls=[{
                    "id": "call_search_bellevue",
                    "function": {
                        "name": "search_products",
                        "arguments": json.dumps({"query": "hammer drill"})
                    }
                }]
            )
        elif last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_search_bellevue":
            print("\n[LLM REASONING]: Found SKU 'ZAV-HAM-01'. Step 2: Check stock at 'Bellevue'.")
            return MockLLMResponse(
                content=None,
                tool_calls=[{
                    "id": "call_stock_bellevue",
                    "function": {
                        "name": "check_store_inventory",
                        "arguments": json.dumps({"sku": "ZAV-HAM-01", "store_name": "Bellevue"})
                    }
                }]
            )
        elif last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_stock_bellevue":
            # Notice the agent dynamically notices in_stock is 0! It decides to check nearby Seattle!
            print("\n[LLM REASONING]: Bellevue has 0 units in stock! Let me check Seattle before answering.")
            return MockLLMResponse(
                content=None,
                tool_calls=[{
                    "id": "call_stock_backup",
                    "function": {
                        "name": "check_store_inventory",
                        "arguments": json.dumps({"sku": "ZAV-HAM-01", "store_name": "Seattle"})
                    }
                }]
            )
        elif last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_stock_backup":
            print("\n[LLM REASONING]: Seattle has 14 units. I can now inform the customer and offer an alternative.")
            return MockLLMResponse(
                content="The **DeWalt 20V Cordless Hammer Drill** is currently **out of stock at Bellevue**. "
                        "However, our nearby **Seattle store has 14 units available** in Aisle 4, Bay B! "
                        "Would you like to reserve one for pickup?"
            )

    # SCENARIO C: Standard Lookup (Seattle)
    if last_msg["role"] == "user":
        print("\n[LLM REASONING]: User wants product & stock info. Step 1: Search catalog.")
        return MockLLMResponse(
            content=None,
            tool_calls=[{
                "id": "call_search_01",
                "function": {
                    "name": "search_products",
                    "arguments": json.dumps({"query": "hammer drill"})
                }
            }]
        )

    if last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_search_01":
        print("\n[LLM REASONING]: Catalog search returned SKU 'ZAV-HAM-01'. Step 2: Query inventory.")
        return MockLLMResponse(
            content=None,
            tool_calls=[{
                "id": "call_stock_02",
                "function": {
                    "name": "check_store_inventory",
                    "arguments": json.dumps({"sku": "ZAV-HAM-01", "store_name": "Seattle"})
                }
            }]
        )

    if last_msg["role"] == "tool" and last_msg["tool_call_id"] == "call_stock_02":
        print("\n[LLM REASONING]: Retrieved inventory details. Ready to synthesize answer.")
        return MockLLMResponse(
            content="We have the **DeWalt 20V Cordless Hammer Drill** ($129.99, SKU: `ZAV-HAM-01`) in stock! "
                    "There are **14 units available** at our **Seattle** store in **Aisle 4, Bay B**."
        )

    return MockLLMResponse(content="I could not find the information you requested.")


# =============================================================================
# 3. THE UNIVERSAL REACT AGENT LOOP
# =============================================================================
def run_agent_loop(user_query: str, max_iterations: int = 5, use_mock: bool = True) -> Dict[str, Any]:
    """
    The fundamental ReAct agent execution loop.
    Returns both the final text and the complete internal state (memory).
    """
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an expert sales and inventory assistant at Zava DIY. "
                "Always look up products and check store stock before answering questions. "
                "Be concise, helpful, and accurate."
            )
        },
        {"role": "user", "content": user_query}
    ]

    print("\n" + "=" * 75)
    print(f">> NEW QUERY: \"{user_query}\"")
    print("=" * 75)

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- [ITERATION {iteration} / {max_iterations}] ---")

        # Step A: PERCEPTION & REASONING
        if use_mock:
            response = mock_llm_call(messages)
        else:
            # LIVE AZURE AI MODEL EXECUTION
            from openai import OpenAI
            client = OpenAI(
                base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_KEY")
            )
            model_name = os.getenv("GPT_MODEL_DEPLOYMENT_NAME", "gpt-5.4-nano")
            
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                max_completion_tokens=300
            )
            response = completion.choices[0].message

        # Step B: TERMINATION CHECK
        if not response.tool_calls:
            print("\n[FINAL ANSWER REACHED - TERMINATING LOOP]")
            messages.append({"role": "assistant", "content": response.content})
            return {"answer": response.content, "iterations": iteration, "history": messages}

        # Step C: TOOL EXECUTION (ACTING)
        if hasattr(response, "model_dump"):
            messages.append(response.model_dump(exclude_unset=True))
        else:
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls
            })

        for tool_call in response.tool_calls:
            if isinstance(tool_call, dict):
                fn_name = tool_call["function"]["name"]
                raw_args = tool_call["function"]["arguments"]
                call_id = tool_call["id"]
            else:
                fn_name = tool_call.function.name
                raw_args = tool_call.function.arguments
                call_id = tool_call.id

            print(f"[TOOL EXECUTION]: '{fn_name}' with args: {raw_args}")

            if fn_name not in TOOL_REGISTRY:
                tool_output = json.dumps({"error": f"Tool '{fn_name}' does not exist."})
            else:
                try:
                    args = json.loads(raw_args)
                    tool_fn = TOOL_REGISTRY[fn_name]
                    tool_output = tool_fn(**args)
                except Exception as e:
                    tool_output = json.dumps({"error": f"Failed to execute {fn_name}: {str(e)}"})

            print(f"  --> Observation: {tool_output}")

            # Step D: FEED OBSERVATION BACK TO STATE
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_output
            })

    return {
        "answer": "Error: Exceeded max iterations.",
        "iterations": max_iterations,
        "history": messages
    }


# =============================================================================
# 4. EXPERIMENTAL TEST SUITE / INTERACTIVE RUNNER
# =============================================================================
if __name__ == "__main__":
    has_live_key = bool(os.getenv("AZURE_OPENAI_KEY"))
    mode_name = "LIVE AZURE AI MODEL (gpt-5.4-nano)" if has_live_key else "SIMULATION MOCK"
    
    print("\n" + "=" * 75)
    print(f" ZAVA DIY AGENT RUNNER | Mode: {mode_name}")
    print("=" * 75)

    test_query = "Do you have any hammer drills in stock at the Seattle store?"
    print(f"\n>> Running Query: \"{test_query}\"")
    
    result = run_agent_loop(user_query=test_query, use_mock=not has_live_key)

    print("\n" + "=" * 70)
    print("📢 AGENT RESPONSE (GENERATED LIVE BY YOUR MODEL):")
    print("=" * 70)
    print(result["answer"])
    print(f"\nIterations Taken: {result['iterations']}")
    print("=" * 70)

