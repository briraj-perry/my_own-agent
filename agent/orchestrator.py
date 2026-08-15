import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Tuple, Optional, List

from agent.base_agent import BaseAgent, AgentName, AgentTask, AgentResponse
from agent.prompts import ORCHESTRATOR_ROUTING_PROMPT
from config import settings

logger = logging.getLogger(__name__)

class MasterOrchestrator(BaseAgent):
    """Analyzes incoming prompts and routes to the correct specialized agent."""
    
    name = AgentName.ORCHESTRATOR
    description = "Routes tasks to the appropriate specialized agent."
    system_prompt = ORCHESTRATOR_ROUTING_PROMPT

    def __init__(self):
        super().__init__()
        self.agents = {}
        self.active_sub_agents = {}

    @property
    def active_model(self) -> str:
        return self.model

    @active_model.setter
    def active_model(self, val: str):
        self.set_model(val)
        
    def _get_agent(self, agent_name) -> BaseAgent:
        """Lazily load agents to avoid circular imports."""
        agent_name = str(agent_name).lower().replace("agentname.", "")
        if agent_name not in self.agents:
            if agent_name == "neo":
                try:
                    from agent.neo_agent import NeoAgent
                    self.agents["neo"] = NeoAgent()
                except Exception:
                    pass
            elif agent_name == "claw":
                try:
                    from agent.claw_agent import ClawAgent
                    self.agents["claw"] = ClawAgent()
                except Exception:
                    pass
            elif agent_name == "eagle":
                try:
                    from agent.eagle_agent import EagleAgent
                    self.agents["eagle"] = EagleAgent()
                except Exception:
                    pass
            elif agent_name == "herald":
                try:
                    from agent.herald_agent import HeraldAgent
                    self.agents["herald"] = HeraldAgent()
                except Exception:
                    pass
            else:
                # Default fallback: try to load Neo
                try:
                    from agent.neo_agent import NeoAgent
                    self.agents["neo"] = NeoAgent()
                except Exception:
                    pass
                    
        return self.agents.get(agent_name, self.agents.get("neo"))

    async def route(self, prompt: str, files: list = None, images: list = None) -> Tuple[BaseAgent, AgentTask, Dict[str, Any]]:
        """Single LLM call to determine which agent handles this request.
        Returns (target_agent_instance, AgentTask, routing_info_dict)"""
        files = files or []
        images = images or []
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        routing_info_dict = {
            "target_agent": "neo",
            "reasoning": "Fallback routing.",
            "task_context": {
                "task_type": "general",
                "complexity": "simple"
            }
        }
        
        prompt_clean = prompt
        # Check for explicit directive tag e.g. [AGENT:CLAW] or @claw
        explicit_agent = None
        for ag_name in ["neo", "claw", "eagle", "herald"]:
            prefix_tag = f"[agent:{ag_name}]"
            at_tag = f"@{ag_name}"
            if prompt.lower().startswith(prefix_tag):
                explicit_agent = ag_name
                prompt_clean = prompt[len(prefix_tag):].strip()
                break
            elif prompt.lower().startswith(at_tag):
                explicit_agent = ag_name
                prompt_clean = prompt[len(at_tag):].strip()
                break

        if explicit_agent:
            routing_info_dict = {
                "target_agent": explicit_agent,
                "reasoning": f"Direct request for {explicit_agent.upper()} specialist.",
                "task_context": {"task_type": explicit_agent, "complexity": "standard"}
            }
        else:
            try:
                response_text = await self._call_ollama_complete(
                    messages=messages,
                    temperature=0.1,
                    num_ctx=2048,
                    num_predict=512
                )
                
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}") + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    routing_info_dict.update(parsed)
                else:
                    raise ValueError("No JSON object found in response.")
                    
            except Exception as e:
                logger.warning(f"Routing LLM call failed or parsing failed: {e}. Falling back to keywords.")
                prompt_lower = prompt.lower()
                if any(kw in prompt_lower for kw in ["nextjs", "react", "full-stack", "dashboard", "next.js"]):
                    routing_info_dict["target_agent"] = "claw"
                    routing_info_dict["reasoning"] = "Keyword match for Next.js/React (Claw)."
                elif any(kw in prompt_lower for kw in ["analyze", "review", "bug", "fix", "debug", "pdf", "ppt", "spreadsheet", "excel", "screen"]) or images:
                    routing_info_dict["target_agent"] = "eagle"
                    routing_info_dict["reasoning"] = "Keyword match for Analysis & Debugging (Eagle)."
                elif any(kw in prompt_lower for kw in ["presentation", "slides", "powerpoint", "reveal", "pptx", "slide deck"]):
                    routing_info_dict["target_agent"] = "herald"
                    routing_info_dict["reasoning"] = "Keyword match for Presentations (Herald)."
                else:
                    routing_info_dict["target_agent"] = "neo"
                    routing_info_dict["reasoning"] = "General coding & web request (Neo)."

                
        target_agent_name = routing_info_dict.get("target_agent", "neo").lower()
        if target_agent_name not in ["neo", "claw", "eagle", "herald"]:
            target_agent_name = "neo"
            
        target_agent_instance = self._get_agent(target_agent_name)
        
        if not target_agent_instance:
            from agent.base_agent import BaseAgent # type: ignore
            # Fallback if no agent is importable
            target_agent_instance = BaseAgent() # type: ignore
            
        task = AgentTask(
            prompt=prompt_clean,
            files=files,
            images=images,
            context=routing_info_dict.get("task_context", {})
        )
        
        return target_agent_instance, task, routing_info_dict

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Route and execute (non-streaming)."""
        target_agent_instance, routed_task, routing_info_dict = await self.route(
            prompt=task.prompt, 
            files=task.files, 
            images=task.images
        )
        task.context.update(routed_task.context)
        return await target_agent_instance.execute(task)

    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[dict, None]:
        """Route and stream execute."""
        target_agent_instance, routed_task, routing_info_dict = await self.route(
            prompt=task.prompt, 
            files=task.files, 
            images=task.images
        )
        
        task.context.update(routed_task.context)
        
        yield {
            "type": "routing",
            "target_agent": routing_info_dict.get("target_agent", "neo"),
            "reasoning": routing_info_dict.get("reasoning", "")
        }
        
        async for event in target_agent_instance.stream_execute(task):
            yield event

    async def stream_response(self, user_query: str, images: list = None, target_folder: str = ".") -> AsyncGenerator[dict, None]:
        """Main entry point matching NeoAgentCore.stream_response() signature for backward compatibility.
        This is what server.py and desktop_mascot.py call."""
        task = AgentTask(
            prompt=user_query,
            images=images or [],
            target_folder=target_folder
        )
        async for event in self.stream_execute(task):
            yield event

    async def analyze_and_autofix_folder(self, folder_path: str = ".") -> Dict[str, Any]:
        """Delegates folder analysis to NeoAgentCore for backward compatibility."""
        try:
            from agent.core import NeoAgentCore
            core = NeoAgentCore()
            return await core.analyze_and_autofix_folder(folder_path)
        except Exception as e:
            return {"status": "error", "message": f"Folder analysis error: {str(e)}"}

    async def analyze_and_autofix_screen_and_folder(self, folder_path: str = ".") -> Dict[str, Any]:
        """Delegates screen+folder analysis to NeoAgentCore for backward compatibility."""
        try:
            from agent.core import NeoAgentCore
            core = NeoAgentCore()
            return await core.analyze_and_autofix_screen_and_folder(folder_path)
        except Exception as e:
            return {"status": "error", "message": f"Screen analysis error: {str(e)}"}

    def set_model(self, model_id: str) -> dict:
        """Set the active model for all agents."""
        self.model = model_id
        # Update model on all loaded agents
        for agent in self.agents.values():
            if hasattr(agent, 'model'):
                agent.model = model_id
        return {"status": "success", "selected_model": model_id, "message": f"Active model set to {model_id}"}

    def get_available_models(self) -> list:
        """Query Ollama for installed models."""
        import urllib.request
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get("models", [])
                return [{"id": m.get("name", ""), "name": f"{m.get('name', '')} (Ollama Local)", "provider": "Ollama"} for m in models]
        except Exception:
            return [
                {"id": "gemma4:31b-cloud", "name": "Gemma 4 31B Cloud", "provider": "Ollama"},
                {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B", "provider": "Ollama"},
            ]

    def get_sub_agents_data(self) -> list:
        """Return loaded sub-agents info."""
        return [
            {"name": "neo", "description": "Single-file HTML/CSS/JS web apps, Canvas games", "icon": "ðŸ¤–", "loaded": "neo" in self.agents},
            {"name": "claw", "description": "Full-stack Next.js/React applications", "icon": "âš¡", "loaded": "claw" in self.agents},
            {"name": "eagle", "description": "Code analysis, document parsing, vision debugging", "icon": "ðŸ¦…", "loaded": "eagle" in self.agents},
            {"name": "herald", "description": "School presentation generation", "icon": "ðŸ“Š", "loaded": "herald" in self.agents},
        ]

    def resolve_permission(self, request_id, approved) -> bool:
        """Forward permission resolution to Neo agent if loaded."""
        neo = self.agents.get("neo")
        if neo and hasattr(neo, 'pending_permissions'):
            if request_id in neo.pending_permissions:
                future = neo.pending_permissions[request_id]
                if not future.done():
                    future.set_result(approved)
                return True
        return True

    def resolve_folder_selection(self, request_id, folder) -> bool:
        """Forward folder selection to Neo agent if loaded."""
        neo = self.agents.get("neo")
        if neo and hasattr(neo, 'pending_folder_selections'):
            if request_id in neo.pending_folder_selections:
                future = neo.pending_folder_selections[request_id]
                if not future.done():
                    future.set_result(folder)
                return True
        return True

    def resolve_framework_selection(self, request_id, choice) -> bool:
        """Forward framework selection to Neo agent if loaded."""
        neo = self.agents.get("neo")
        if neo and hasattr(neo, 'pending_framework_selections'):
            if request_id in neo.pending_framework_selections:
                future = neo.pending_framework_selections[request_id]
                if not future.done():
                    future.set_result(choice)
                return True
        return True
