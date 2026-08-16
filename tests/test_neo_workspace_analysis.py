"""Unit tests for Neo Agent dynamic workspace directory analysis and code preservation."""

import os
import sys
import unittest
import tempfile
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.neo_agent import NeoAgent
from agent.base_agent import AgentTask
from tools import file_tools


class TestNeoWorkspaceAnalysis(unittest.TestCase):
    """Test suite verifying dynamic workspace directory analysis and context preservation in NeoAgent."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.temp_dir.name
        self.agent = NeoAgent()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dynamic_directory_analysis_empty_folder(self):
        """Test directory scanning on an empty folder."""
        files = file_tools.get_folder_code_files(self.workspace)
        self.assertEqual(len(files), 0)

    def test_dynamic_directory_analysis_with_existing_game(self):
        """Test directory scanning dynamically discovers existing game files without hardcoding."""
        game_code = """import pygame
import random

WIDTH, HEIGHT = 600, 600
class SnakeGame:
    def __init__(self):
        self.score = 0
"""
        file_tools.write_file("custom_snake_game.py", game_code, folder=self.workspace)
        
        files = file_tools.get_folder_code_files(self.workspace)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["rel_path"], "custom_snake_game.py")
        self.assertTrue(files[0]["is_python"])

    def test_stream_execute_analyzes_directory_events(self):
        """Test that stream_execute emits directory analysis events before implementation."""
        # Create a sample project in the temporary workspace
        sample_code = """# Game loop\nscore = 0\nprint('Score:', score)\n"""
        file_tools.write_file("arcade_game.py", sample_code, folder=self.workspace)

        task = AgentTask(
            prompt="add high score tracking to arcade_game.py",
            target_folder=self.workspace,
            images=[]
        )

        async def collect_analysis_events():
            events = []
            # We mock the LLM streaming to test the analysis phase
            async def mock_stream(messages, model=None, images=None):
                yield "```python\n# Updated code with high score\nscore = 0\nhigh_score = 100\n```"

            self.agent._stream_ollama_tokens = mock_stream

            async for event in self.agent.stream_execute(task):
                events.append(event)
            return events

        events = asyncio.run(collect_analysis_events())
        
        # Verify directory analysis event was emitted
        exec_logs = [e for e in events if e.get("type") == "execution_log"]
        analysis_logs = [e for e in exec_logs if "analyze_directory" in e.get("command", "")]
        self.assertTrue(len(analysis_logs) > 0, "Expected analyze_directory execution_log event")
        self.assertIn("arcade_game.py", analysis_logs[0].get("output", ""))

        # Verify state event for analysis was emitted
        state_events = [e for e in events if e.get("type") == "state" and e.get("step") == "analyze"]
        self.assertTrue(len(state_events) > 0, "Expected state event with step='analyze'")

        # Verify updated file was written
        updated_content = file_tools.read_file("arcade_game.py", folder=self.workspace)
        self.assertEqual(updated_content.get("status"), "success")
        self.assertIn("high_score", updated_content.get("content", ""))


if __name__ == "__main__":
    unittest.main()
