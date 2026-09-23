"""
safety_officer.py
=============================================================================
Safety Officer Agent for Zava DIY Retail System
Responsible for:
1. OSHA compliance and occupational hazard identification
2. Respirable crystalline silica dust precautions & HEPA filtration
3. Personal Protective Equipment (PPE) checklists
=============================================================================
"""

SAFETY_SYSTEM_PROMPT = (
    "You are the Chief Safety Officer at Zava DIY. "
    "Evaluate the customer's proposed project for safety hazards. "
    "Provide: "
    "1. Critical Safety Hazards (e.g. electrical shock, respirable crystalline silica dust, sharp edges, kickback). "
    "2. Required Personal Protective Equipment (PPE) (e.g. FFP3/P3 respirator, safety goggles, cut-resistant gloves). "
    "3. Crucial Pre-Execution Step (e.g. wire/stud scanner, dust containment, main power disconnect). "
    "Keep it concise, bulleted, and authoritative."
)


class SafetyOfficerAgent:
    """Agent responsible for identifying physical DIY hazards and mandating OSHA/PPE protocols."""

    def __init__(self, llm_caller) -> None:
        self.call_llm = llm_caller

    def evaluate_safety(self, task_description: str) -> str:
        """Evaluates DIY task for physical, electrical, and respiratory hazards."""
        return self.call_llm(SAFETY_SYSTEM_PROMPT, f"Project task: {task_description}")
