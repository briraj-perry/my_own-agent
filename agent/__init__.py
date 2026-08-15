"""Agent package initialization.

Exports all agent classes, base infrastructure, and shared utilities
for the Neo Companion Studio multi-agent system.
"""

# Existing exports (backward compatibility)
from .state import AgentState, create_initial_state
from .prompts import (
    get_system_prompt,
    CODING_SYSTEM_PROMPT,
    GENERAL_SYSTEM_PROMPT,
    SELF_CORRECTION_SYSTEM_PROMPT,
    WEB_APP_SYSTEM_PROMPT,
    CLAW_NEXTJS_SYSTEM_PROMPT,
    ORCHESTRATOR_ROUTING_PROMPT,
    EAGLE_SYSTEM_PROMPT,
    HERALD_SYSTEM_PROMPT,
)
from .nodes import call_model, check_permission, execute_tools, self_correct_eval
from .graph import build_agent_graph, create_agent
from .core import NeoAgentCore

# New multi-agent system exports
from .base_agent import BaseAgent, AgentTask, AgentResponse, AgentArtifact, AgentName
from .orchestrator import MasterOrchestrator
from .neo_agent import NeoAgent
from .claw_agent import ClawAgent
from .eagle_agent import EagleAgent
from .herald_agent import HeraldAgent
from .planner import ExecutionPlanner

# Legacy compatibility
from .claw import ClawAgentEngine

__all__ = [
    # Base infrastructure
    "BaseAgent",
    "AgentTask",
    "AgentResponse",
    "AgentArtifact",
    "AgentName",
    # Multi-agent system
    "MasterOrchestrator",
    "NeoAgent",
    "ClawAgent",
    "EagleAgent",
    "HeraldAgent",
    # Existing exports
    "AgentState",
    "create_initial_state",
    "get_system_prompt",
    "CODING_SYSTEM_PROMPT",
    "GENERAL_SYSTEM_PROMPT",
    "SELF_CORRECTION_SYSTEM_PROMPT",
    "WEB_APP_SYSTEM_PROMPT",
    "CLAW_NEXTJS_SYSTEM_PROMPT",
    "ORCHESTRATOR_ROUTING_PROMPT",
    "EAGLE_SYSTEM_PROMPT",
    "HERALD_SYSTEM_PROMPT",
    "call_model",
    "check_permission",
    "execute_tools",
    "self_correct_eval",
    "build_agent_graph",
    "create_agent",
    "NeoAgentCore",
    "ClawAgentEngine",
    "ExecutionPlanner",
]
