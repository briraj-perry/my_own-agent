"""Unit tests for Eagle Agent — whole folder audit, repair sentinel, and app review specialist."""

import os
import sys
import unittest
from pathlib import Path

# Ensure root workspace directory is on sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.prompts import get_system_prompt, EAGLE_AGENT_SYSTEM_PROMPT, SUBAGENT_SYSTEM_PROMPTS
from agent.eagle import EagleAgentEngine, extract_eagle_fixes
from agent.core import NeoAgentCore


class TestEagleAgent(unittest.TestCase):
    """Test suite verifying Eagle Agent engine, prompts, and team DAG integration."""

    def test_eagle_prompt_registry(self):
        """Test that EAGLE_AGENT_SYSTEM_PROMPT is registered and accessible via get_system_prompt."""
        prompt = get_system_prompt("eagle")
        self.assertEqual(prompt, EAGLE_AGENT_SYSTEM_PROMPT)
        self.assertIn("Eagle Agent", prompt)
        self.assertIn("Chief Code Quality Sentinel", prompt)
        self.assertIn("### 🔍 Eagle Audit Findings", prompt)
        self.assertIn("### 🔧 What Was Fixed", prompt)
        self.assertIn("### 📱 Application Quality Review", prompt)
        self.assertIn("eagle", SUBAGENT_SYSTEM_PROMPTS)

    def test_extract_eagle_fixes(self):
        """Test extraction of ### FIX_FILE blocks."""
        sample_eagle_output = (
            "### 🔍 Eagle Audit Findings\n"
            "- Button ID 'submit-btn' was missing click listener in script.js\n\n"
            "### FIX_FILE: script.js\n"
            "```javascript\n"
            "document.addEventListener('DOMContentLoaded', () => {\n"
            "  const btn = document.getElementById('submit-btn');\n"
            "  btn.addEventListener('click', () => { console.log('Clicked'); });\n"
            "});\n"
            "```\n\n"
            "### FIX_FILE: style.css\n"
            "```css\n"
            "body { background: #0a0f1a; }\n"
            "```\n\n"
            "### 📱 Application Quality Review\n"
            "- Architecture: 100% Operational\n"
        )
        fixes = extract_eagle_fixes(sample_eagle_output)
        self.assertEqual(len(fixes), 2)
        self.assertIn("script.js", fixes)
        self.assertIn("style.css", fixes)
        self.assertIn("submit-btn", fixes["script.js"])
        self.assertIn("background: #0a0f1a", fixes["style.css"])

    def test_static_precheck_unhandled_buttons(self):
        """Test static pre-check identifies HTML button IDs without matching JS handlers."""
        engine = EagleAgentEngine()
        precheck = engine.perform_static_precheck(".")
        self.assertIsInstance(precheck, dict)
        self.assertIn("files_scanned", precheck)
        self.assertIn("detected_issues", precheck)

    def test_core_team_includes_eagle_agent(self):
        """Test that NeoAgentCore web application build pipeline delegates to Eagle Agent."""
        core = NeoAgentCore()
        team = core._build_coordinated_team("Build a complete Task Manager Web App with 3 pages")
        agent_ids = [a.id for a in team]
        self.assertIn("eagle", agent_ids)
        
        eagle_agent = next(a for a in team if a.id == "eagle")
        self.assertEqual(eagle_agent.name, "Eagle Agent")
        self.assertEqual(eagle_agent.badge_icon, "🦅")
        self.assertEqual(len(eagle_agent.sub_steps), 5)
        self.assertIn("interface", eagle_agent.dependencies)
        self.assertIn("implementation", eagle_agent.dependencies)

    def test_core_has_eagle_engine_and_review_method(self):
        """Test that NeoAgentCore has initialized eagle_engine and analyze_and_review_with_eagle method."""
        core = NeoAgentCore()
        self.assertTrue(hasattr(core, "eagle_engine"))
        self.assertIsInstance(core.eagle_engine, EagleAgentEngine)
        self.assertTrue(hasattr(core, "analyze_and_review_with_eagle"))
        self.assertTrue(callable(core.analyze_and_review_with_eagle))


if __name__ == "__main__":
    unittest.main()
