"""Verify role isolation, streamed synthesis, and its fallback without API calls."""

import asyncio
import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))

with patch("dotenv.load_dotenv"), patch.dict(os.environ, {
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-4.1-mini",
    "B2C_SYNTHESIZER_MODEL_DEPLOYMENT_NAME": "gpt-5-mini",
    "B2C_SYNTHESIZER_MAX_COMPLETION_TOKENS": "4096",
}), patch("shared.llm_config.get_azure_or_openai_client", return_value=MagicMock()):
    service = importlib.import_module("services.agent_service")


def completion(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class SynthesizerModelTests(unittest.TestCase):
    def run_pipeline(self, mode="stream", model="gpt-5-mini"):
        requests = []

        def create(**kwargs):
            requests.append(kwargs)
            if kwargs["messages"][0]["content"] == service.supervisor_module_prompt:
                return completion(json.dumps({"search_terms": ["Cordless Drill"], "task_description": "Mount a shelf"}))
            if kwargs.get("stream"):
                if mode == "failure":
                    raise RuntimeError("Simulated stream failure")
                if mode == "empty":
                    return iter([])
                return iter([chunk("Use a "), chunk("Cordless Drill. Check wall wiring.")])
            if kwargs["model"] == model and kwargs["messages"][0]["content"] == service.SYNTHESIZER_SYSTEM_PROMPT:
                return completion("" if mode == "empty" else "Use a Cordless Drill. Check wall wiring.")
            return completion("Check wall wiring and wear eye protection.")

        async def collect():
            return [json.loads(event.removeprefix("data: ")) async for event in service.multi_agent_stream("Mount a shelf")]

        from supervisor import SUPERVISOR_SYSTEM_PROMPT
        with patch.object(service, "supervisor_module_prompt", SUPERVISOR_SYSTEM_PROMPT, create=True), \
             patch.object(service.client.chat.completions, "create", side_effect=create), \
             patch.object(service.inventory_specialist, "query_inventory", new=AsyncMock(return_value='{"row_count": 1, "name": "Cordless Drill", "price": 29.99}')), \
             patch.object(service.asyncio, "sleep", new=AsyncMock()), \
             patch.object(service, "SYNTHESIZER_MODEL_NAME", model):
            events = asyncio.run(collect())
        return requests, events

    def test_only_synthesis_switches_model(self):
        requests, events = self.run_pipeline()
        self.assertEqual([request["model"] for request in requests], ["gpt-4.1-mini", "gpt-4.1-mini", "gpt-5-mini"])
        self.assertEqual(requests[-1]["max_completion_tokens"], 4096)
        self.assertEqual(requests[-1]["reasoning_effort"], "low")
        self.assertNotIn("reasoning_effort", requests[0])
        self.assertNotIn("max_tokens", requests[-1])
        self.assertIn("Use a Cordless Drill", "".join(event.get("content", "") for event in events))
        self.assertEqual(events[-1], {"done": True})
        self.assertFalse(any("error" in event for event in events))

    def test_stream_failure_keeps_synthesis_model_for_fallback(self):
        requests, events = self.run_pipeline("failure")
        self.assertEqual([request["model"] for request in requests[-2:]], ["gpt-5-mini", "gpt-5-mini"])
        self.assertEqual(requests[-1]["max_completion_tokens"], requests[-2]["max_completion_tokens"])
        self.assertFalse(any("error" in event for event in events))
        self.assertIn("Use a Cordless Drill", "".join(event.get("content", "") for event in events))

    def test_empty_stream_and_fallback_report_error(self):
        requests, events = self.run_pipeline("empty")
        self.assertEqual(len(requests), 4)
        self.assertTrue(any("empty response" in event.get("error", "") for event in events))
        self.assertEqual(events[-1], {"done": True})

    def test_model_override_supports_rollback(self):
        requests, events = self.run_pipeline(model="gpt-4.1-mini")
        self.assertEqual(requests[-1]["model"], "gpt-4.1-mini")
        self.assertIn("max_tokens", requests[-1])
        self.assertNotIn("max_completion_tokens", requests[-1])
        self.assertNotIn("reasoning_effort", requests[-1])
        self.assertFalse(any("error" in event for event in events))

    def test_health_reports_models_by_role(self):
        models = asyncio.run(service.health_check())["agent_models"]
        self.assertEqual(models["supervisor"], "gpt-4.1-mini")
        self.assertEqual(models["safety_officer"], "gpt-4.1-mini")
        self.assertEqual(models["synthesizer"], "gpt-5-mini")
        self.assertIsNone(models["inventory_specialist"])


if __name__ == "__main__":
    unittest.main()
