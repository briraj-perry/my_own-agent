"""Automated integration test suite for Neo Mascot Companion Studio multi-agent system.

Verifies:
1. Base infrastructure (BaseAgent, AgentTask, AgentResponse, AgentArtifact)
2. MasterOrchestrator routing (explicit directives, keyword fallback)
3. Specialized Agents (Neo, Claw, Eagle, Herald)
4. Tool additions (DocumentTools, SlideBuilder, VisionDebugger)
5. FastAPI Server endpoints & responses
"""

import os
import sys
import json
import asyncio
from fastapi.testclient import TestClient

from agent.base_agent import AgentTask, AgentResponse, AgentArtifact, AgentName, BaseAgent
from agent.orchestrator import MasterOrchestrator
from agent.neo_agent import NeoAgent
from agent.claw_agent import ClawAgent
from agent.eagle_agent import EagleAgent
from agent.herald_agent import HeraldAgent
from tools.document_tools import detect_document_type
from tools.slide_builder import SlideBuilder
from tools.vision_debugger import VisionDebugger, DebugCard
from server import app


def test_base_agent_classes():
    """Verify data classes and enums."""
    task = AgentTask(prompt="Test prompt", target_folder=".")
    assert task.prompt == "Test prompt"
    assert task.target_folder == "."

    artifact = AgentArtifact(
        artifact_type="file",
        title="index.html",
        content="<html><body>Hello</body></html>",
        file_path="index.html"
    )
    art_dict = artifact.to_dict()
    assert art_dict["artifact_type"] == "file"
    assert art_dict["title"] == "index.html"

    resp = AgentResponse(agent_name="neo", content="Done!", artifacts=[artifact])
    resp_dict = resp.to_dict()
    assert resp_dict["agent_name"] == "neo"
    assert len(resp_dict["artifacts"]) == 1


def test_orchestrator_initialization_and_properties():
    """Verify orchestrator properties and backward compatibility."""
    orch = MasterOrchestrator()
    assert orch.active_model is not None
    assert isinstance(orch.get_available_models(), list)
    assert len(orch.get_sub_agents_data()) == 4


def test_orchestrator_routing():
    """Verify routing mechanisms."""
    orch = MasterOrchestrator()

    async def run():
        # Directive routing
        _, task_claw, info_claw = await orch.route("[AGENT:CLAW] Build a Next.js app")
        assert info_claw["target_agent"] == "claw"
        assert task_claw.prompt == "Build a Next.js app"

        _, task_eagle, info_eagle = await orch.route("@eagle Check this code for bugs")
        assert info_eagle["target_agent"] == "eagle"

        _, task_herald, info_herald = await orch.route("[AGENT:HERALD] Create 10 slides on physics")
        assert info_herald["target_agent"] == "herald"

        # Keyword routing fallback
        _, _, kw_herald = await orch.route("Create a presentation about Space Exploration")
        assert kw_herald["target_agent"] == "herald"

        _, _, kw_eagle = await orch.route("Analyze and debug my script error")
        assert kw_eagle["target_agent"] == "eagle"

    asyncio.run(run())


def test_slide_builder():
    """Verify Reveal.js presentation generation."""
    builder = SlideBuilder()
    sample_deck = {
        "title": "Unit Test Presentation",
        "subtitle": "Testing slide builder engine",
        "theme": "modern-dark",
        "slides": [
            {"type": "title", "title": "Unit Test Presentation", "subtitle": "Automated verification"},
            {"type": "content", "title": "Key Features", "bullets": ["Multi-agent routing", "Slide builder", "Vision debug"]},
            {"type": "code", "title": "Python Snippet", "code": "def hello(): print('world')", "language": "python"}
        ]
    }
    out_dir = "data/presentations"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "test_output.html")
    res = builder.build_revealjs(sample_deck, out_path)
    assert res.get("status") == "success"
    assert os.path.exists(out_path)


def test_debug_card_formatting():
    """Verify DebugCard Markdown generation."""
    card = DebugCard(
        bug_title="IndexError: list index out of range",
        severity="🔴 Critical",
        what_happened="Attempted to access list element beyond its length.",
        why_it_happened="In Python lists are 0-indexed and bounded by len(list).",
        code_before="item = my_list[10]",
        code_after="if len(my_list) > 10:\n    item = my_list[10]",
        pro_tip="Always check list boundaries or use try-except IndexError.",
        related_concepts=["Lists", "Indexing", "Bounds Checking"]
    )
    md = card.to_markdown()
    assert "IndexError" in md
    assert "Critical" in md
    assert "Pro Tip" in md


def test_server_rest_api():
    """Verify FastAPI endpoints."""
    client = TestClient(app)

    # /api/status
    r_status = client.get("/api/status")
    assert r_status.status_code == 200
    assert r_status.json().get("agent") == "my_neo-agent"

    # /api/agents
    r_agents = client.get("/api/agents")
    assert r_agents.status_code == 200
    agents = r_agents.json().get("agents", [])
    assert len(agents) == 4
    agent_names = [a["name"] for a in agents]
    assert "neo" in agent_names
    assert "claw" in agent_names
    assert "eagle" in agent_names
    assert "herald" in agent_names

def test_eagle_agent_handling():
    """Verify Eagle Agent handles diverse prompts without premature rejection."""
    eagle = EagleAgent()

    # 1. General concept question
    t1 = AgentTask(prompt="Explain how to prevent SQL injection in web apps")
    ctx1 = eagle._build_analysis_context(t1)
    p1 = eagle._assemble_prompt(t1, ctx1)
    assert "SQL injection" in p1

    # 2. Workspace review request
    t2 = AgentTask(prompt="Review my workspace files for potential bugs", target_folder=".")
    ctx2 = eagle._build_analysis_context(t2)
    assert ctx2["workspace_summary"] != ""

    # 3. Direct code snippet with backticks
    t3 = AgentTask(prompt="Fix this:\n```python\nprint('hello world')\n```")
    ctx3 = eagle._build_analysis_context(t3)
    assert len(ctx3["code_snippets"]) == 1
    assert ctx3["code_snippets"][0]["language"] == "python"


if __name__ == "__main__":
    print("Running integration tests...")
    test_base_agent_classes()
    print("  [PASS] Base agent classes.")
    test_orchestrator_initialization_and_properties()
    print("  [PASS] Orchestrator initialization & properties.")
    test_orchestrator_routing()
    print("  [PASS] Orchestrator routing.")
    test_eagle_agent_handling()
    print("  [PASS] Eagle agent handling & context building.")
    test_slide_builder()
    print("  [PASS] Slide builder.")
    test_debug_card_formatting()
    print("  [PASS] DebugCard formatting.")
    test_server_rest_api()
    print("  [PASS] Server REST API.")
    print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")


