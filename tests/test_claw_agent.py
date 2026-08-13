"""Unit tests for Claw Agent (Next.js Architect) and Framework Selection Routing."""

import sys
import asyncio
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.claw import ClawAgentEngine
from agent.prompts import get_system_prompt, CLAW_NEXTJS_SYSTEM_PROMPT
from agent.core import NeoAgentCore, is_app_building_intent


class TestClawAgent(unittest.TestCase):
    """Test suite verifying Claw Agent prompt builder, app intent detection, and framework selection resolution."""

    def test_app_building_intent_detection(self):
        """Test detection of app creation requests."""
        self.assertTrue(is_app_building_intent("make a todo app"))
        self.assertTrue(is_app_building_intent("build a dashboard app"))
        self.assertTrue(is_app_building_intent("create a website for my portfolio"))
        self.assertTrue(is_app_building_intent("develop a weather web app"))
        self.assertFalse(is_app_building_intent("explain how recursion works in python"))
        self.assertFalse(is_app_building_intent("what is the capital of France?"))

    def test_claw_system_prompt(self):
        """Test system prompt for Claw Agent mode."""
        prompt = get_system_prompt("claw")
        self.assertIn("Claw, an elite Next.js & React Full-Stack Application Architect Agent", prompt)
        self.assertIn("package.json", prompt)
        self.assertIn("app/page.jsx", prompt)
        self.assertIn("app/layout.jsx", prompt)

        prompt_nextjs = get_system_prompt("nextjs")
        self.assertEqual(prompt, prompt_nextjs)

    def test_claw_agent_engine_initialization(self):
        """Test ClawAgentEngine setup."""
        claw = ClawAgentEngine()
        self.assertEqual(claw.agent_name, "claw")
        self.assertEqual(claw.agent_role, "Next.js App Specialist")
        self.assertEqual(claw.mascot_state, "claw")

    def test_resolve_framework_selection(self):
        """Test framework choice resolution in NeoAgentCore."""
        agent = NeoAgentCore()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        req_id = "test-fw-123"
        fut = loop.create_future()
        agent.pending_framework_selections[req_id] = fut

        resolved = agent.resolve_framework_selection(req_id, "nextjs")
        self.assertTrue(resolved)
        self.assertEqual(fut.result(), "nextjs")

        loop.close()


if __name__ == "__main__":
    unittest.main()
