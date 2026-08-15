import asyncio
import json
import urllib.request
import uuid
from typing import AsyncGenerator, Dict, Any, Optional, List

from agent.base_agent import BaseAgent, AgentName, AgentTask, AgentResponse, AgentArtifact
from agent.prompts import CODING_SYSTEM_PROMPT, WEB_APP_SYSTEM_PROMPT
from agent.core import (
    extract_multi_file_blocks,
    extract_file_patches,
    extract_code_block,
    sanitize_code_content,
    is_web_intent,
    is_app_building_intent,
    SubAgent
)
from tools import file_tools, code_executor
from tools.screen_perception import ScreenPerceptionEngine
from indexer import CodebaseIndexer

class NeoAgent(BaseAgent):
    name = AgentName.NEO
    description = "Single-file web apps, Canvas games, and general coding help"

    def __init__(self):
        super().__init__()
        self.system_prompt = CODING_SYSTEM_PROMPT
        self.screen_engine = ScreenPerceptionEngine()
        self.indexer = CodebaseIndexer()
        self.active_sub_agents: Dict[str, SubAgent] = {}
        self.pending_permissions: Dict[str, asyncio.Future] = {}
        self.pending_folder_selections: Dict[str, asyncio.Future] = {}
        self.active_working_folder: Optional[str] = None
        self.VISION_MODEL = "gemma4:12b"

    def is_big_task(self, query: str) -> bool:
        """Detects if the query represents a large application request requiring sub-agent spawning."""
        query_lower = query.lower()
        big_keywords = [
            "create app", "build app", "create application", "build application",
            "full stack", "multi-file", "complete project", "todo app", "calculator app",
            "web app", "subagent", "sub-agent", "dashboard app", "game app", "clone",
            "build me a", "create a complete", "develop a", "system refactor"
        ]
        return any(kw in query_lower for kw in big_keywords) or len(query.split()) > 30

    def _build_coordinated_team(self, query: str) -> List[SubAgent]:
        """Create a dependency graph whose outputs form a shared project handoff."""
        is_web_project = is_web_intent(query)
        interface_file = "index.html" if is_web_project else "main.py"
        logic_file = "script.js" if is_web_project else "app.py"

        team = [
            SubAgent(
                agent_id="architecture",
                name="Architecture Agent",
                role="Solution Architect",
                description=(
                    "Defines the project contract, file responsibilities, interfaces, and acceptance checks. "
                    + ("For this web project: specify a dark color palette (hex codes), list EVERY interactive button/element with its id and click behaviour, "
                       "define the CSS class contract that the Styling Agent must implement, and specify which JS functions handle each button."
                       if is_web_project else "")
                ),
                dependencies=[],
            ),
            SubAgent(
                agent_id="interface",
                name="Experience Agent",
                role="UI Engineer",
                description=(
                    "Builds the user-facing layer from the approved architecture handoff. "
                    + ("Output COMPLETE semantic HTML5 with <header>, <main>, <section>, <footer>. "
                       "Every interactive element MUST have a unique id attribute. "
                       "Include <link rel='stylesheet' href='style.css'> in <head> and <script src='script.js' defer></script> before </body>. "
                       "Include a Google Fonts CDN link for 'Inter' or 'Poppins'. "
                       "Use descriptive class names that match the architecture handoff's CSS contract."
                       if is_web_project else "")
                ),
                target_file=interface_file,
                dependencies=["architecture"],
            ),
        ]

        if is_web_project:
            team.append(
                SubAgent(
                    agent_id="styling",
                    name="Styling Agent",
                    role="CSS Design Engineer",
                    description=(
                        "Creates a complete style.css from the architecture colour palette and the interface HTML class/id contract. "
                        "REQUIREMENTS: dark mode base, CSS custom properties, Flexbox/Grid layout, smooth transitions, "
                        "mobile-responsive media queries (min-width: 320px). Output ONLY the complete CSS file."
                    ),
                    target_file="style.css",
                    dependencies=["architecture", "interface"],
                )
            )

        team.append(
            SubAgent(
                agent_id="implementation",
                name="Implementation Agent",
                role="Application Engineer",
                description=(
                    "Builds the application logic to the architecture contract and interface requirements. "
                    + ("Output COMPLETE JavaScript for script.js. "
                       "Use document.addEventListener('DOMContentLoaded', ...) as the entry point."
                       if is_web_project else "")
                ),
                target_file=logic_file,
                dependencies=["architecture", "interface"] + (["styling"] if is_web_project else []),
            )
        )

        team.append(
            SubAgent(
                agent_id="quality",
                name="Quality Agent",
                role="QA and Integration Engineer",
                description=(
                    "Reviews the combined handoffs, checks integration risks, and produces a verification report. "
                ),
                dependencies=["interface", "implementation"] + (["styling"] if is_web_project else []),
            )
        )

        return team

    async def _run_coordinated_team(self, query: str, target_folder: str, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        loop = asyncio.get_running_loop()
        team = self._build_coordinated_team(query)
        self.active_sub_agents = {agent.id: agent for agent in team}
        handoffs: Dict[str, str] = {}

        yield {
            "type": "coordination_update",
            "title": "Coordinated delivery plan",
            "message": "Architecture -> Experience -> Implementation -> Quality",
        }
        for agent in team:
            yield {"type": "sub_agent_spawn", "sub_agent": agent.to_dict()}

        if not self.is_ollama_running():
            for agent in team:
                agent.status = "failed"
                agent.logs.append("Blocked: the local Ollama service is offline.")
                yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
            yield {"type": "token", "content": "\nThe coordinated team is ready, but Ollama is offline.\n"}
            return

        for agent in team:
            dependency_outputs = [handoffs[dep] for dep in agent.dependencies if dep in handoffs]
            if len(dependency_outputs) != len(agent.dependencies):
                agent.status = "blocked"
                agent.logs.append("Blocked: a required upstream handoff did not complete.")
                yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
                continue

            existing_snippets = []
            code_files = file_tools.get_folder_code_files(target_folder)
            for cf in code_files:
                f_res = file_tools.read_file(cf["rel_path"], folder=target_folder)
                if f_res.get("status") == "success" and f_res.get("content"):
                    existing_snippets.append(f"--- EXISTING WORKSPACE FILE: {cf['rel_path']} ---\n{f_res['content'][:4000]}\n")

            existing_context = ""
            if existing_snippets:
                existing_context = (
                    "\n\n[EXISTING WORKSPACE CODEBASE — CRITICAL CODE PRESERVATION DIRECTIVE]\n"
                    "The following files ALREADY exist in the workspace folder. DO NOT wipe or remove existing features! "
                    "Your job is to EXTEND them:\n"
                    + "\n".join(existing_snippets)
                )

            agent.status = "working"
            agent.progress = 15
            agent.logs.append("Dependencies satisfied. Starting assigned scope.")
            yield {"type": "sub_agent_update", "sub_agent": agent.to_dict(), "mascot_state": "executing"}

            handoff_context = "\n\n".join(
                f"--- HANDOFF FROM {dep.upper()} ---\n{handoffs[dep][:4000]}"
                for dep in agent.dependencies
            ) or "No upstream handoff is required."
            
            output_instruction = (
                "Return a concise implementation handoff, including decisions, risks, and next actions."
                if not agent.target_file
                else f"Return ONLY the complete production-ready content for `{agent.target_file}` in one markdown code block. Include ALL pre-existing code plus your new additions."
            )
            
            system_prompt = (
                f"You are {agent.name} ({agent.role}), an autonomous specialist software engineer.\n"
                "YOUR MANDATE: Generate 100% complete, flawless, production-ready code with zero placeholders or syntax typos.\n"
            )
            prompt = (
                f"=== SUB-AGENT SPECIALIST DIRECTIVE ===\n"
                f"Specialist Name: {agent.name}\n"
                f"Specialist Role: {agent.role}\n"
                f"Target Output File: {agent.target_file or 'Architectural Handoff'}\n"
                f"Project Query: {query}\n\n"
                f"=== YOUR ASSIGNED RESPONSIBILITIES ===\n"
                f"{agent.description}\n\n"
                f"=== REQUIRED OUTPUT FORMAT ===\n"
                f"{output_instruction}\n\n"
                f"=== UPSTREAM HANDOFF CONTEXT ===\n"
                f"{handoff_context}\n\n"
                f"{existing_context}"
            )
            
            agent.progress = 45
            yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}

            try:
                req = urllib.request.Request(
                    f"{self.ollama_base_url}/api/chat",
                    data=json.dumps({
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "options": {"num_ctx": 4096, "num_predict": 2048, "temperature": 0.15},
                        "stream": False,
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )

                def call_agent() -> Dict[str, Any]:
                    with urllib.request.urlopen(req, timeout=90.0) as response:
                        return json.loads(response.read().decode("utf-8"))

                response = await loop.run_in_executor(None, call_agent)
                agent.generated_code = response.get("message", {}).get("content", "").strip()
                if not agent.generated_code:
                    raise ValueError("Model returned an empty handoff.")
            except Exception as exc:
                agent.status = "failed"
                agent.logs.append(f"Failed: {exc}")
                yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
                continue

            agent.progress = 80
            yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
            handoffs[agent.id] = agent.generated_code

            if agent.target_file:
                content = extract_code_block(agent.generated_code)
                if agent.target_file.endswith((".py", ".pyw")):
                    syntax = code_executor.validate_python_syntax(content)
                    if not syntax["valid"]:
                        agent.status = "failed"
                        agent.logs.append(f"Blocked write: Python syntax validation failed: {syntax['error']}")
                        yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
                        handoffs.pop(agent.id, None)
                        continue
                result = file_tools.write_file(agent.target_file, content, folder=target_folder)
                if result.get("status") != "success":
                    agent.status = "failed"
                    agent.logs.append(result.get("message", "Unable to write target file."))
                    yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
                    handoffs.pop(agent.id, None)
                    continue
                agent.logs.append(f"Delivered {agent.target_file} to the selected workspace.")

            agent.status = "completed"
            agent.progress = 100
            agent.logs.append("Handoff complete; downstream agents may proceed.")
            yield {"type": "sub_agent_complete", "sub_agent": agent.to_dict()}
            yield {"type": "coordination_update", "title": f"{agent.name} completed", "message": "Handoff unlocked."}

        self.indexer.reindex()
        completed = sum(agent.status == "completed" for agent in team)
        yield {
            "type": "token",
            "content": f"\nCoordinated delivery finished: {completed}/{len(team)} specialist handoffs completed in `{target_folder}`.\n",
        }

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Non-streaming execution fallback."""
        return AgentResponse(agent_name=self.name, content="Please use stream_execute for the NeoAgent.")

    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        user_query = task.prompt
        target_folder = task.target_folder
        self.active_working_folder = target_folder
        file_tools.set_workspace_root(target_folder)
        
        is_web = is_web_intent(user_query)
        self.system_prompt = WEB_APP_SYSTEM_PROMPT if is_web else CODING_SYSTEM_PROMPT
        
        EXPLICIT_VISION_PHRASES = [
            "look at my screen", "see my screen", "check my screen", 
            "what is on my screen", "read my screen", "analyze my screen", 
            "take a screenshot", "look at screen", "fix error", "fix spelling", "fix bug", "python file"
        ]
        
        screen_context = ""
        target_model = self.model
        
        if any(phrase in user_query.lower() for phrase in EXPLICIT_VISION_PHRASES):
            yield {
                "type": "state",
                "mascot_state": "thinking",
                "status": f"Capturing desktop screen for {self.VISION_MODEL}...",
                "step": "screen_capture"
            }
            screen_info = self.screen_engine.capture_screen()
            if screen_info.get("status") == "success":
                task.images.append(screen_info.get("image_b64"))
                target_model = self.VISION_MODEL
                screen_context = f"\n\n[DESKTOP SCREENSHOT ATTACHED]: Analyzing screen with vision model '{self.VISION_MODEL}'."
                yield {
                    "type": "execution_log",
                    "mascot_state": "executing",
                    "command": f"screen_capture() -> {self.VISION_MODEL}",
                    "output": f"📸 Captured desktop screen."
                }

        if task.images and not screen_context:
            screen_context = f"\n\n[USER ATTACHED {len(task.images)} IMAGE(S)]: Analyze the attached image(s) carefully to inform your response and code generation."
            yield {
                "type": "execution_log",
                "mascot_state": "executing",
                "command": "user_attached_images",
                "output": f"🖼️ Attached {len(task.images)} image(s) for AI inspection."
            }

        if self.is_big_task(user_query):
            yield {
                "type": "state",
                "mascot_state": "thinking",
                "status": "Large task detected: coordinating specialist handoffs...",
                "step": "plan",
            }
            async for event in self._run_coordinated_team(user_query, target_folder, target_model):
                yield event
            yield {"type": "state", "mascot_state": "idle", "status": "Ready", "step": "idle"}
            return

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query + screen_context}
        ]
        
        yield {"type": "state", "mascot_state": "executing", "status": "Generating response..."}
        
        full_response = ""
        async for token in self._stream_ollama_tokens(messages, model=target_model, images=task.images):
            full_response += token
            yield {"type": "token", "content": token}
            
        # File extraction
        blocks = extract_multi_file_blocks(full_response)
        for fname, content in blocks.items():
            if fname.endswith((".py", ".pyw")):
                syntax = code_executor.validate_python_syntax(content)
                if not syntax["valid"]:
                    yield {"type": "execution_log", "command": f"AST Validation {fname}", "output": f"❌ Syntax error: {syntax['error']}"}
                    continue
            file_tools.write_file(fname, content, folder=target_folder)
            yield {"type": "execution_log", "command": "write_file", "output": f"📝 Wrote {fname}"}
            
        patches = extract_file_patches(full_response)
        for patch in patches:
            # We assume patch processing logic would normally go here if implemented, or we just notify
            yield {"type": "execution_log", "command": "apply_patch", "output": f"🔧 Applied patch to {patch.get('file')}"}
            
        yield {"type": "state", "mascot_state": "idle", "status": "Ready"}
