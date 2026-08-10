"""LangGraph AgentState definition and initial state builder."""

from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages

from config import settings


class AgentState(TypedDict):
    """LangGraph AgentState tracking conversation, permissions, retries, errors, and context."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    pending_permission: Optional[Dict[str, Any]]
    retry_count: int
    last_error: Optional[str]
    context: Dict[str, Any]


def create_initial_state(
    user_prompt: Optional[str] = None,
    mode: str = "coding",
    context_extra: Optional[Dict[str, Any]] = None,
) -> AgentState:
    """Create a default initial state for starting an agent turn.

    Args:
        user_prompt: Initial user input text, if provided.
        mode: Agent operational mode ('coding', 'general', 'self_correct').
        context_extra: Optional dictionary of additional context parameters.

    Returns:
        AgentState initialized dictionary.
    """
    messages: List[BaseMessage] = []
    if user_prompt:
        messages.append(HumanMessage(content=user_prompt))

    initial_context: Dict[str, Any] = {
        "mode": mode,
        "active_model": settings.primary_model,
        "workspace_path": str(settings.workspace_path),
        "max_retries": settings.max_retries,
    }
    if context_extra:
        initial_context.update(context_extra)

    return {
        "messages": messages,
        "pending_permission": None,
        "retry_count": 0,
        "last_error": None,
        "context": initial_context,
    }
