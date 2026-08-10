"""StateGraph definition linking nodes with conditional edges and SQLite MemorySaver checkpointer integration."""

import logging
from typing import Any, Dict, Literal, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import AIMessage

from config import settings
from agent.state import AgentState
from agent.nodes import call_model, check_permission, execute_tools, self_correct_eval
from memory.checkpointer import get_sqlite_checkpointer, get_memory_checkpointer

logger = logging.getLogger(__name__)


def should_continue_after_model(state: AgentState) -> Literal["check_permission", "__end__"]:
    """Conditional edge after call_model: routes to permission check if tools requested, else END."""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None)

    if tool_calls and len(tool_calls) > 0:
        return "check_permission"

    return END


def route_permission_check(
    state: AgentState,
) -> Literal["execute_tools", "__end__"]:
    """Conditional edge after check_permission: pauses at END if approval pending, else proceeds to execute_tools."""
    pending = state.get("pending_permission")

    if pending and pending.get("status") == "awaiting_approval" and not pending.get("approved"):
        logger.info("Execution paused: waiting for user permission approval.")
        return END

    return "execute_tools"


def route_after_tool_execution(
    state: AgentState,
) -> Literal["self_correct_eval", "call_model", "__end__"]:
    """Conditional edge after execute_tools: triggers self-correction if error occurred, or calls model."""
    last_error = state.get("last_error")
    retry_count = state.get("retry_count", 0)

    if last_error:
        if retry_count < settings.max_retries:
            logger.info(
                f"Error detected in tool execution. Initiating self-correction (Retry {retry_count + 1}/{settings.max_retries})"
            )
            return "self_correct_eval"
        else:
            logger.warning(
                f"Max retries ({settings.max_retries}) reached. Stopping self-correction loop."
            )
            return END

    return "call_model"


def build_agent_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    use_sqlite_checkpoint: bool = True,
) -> Any:
    """Builds and compiles the LangGraph StateGraph for my_neo-agent.

    Args:
        checkpointer: Custom checkpointer instance (SQLite or Memory).
        use_sqlite_checkpoint: If True and no checkpointer provided, defaults to SQLite checkpointer.

    Returns:
        Compiled LangGraph executable graph app.
    """
    workflow = StateGraph(AgentState)

    # Add core nodes
    workflow.add_node("call_model", call_model)
    workflow.add_node("check_permission", check_permission)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("self_correct_eval", self_correct_eval)

    # Set entry point
    workflow.add_edge(START, "call_model")

    # Add conditional edges
    workflow.add_conditional_edges(
        "call_model",
        should_continue_after_model,
        {
            "check_permission": "check_permission",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "check_permission",
        route_permission_check,
        {
            "execute_tools": "execute_tools",
            END: END,
        },
    )

    workflow.add_conditional_edges(
        "execute_tools",
        route_after_tool_execution,
        {
            "self_correct_eval": "self_correct_eval",
            "call_model": "call_model",
            END: END,
        },
    )

    # After self_correct_eval, always route back to call_model with reflection prompt
    workflow.add_edge("self_correct_eval", "call_model")

    # Resolve checkpointer
    if checkpointer is None:
        if use_sqlite_checkpoint:
            checkpointer = get_sqlite_checkpointer()
        else:
            checkpointer = get_memory_checkpointer()

    app = workflow.compile(checkpointer=checkpointer)
    return app


def create_agent(checkpointer: Optional[BaseCheckpointSaver] = None) -> Any:
    """Convenience alias to build and return compiled agent."""
    return build_agent_graph(checkpointer=checkpointer)


# Compiled default agent instance
app = build_agent_graph()
