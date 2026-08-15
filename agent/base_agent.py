"""Base agent infrastructure for the Neo Companion multi-agent system.

Provides abstract base class, standardized data classes, and shared utilities
that all specialized agents (Neo, Claw, Eagle, Herald) inherit from.
"""

import asyncio
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, Any, Optional, List
from enum import Enum


class AgentName(str, Enum):
    """Identifiers for each specialized agent in the system."""
    ORCHESTRATOR = "orchestrator"
    NEO = "neo"
    CLAW = "claw"
    EAGLE = "eagle"
    HERALD = "herald"


@dataclass
class AgentTask:
    """Standardized input passed to any agent by the orchestrator.
    
    Attributes:
        prompt: The user's original message or the orchestrator's reformulated task.
        conversation_id: Unique ID for this conversation thread.
        context: Extra context injected by the orchestrator (task_type, complexity, etc.).
        files: Paths to files attached by the user (code, PDFs, PPTXs, etc.).
        images: Base64-encoded images or image file paths attached by the user.
        target_folder: The active workspace folder where output files should be written.
        chat_history: Previous messages in this conversation for multi-turn context.
    """
    prompt: str
    conversation_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    target_folder: str = "."
    chat_history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class AgentArtifact:
    """A structured output produced by an agent (file, debug card, slide deck, etc.).
    
    Attributes:
        artifact_type: Category of artifact — "file", "debug_card", "slide_deck",
                       "project_tree", "code_block", "analysis_report".
        title: Human-readable title for display in the UI.
        content: The actual content (file source, HTML, JSON string, etc.).
        file_path: Absolute or relative path where the artifact was saved on disk.
        metadata: Extra agent-specific metadata (language, slide_count, severity, etc.).
    """
    artifact_type: str
    title: str
    content: str
    file_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict for JSON/WebSocket transmission."""
        return {
            "artifact_type": self.artifact_type,
            "title": self.title,
            "content": self.content[:500] if len(self.content) > 500 else self.content,
            "file_path": self.file_path,
            "metadata": self.metadata,
        }


@dataclass
class AgentResponse:
    """Standardized output returned by any agent after execution.
    
    Attributes:
        agent_name: Which agent produced this response.
        content: Main text/markdown response to display in the chat.
        artifacts: List of structured outputs (files, cards, decks, etc.).
        suggestions: Follow-up suggestions for the student.
        error: Error message if execution failed, None otherwise.
    """
    agent_name: str
    content: str
    artifacts: List[AgentArtifact] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dict for JSON/WebSocket transmission."""
        return {
            "agent_name": self.agent_name,
            "content": self.content,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "suggestions": self.suggestions,
            "error": self.error,
        }


class BaseAgent(ABC):
    """Abstract base class for all Neo Companion agents.
    
    Every specialized agent (Neo, Claw, Eagle, Herald) inherits from this
    and implements execute() and stream_execute(). The shared _call_ollama()
    helper provides consistent LLM inference across all agents.
    
    Subclasses must set:
        - name: AgentName enum value
        - description: One-line description of what this agent does
        - system_prompt: The system prompt used for LLM calls
    """

    name: AgentName
    description: str
    system_prompt: str

    def __init__(self):
        # Import here to avoid circular imports at module level
        from config import settings
        self.settings = settings
        self.ollama_base_url = str(settings.ollama_base_url)
        self.model = settings.primary_model

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResponse:
        """Execute a task and return a complete response.
        
        Use this for non-streaming scenarios (e.g., orchestrator routing call,
        background analysis, or test harnesses).
        
        Args:
            task: Standardized AgentTask with prompt, files, images, etc.
            
        Returns:
            AgentResponse with content, artifacts, and suggestions.
        """
        ...

    @abstractmethod
    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream execution as WebSocket-compatible event dicts.
        
        This is the primary execution method used by the server and desktop mascot.
        Each yielded dict follows the existing WebSocket event protocol:
        
            {"type": "token", "content": "..."}           — Streamed text token
            {"type": "state", "mascot_state": "...", ...}  — Mascot state update
            {"type": "routing", "target_agent": "...", ...} — Orchestrator routing
            {"type": "artifact", "artifact": {...}}        — Structured output
            {"type": "execution_log", ...}                 — Execution log entry
            {"type": "sub_agent_spawn", ...}               — Sub-agent lifecycle
            {"type": "sub_agent_update", ...}
            {"type": "sub_agent_complete", ...}
            {"type": "plan_generated", ...}                — DAG execution plan
            {"type": "coordination_update", ...}
        
        Args:
            task: Standardized AgentTask.
            
        Yields:
            Event dicts compatible with the WebSocket protocol.
        """
        ...
        yield  # Make this a generator (pragma: no cover)

    def is_ollama_running(self) -> bool:
        """Check if the local Ollama service is accessible."""
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/api/version")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    async def _call_ollama(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int = 4096,
        images: Optional[List[str]] = None,
    ) -> Any:
        """Shared Ollama inference helper used by all agents.
        
        For non-streaming: returns the complete response dict.
        For streaming: returns the raw HTTP response object for line-by-line reading.
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."} dicts.
            model: Override the agent's default model. Defaults to self.model.
            stream: If True, returns raw response for streaming. If False, returns parsed dict.
            temperature: LLM temperature (lower = more deterministic).
            num_ctx: Context window size in tokens.
            num_predict: Max tokens to generate.
            images: Optional list of base64-encoded images for vision models.
            
        Returns:
            If stream=False: Parsed JSON response dict with message.content.
            If stream=True: Raw HTTP response object for line-by-line reading.
            
        Raises:
            ConnectionError: If Ollama is not running.
            TimeoutError: If the request times out.
        """
        loop = asyncio.get_running_loop()
        target_model = model or self.model

        # Inject images into the last user message if provided
        if images and messages:
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    msg["images"] = images
                    break

        payload = {
            "model": target_model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
            "stream": stream,
        }

        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        timeout = self.settings.timeout_seconds if hasattr(self.settings, 'timeout_seconds') else 120.0

        if stream:
            # Return raw response for streaming — caller reads line by line
            def open_stream():
                return urllib.request.urlopen(req, timeout=timeout)
            return await loop.run_in_executor(None, open_stream)
        else:
            # Non-streaming: read full response and parse JSON
            def call_sync():
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            return await loop.run_in_executor(None, call_sync)

    async def _stream_ollama_tokens(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int = 4096,
        images: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Convenience async generator that yields individual text tokens from Ollama streaming.
        
        Use this when you want to stream tokens one by one without managing the
        raw HTTP response manually.
        
        Yields:
            Individual text token strings.
        """
        loop = asyncio.get_running_loop()
        response = await self._call_ollama(
            messages=messages,
            model=model,
            stream=True,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict,
            images=images,
        )

        def read_line(res):
            return res.readline()

        while True:
            line = await loop.run_in_executor(None, read_line, response)
            if not line:
                break
            try:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

    async def _call_ollama_complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int = 4096,
    ) -> str:
        """Convenience method: call Ollama and return just the text content.
        
        Returns:
            The assistant's response text content as a string.
        """
        response = await self._call_ollama(
            messages=messages,
            model=model,
            stream=False,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict,
        )
        return response.get("message", {}).get("content", "").strip()
