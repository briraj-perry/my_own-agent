import asyncio
import os
import re
from typing import AsyncGenerator, Dict, Any, Optional

from config import settings
from agent.base_agent import BaseAgent, AgentTask, AgentResponse, AgentArtifact, AgentName
from agent.claw import ClawAgentEngine
from agent.prompts import CLAW_NEXTJS_SYSTEM_PROMPT

try:
    from indexer import CodebaseIndexer
except ImportError:
    CodebaseIndexer = None


class ClawAgent(BaseAgent):
    name = AgentName.CLAW
    description = "Full-stack Next.js/React applications"
    
    def __init__(self):
        super().__init__()
        self.system_prompt = CLAW_NEXTJS_SYSTEM_PROMPT
        self.engine = ClawAgentEngine()
    
    async def execute(self, task: AgentTask) -> AgentResponse:
        content = ""
        artifacts = []
        error = None
        
        try:
            async for event in self.stream_execute(task):
                if event.get("type") == "token":
                    content += event.get("content", "")
                elif event.get("type") == "artifact":
                    artifact_data = event.get("artifact", {})
                    artifacts.append(
                        AgentArtifact(
                            artifact_type=artifact_data.get("artifact_type", "file"),
                            title=artifact_data.get("title", "File"),
                            content=artifact_data.get("content", ""),
                            file_path=artifact_data.get("file_path", ""),
                            metadata=artifact_data.get("metadata", {})
                        )
                    )
                elif event.get("type") == "state" and event.get("step") == "error":
                    error = event.get("status", "Unknown error")
        except Exception as e:
            error = str(e)
            
        return AgentResponse(
            agent_name=self.name.value,
            content=content,
            artifacts=artifacts,
            suggestions=["Run `npm install`", "Run `npm run dev`"] if not error else [],
            error=error
        )
    
    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        # Support multi-turn: detect if modifying existing project vs creating new
        prompt_lower = task.prompt.lower()
        is_update = any(kw in prompt_lower for kw in ["fix", "update", "modify", "add", "change", "error", "bug", "repair", "clean"])
        action_desc = "Updating existing" if is_update else "Creating new"
        
        # Support framework detection
        framework = "Next.js"
        if "vite" in prompt_lower:
            framework = "Vite"
        elif "react" in prompt_lower and "next" not in prompt_lower:
            framework = "React"
            
        # 1. Yield state event
        yield {
            "type": "state",
            "mascot_state": "claw",
            "status": f"⚡ Claw Agent initialized. {action_desc} {framework} application...",
            "step": "plan"
        }
        
        # Initialize indexer if available
        indexer = CodebaseIndexer() if CodebaseIndexer else None
        
        # 2. Delegate to self.engine.stream_nextjs_app_response()
        # 3. Yield all events from the engine
        # 4. Collect written files into artifacts
        async for event in self.engine.stream_nextjs_app_response(
            user_query=task.prompt,
            target_folder=task.target_folder,
            model_id=self.model,
            indexer=indexer
        ):
            yield event
            
            # If the engine logs a file write, intercept it and yield an artifact event
            if event.get("type") == "execution_log" and "write_file" in event.get("command", ""):
                match = re.search(r"write_file\('([^']+)'\)", event.get("command", ""))
                if match:
                    filename = match.group(1)
                    filepath = os.path.join(task.target_folder, filename)
                    try:
                        if os.path.exists(filepath):
                            with open(filepath, "r", encoding="utf-8") as f:
                                file_content = f.read()
                            
                            # Determine language for metadata
                            lang = "javascript"
                            if filename.endswith(".jsx"): lang = "jsx"
                            elif filename.endswith(".tsx"): lang = "tsx"
                            elif filename.endswith(".ts"): lang = "typescript"
                            elif filename.endswith(".css"): lang = "css"
                            elif filename.endswith(".json"): lang = "json"
                            
                            yield {
                                "type": "artifact",
                                "artifact": {
                                    "artifact_type": "file",
                                    "title": filename,
                                    "content": file_content,
                                    "file_path": filepath,
                                    "metadata": {"language": lang}
                                }
                            }
                    except Exception:
                        pass
