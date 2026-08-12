"""Unit tests for my_neo-agent core agent logic and graph structure."""

import os
import sys
import asyncio
from pathlib import Path

# Ensure root workspace directory is on sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from config import settings
from memory.checkpointer import SQLiteChatMemory, SQLiteCheckpointer, get_memory_checkpointer
from agent.state import AgentState, create_initial_state
from agent.prompts import get_system_prompt, CODING_SYSTEM_PROMPT
from agent.nodes import check_permission, execute_tools, self_correct_eval
from agent.graph import build_agent_graph, should_continue_after_model, route_permission_check, route_after_tool_execution
from agent.core import NeoAgentCore


class TestAgentCore(unittest.TestCase):
    """Test suite verifying agent state, prompts, nodes, memory checkpointer, and graph construction."""

    def test_config_settings(self):
        """Test configuration defaults and directory creation."""
        self.assertEqual(settings.ollama_base_url, "http://localhost:11434")
        self.assertEqual(settings.primary_model, "qwen2.5-coder:14b")
        self.assertIn("qwen2.5-coder:7b", settings.fallback_models)
        self.assertTrue(settings.data_dir.exists())

    def test_initial_state_creation(self):
        """Test AgentState initialization function."""
        state = create_initial_state("Hello, help me code!", mode="coding")
        self.assertEqual(len(state["messages"]), 1)
        self.assertIsInstance(state["messages"][0], HumanMessage)
        self.assertEqual(state["messages"][0].content, "Hello, help me code!")
        self.assertEqual(state["retry_count"], 0)
        self.assertIsNone(state["last_error"])
        self.assertIsNone(state["pending_permission"])
        self.assertEqual(state["context"]["mode"], "coding")

    def test_system_prompt_builder(self):
        """Test system prompt selection."""
        prompt = get_system_prompt("coding")
        self.assertIn("advanced local AI Coding Agent", prompt)

        gen_prompt = get_system_prompt("general")
        self.assertIn("highly knowledgeable local AI assistant", gen_prompt)

    def test_permission_check_node(self):
        """Test check_permission node requiring approval for destructive tools."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "execute_command", "args": {"cmd": "dir"}, "id": "call_123"}
            ],
        )
        state: AgentState = {
            "messages": [ai_msg],
            "pending_permission": None,
            "retry_count": 0,
            "last_error": None,
            "context": {},
        }
        res = check_permission(state)
        self.assertIsNotNone(res["pending_permission"])
        self.assertEqual(res["pending_permission"]["tool"], "execute_command")

    def test_execute_tools_node(self):
        """Test execute_tools node invoking functions from tools_map."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {"name": "add_numbers", "args": {"a": 5, "b": 10}, "id": "call_456"}
            ],
        )
        state: AgentState = {
            "messages": [ai_msg],
            "pending_permission": None,
            "retry_count": 0,
            "last_error": None,
            "context": {},
        }

        def dummy_add(a, b):
            return a + b

        config = {"configurable": {"tools_map": {"add_numbers": dummy_add}}}
        res = execute_tools(state, config=config)

        self.assertIsNone(res["last_error"])
        self.assertEqual(len(res["messages"]), 1)
        self.assertIsInstance(res["messages"][0], ToolMessage)
        self.assertEqual(res["messages"][0].content, "15")

    def test_self_correct_eval_node(self):
        """Test self-correction evaluation node incrementing retry count."""
        state: AgentState = {
            "messages": [],
            "pending_permission": None,
            "retry_count": 0,
            "last_error": "SyntaxError: invalid syntax at line 5",
            "context": {"mode": "coding"},
        }
        res = self_correct_eval(state)
        self.assertEqual(res["retry_count"], 1)
        self.assertEqual(res["context"]["mode"], "self_correct")
        self.assertEqual(len(res["messages"]), 1)
        self.assertIn("Attempt 1", res["messages"][0].content)

    def test_graph_routing_rules(self):
        """Test conditional graph routing functions."""
        # 1. Test model response with tool call
        msg_with_tool = AIMessage(
            content="",
            tool_calls=[{"name": "read_file", "args": {}, "id": "1"}],
        )
        state1: AgentState = {
            "messages": [msg_with_tool],
            "pending_permission": None,
            "retry_count": 0,
            "last_error": None,
            "context": {},
        }
        self.assertEqual(should_continue_after_model(state1), "check_permission")

        # 2. Test permission check route
        state_pending: AgentState = {
            "messages": [],
            "pending_permission": {"status": "awaiting_approval", "approved": False},
            "retry_count": 0,
            "last_error": None,
            "context": {},
        }
        self.assertEqual(route_permission_check(state_pending), "__end__")

        # 3. Test tool execution route on error
        state_err: AgentState = {
            "messages": [],
            "pending_permission": None,
            "retry_count": 1,
            "last_error": "Error running code",
            "context": {},
        }
        self.assertEqual(route_after_tool_execution(state_err), "self_correct_eval")

    def test_sqlite_chat_memory(self):
        """Test SQLite chat memory read/write."""
        db_path = settings.data_dir / "test_chat.db"
        memory = SQLiteChatMemory(db_path=db_path)
        thread_id = "test_thread_1"

        memory.save_message(thread_id, "user", "Hello world")
        memory.save_message(thread_id, "assistant", "Hi there!")

        history = memory.get_messages(thread_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello world")
        self.assertEqual(history[1]["role"], "assistant")

        memory.clear_history(thread_id)
        self.assertEqual(len(memory.get_messages(thread_id)), 0)

        if db_path.exists():
            db_path.unlink()

    def test_build_agent_graph(self):
        """Test agent graph building with in-memory checkpointer."""
        checkpointer = get_memory_checkpointer()
        graph = build_agent_graph(checkpointer=checkpointer)
        self.assertIsNotNone(graph)

    def test_coordinated_team_dependency_order_and_offline_safety(self):
        """Large-task specialists expose dependencies and do not write when Ollama is offline."""
        core = NeoAgentCore()
        team = core._build_coordinated_team("Build a complete web application")
        self.assertEqual(
            [(agent.id, agent.dependencies) for agent in team],
            [
                ("architecture", []),
                ("interface", ["architecture"]),
                ("implementation", ["architecture", "interface"]),
                ("quality", ["interface", "implementation"]),
            ],
        )

        core.is_ollama_running = lambda: False

        async def collect_events():
            return [
                event async for event in core._run_coordinated_team(
                    "Build a complete web application", ".", "test-model"
                )
            ]

        events = asyncio.run(collect_events())
        self.assertEqual(events[0]["type"], "coordination_update")
        updates = [event for event in events if event["type"] == "sub_agent_update"]
        self.assertEqual(len(updates), 4)
        self.assertTrue(all(event["sub_agent"]["status"] == "failed" for event in updates))


if __name__ == "__main__":
    unittest.main()
