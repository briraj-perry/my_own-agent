"""LangGraph nodes for LLM inference (with fallback), permission checks, tool execution, and self-correction."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama

from config import settings
from agent.state import AgentState
from agent.prompts import get_system_prompt, SELF_CORRECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _invoke_llm_with_fallback(
    messages: List[BaseMessage],
    system_prompt: str,
    active_model: str,
    tools: Optional[List[Any]] = None,
) -> Tuple[BaseMessage, str]:
    """Attempts LLM inference using active model with fallback to secondary models."""
    full_messages = [SystemMessage(content=system_prompt)] + list(messages)

    models_to_try = [active_model] + [
        m for m in settings.model_chain if m != active_model
    ]
    last_exc = None

    for model_name in models_to_try:
        try:
            logger.info(
                f"Calling Ollama model '{model_name}' at {settings.ollama_base_url}"
            )
            llm = ChatOllama(
                base_url=settings.ollama_base_url,
                model=model_name,
                temperature=settings.temperature,
                timeout=settings.timeout_seconds,
            )
            if tools:
                llm = llm.bind_tools(tools)

            response = llm.invoke(full_messages)
            return response, model_name
        except Exception as exc:
            logger.warning(
                f"Failed to call model '{model_name}': {exc}. Trying fallback..."
            )
            last_exc = exc

    # If all models fail, create a fallback AIMessage describing the failure
    error_msg = f"All LLM model calls failed. Last error: {last_exc}"
    logger.error(error_msg)
    return AIMessage(content=f"Error: Unable to reach Ollama server or models. Details: {last_exc}"), active_model


def call_model(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Node: Invokes Ollama LLM using primary model with fallback support."""
    config = config or {}
    context = dict(state.get("context", {}))
    mode = context.get("mode", "coding")
    active_model = context.get("active_model", settings.primary_model)
    messages = list(state.get("messages", []))

    # Retrieve registered tools from configurable if provided
    tools = config.get("configurable", {}).get("tools", None)

    system_prompt = get_system_prompt(agent_mode=mode, context=context)

    response_msg, used_model = _invoke_llm_with_fallback(
        messages=messages,
        system_prompt=system_prompt,
        active_model=active_model,
        tools=tools,
    )

    context["active_model"] = used_model

    return {
        "messages": [response_msg],
        "context": context,
    }


def check_permission(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Node: Checks if pending tool calls require user permission prior to execution."""
    messages = state.get("messages", [])
    if not messages:
        return {"pending_permission": None}

    last_message = messages[-1]
    if not isinstance(last_message, AIMessage) or not getattr(
        last_message, "tool_calls", None
    ):
        return {"pending_permission": None}

    tool_calls = last_message.tool_calls
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        if tool_name in settings.require_permission_tools:
            # Check if permission was already granted in state
            existing_permission = state.get("pending_permission")
            if existing_permission and existing_permission.get("approved"):
                continue

            permission_request = {
                "tool": tool_name,
                "args": tool_call.get("args", {}),
                "tool_call_id": tool_call.get("id"),
                "approved": False,
                "status": "awaiting_approval",
            }
            logger.info(
                f"Permission required for tool '{tool_name}' (Call ID: {tool_call.get('id')})"
            )
            return {"pending_permission": permission_request}

    return {"pending_permission": None}


def execute_tools(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Node: Executes requested tool calls, handling errors and setting last_error if failed."""
    config = config or {}
    messages = state.get("messages", [])
    if not messages:
        return {"last_error": None}

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    if not tool_calls:
        return {"last_error": None}

    # Extract tool implementations from config
    tools_map: Dict[str, Any] = config.get("configurable", {}).get(
        "tools_map", {}
    )

    tool_outputs: List[BaseMessage] = []
    last_error: Optional[str] = None

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id", "unknown_id")

        tool_func = tools_map.get(tool_name)
        if not tool_func:
            err_text = f"Tool '{tool_name}' is not registered in tools_map."
            logger.error(err_text)
            last_error = err_text
            tool_outputs.append(
                ToolMessage(
                    content=f"Error: {err_text}", tool_call_id=tool_call_id
                )
            )
            continue

        try:
            logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
            if hasattr(tool_func, "invoke"):
                result = tool_func.invoke(tool_args)
            elif callable(tool_func):
                result = tool_func(**tool_args)
            else:
                result = str(tool_func)

            tool_outputs.append(
                ToolMessage(content=str(result), tool_call_id=tool_call_id)
            )
        except Exception as exc:
            err_msg = f"Execution of tool '{tool_name}' failed with error: {exc}"
            logger.exception(err_msg)
            last_error = err_msg
            tool_outputs.append(
                ToolMessage(content=f"Error: {err_msg}", tool_call_id=tool_call_id)
            )

    return {
        "messages": tool_outputs,
        "last_error": last_error,
    }


def self_correct_eval(
    state: AgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Node: Evaluates tool execution failure, formulates reflection feedback, and increments retry count."""
    retry_count = state.get("retry_count", 0) + 1
    last_error = state.get("last_error", "Unknown error encountered.")
    context = dict(state.get("context", {}))
    context["mode"] = "self_correct"

    reflection_content = (
        f"[SYSTEM SELF-CORRECTION NOTICE - Attempt {retry_count}/{settings.max_retries}]\n"
        f"The previous action encountered an error:\n{last_error}\n\n"
        f"Please reflect on this error, correct the parameters or logic, and retry."
    )

    reflection_msg = HumanMessage(content=reflection_content)

    logger.info(f"Self-correction loop triggered (Attempt {retry_count}): {last_error}")

    return {
        "messages": [reflection_msg],
        "retry_count": retry_count,
        "context": context,
    }
