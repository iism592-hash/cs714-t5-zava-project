"""
supervisor.py
=============================================================================
Supervisor Agent for Zava DIY Retail System
Responsible for:
1. Natural language query decomposition
2. Primary tool/material keyword extraction for inventory grounding
3. Formulating the specific physical DIY task description
=============================================================================
"""

import json
from typing import Dict, Any


SUPERVISOR_SYSTEM_PROMPT = (
    "You are the Lead Project Supervisor at Zava DIY Hardware. "
    "Analyze the customer request. Identify: "
    "1. The primary power tool or material to search for in our inventory "
    "(pick ONE specific keyword like 'Hammer Drill', 'Circular Saw', 'Tile Adhesive', or 'Concrete Screws'). "
    "2. The physical task being performed. "
    "Output ONLY a valid JSON object with keys: 'search_term' and 'task_description'."
)


class SupervisorAgent:
    """Agent responsible for understanding customer intent and planning specialist tasks."""

    def __init__(self, llm_caller) -> None:
        self.call_llm = llm_caller

    def plan_project(self, customer_query: str) -> Dict[str, str]:
        """Decomposes customer request into target search term and task description."""
        raw_output = self.call_llm(SUPERVISOR_SYSTEM_PROMPT, customer_query)
        clean_json = raw_output.replace("```json", "").replace("```", "").strip()
        try:
            plan = json.loads(clean_json)
            search_term = plan.get("search_term", "Hammer Drill")
            task_desc = plan.get("task_description", customer_query)
            return {"search_term": search_term, "task_description": task_desc}
        except Exception:
            return {"search_term": "Hammer Drill", "task_description": customer_query}
