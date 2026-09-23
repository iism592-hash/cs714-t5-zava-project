"""
synthesizer.py
=============================================================================
Synthesizer / Customer Project Advisor Agent
Responsible for:
1. Synthesizing inventory results and safety protocols
2. Generating a complete, structured customer blueprint
3. Enforcing zero hallucination (strictly using real prices and stock counts)
=============================================================================
"""

SYNTHESIZER_SYSTEM_PROMPT = (
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


class SynthesizerAgent:
    """Agent responsible for assembling the customer project blueprint."""

    def __init__(self, llm_caller) -> None:
        self.call_llm = llm_caller

    def synthesize_blueprint(self, customer_query: str, inventory_report: str, safety_guidelines: str) -> str:
        """Combines inventory grounding and safety rules into an actionable customer blueprint."""
        user_context = (
            f"Customer Question: {customer_query}\n\n"
            f"Real Inventory Report from Database:\n{inventory_report}\n\n"
            f"Safety Officer Guidelines:\n{safety_guidelines}"
        )
        return self.call_llm(SYNTHESIZER_SYSTEM_PROMPT, user_context, max_tokens=800)
