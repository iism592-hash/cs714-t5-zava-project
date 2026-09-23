# Academic Coursework Stages: Evolutionary Multi-Agent Architecture
**Course:** CS714-T5 | **Project:** Zava DIY Retail Autonomous Multi-Agent System

This directory documents the progression of building autonomous agentic capability from first principles up to hierarchical multi-agent collaboration, as required for academic evaluation.

---

## 📂 Progression Overview

| Milestone | Script | Key Mechanics Demonstrated |
|---|---|---|
| **Stage 1** | [`stage1_react_agent_scratch.py`](stage1_react_agent_scratch.py) | • Raw ReAct cycle (`Thought -> Action -> Observation`) without third-party agent frameworks<br>• Explicit tool calling schemas (`tools` definition)<br>• Iteration guards, state history, and convergence logic<br>• Live Azure AI integration (`gpt-5.4-nano`) |
| **Stage 3** | [`stage3_multi_agent_system.py`](stage3_multi_agent_system.py) | • Hierarchical Multi-Agent team orchestration<br>• Role specialization: Supervisor, Inventory Specialist, Safety Officer, Synthesizer<br>• FastMCP client integration over Streamable HTTP (Port 8000)<br>• Real PostgreSQL database grounding with Row-Level Security (RLS) |

---

## 🏃 Running the Stages

### Run Stage 1 (Single ReAct Loop):
```powershell
python stages/stage1_react_agent_scratch.py
```

### Run Stage 3 (Multi-Agent CLI Team):
```powershell
# Ensure FastMCP server is running on port 8000
python stages/stage3_multi_agent_system.py
```
