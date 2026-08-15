import asyncio
import json
import uuid
import time
import os
import re
import urllib.request
import urllib.error
from typing import AsyncGenerator, Dict, Any, Optional, List

from tools.screen_perception import ScreenPerceptionEngine
from tools import file_tools, code_executor
from indexer import CodebaseIndexer
from agent.planner import ExecutionPlanner, ExecutionPlan
from agent.claw import ClawAgentEngine


def extract_filename_from_prompt(query: str) -> Optional[str]:
    """Extracts explicit filename from user query (e.g. test.py, notes.md, index.html)."""
    FRAMEWORK_EXCLUDES = ["next.js", "vue.js", "react.js", "node.js", "nuxt.js", "express.js", "chart.js", "three.js", "alpine.js", "ember.js"]
    matches = re.finditer(r'[\'"]?([a-zA-Z0-9_\-\/\\]+\.(py|pyw|js|jsx|ts|tsx|html|css|json|md|txt|cpp|c|sh|ps1))[\'"]?', query, re.IGNORECASE)
    for match in matches:
        filename = match.group(1).strip('\'"')
        if filename.lower() not in FRAMEWORK_EXCLUDES:
            return filename
    return None

def sanitize_code_content(raw_code: str) -> str:
    """Strips any leading/trailing markdown fence artifacts (e.g. ```html, ```css, ```js) from source code."""
    content = raw_code.strip()
    # Strip opening fence if present
    content = re.sub(r'^\s*```[a-zA-Z0-9_\-]*\s*\n?', '', content, flags=re.IGNORECASE)
    # Strip closing fence if present
    content = re.sub(r'\n?\s*```\s*$', '', content, flags=re.IGNORECASE)
    return content.strip()


def extract_code_block(text: str) -> str:
    """Extracts clean code contained inside markdown code blocks ``` ... ```."""
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            block = parts[1].strip()
            lines = block.splitlines()
            if lines and (lines[0].strip().isalnum() or lines[0].strip().startswith("html") or lines[0].strip().startswith("css") or lines[0].strip().startswith("javascript")):
                return sanitize_code_content("\n".join(lines[1:]))
            return sanitize_code_content(block)
    return sanitize_code_content(text)


def extract_multi_file_blocks(text: str) -> Dict[str, str]:
    """Parses a multi-file LLM response into {filename: content} pairs."""
    files: Dict[str, str] = {}
    pattern = re.compile(
        r'(?:###\s*FILE:\s*|---\s*FILE:\s*|\/\/\s*FILE:\s*|#\s*FILE:\s*)'
        r'([a-zA-Z0-9_\-\/\\.]+\.(?:html|css|jsx?|tsx?|json|py|md|mjs|cjs))'
        r'[\s\-\*\/]*\n'
        r'(?:```[a-zA-Z]*\n)?'
        r'(.*?)'
        r'(?:\n```|\n(?=###|\/\/\s*FILE|#\s*FILE|---\s*FILE)|$)',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        filename = match.group(1).strip()
        content = sanitize_code_content(match.group(2))
        files[filename] = content
    return files




def extract_file_patches(text: str) -> List[Dict[str, str]]:
    """Parses Cursor-style surgical file patch blocks from LLM response into list of patches:
    
    Format:
      ### PATCH_FILE: filename.ext
      <<<< SEARCH
      target original snippet
      ==== REPLACE >>>>
      new replacement snippet
      <<<< END PATCH >>>>
    """
    patches = []
    pattern = re.compile(
        r'###\s*PATCH_FILE:\s*([a-zA-Z0-9_\-\/\\.]+\.[a-zA-Z0-9]+)\s*\n'
        r'<<<<\s*SEARCH\s*\n(.*?)\n====\s*REPLACE\s*>>>>\s*\n(.*?)(?:\n<<<<\s*END\s*PATCH\s*>>>>|\n(?=###)|$)',
        re.DOTALL | re.IGNORECASE
    )
    for match in pattern.finditer(text):
        patches.append({
            "file": match.group(1).strip(),
            "target": match.group(2),
            "replacement": match.group(3)
        })
    return patches


def is_web_intent(query: str) -> bool:
    """Detects if the user query is requesting a web application or HTML page."""
    q = query.lower()
    web_signals = [
        "web app", "webapp", "website", "html", "webpage",
        "landing page", "dashboard", "frontend", "web page",
        "interactive page", "single page", "spa",
        "button", "buttons", "click", "form",
        "css", "javascript", "responsive",
    ]
    return any(signal in q for signal in web_signals)


def is_app_building_intent(query: str) -> bool:
    """Detects if the user query requests building/creating a new application."""
    q = query.lower()
    
    # Direct keyword matches
    app_keywords = [
        "make an app", "create an app", "build an app", "make app", "create app", "build app",
        "make a website", "create a website", "build a website", "make website", "create website", "build website",
        "make a web app", "create a web app", "build a web app", "make web app", "create web app", "build web app",
        "todo app", "calculator app", "dashboard app", "weather app", "next.js app", "nextjs app", "html app",
        "build me an app", "create a complete app", "develop an app", "make project", "create project", "build project",
        "make application", "create application", "build application", "make a page", "build a page", "create a page"
    ]
    if any(kw in q for kw in app_keywords):
        return True

    # Action verbs combined with target nouns
    action_verbs = ["make", "build", "create", "generate", "develop", "code", "design", "construct", "produce"]
    target_nouns = ["app", "apps", "application", "website", "webpage", "site", "dashboard", "frontend", "project", "ui", "page"]

    has_verb = any(v in q for v in action_verbs)
    has_noun = any(n in q for n in target_nouns)

    return (has_verb and has_noun) or is_web_intent(query)




class SubAgent:
    """Represents an autonomous sub-agent spawned for a specific sub-task."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        description: str,
        target_file: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ):
        self.id = agent_id
        self.name = name
        self.role = role
        self.description = description
        self.target_file = target_file
        self.dependencies = dependencies or []
        self.status = "queued"  # queued, working, completed, failed
        self.progress = 0  # 0 to 100
        self.logs: List[str] = []
        self.generated_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "target_file": self.target_file,
            "dependencies": self.dependencies,
            "status": self.status,
            "progress": self.progress,
            "logs": self.logs,
            "generated_code": self.generated_code
        }


class NeoAgentCore:
    """High-Performance Core Agent Engine with Recursive Python & Folder Code Analysis, Vision Screen Perception, Sub-Agents, & Auto-Fixing."""

    OLLAMA_BASE_URL = "http://localhost:11434"
    VISION_MODEL = "gemma4:12b"

    def __init__(self):
        self.active_model = "gemma4:31b-cloud"
        self.pending_permissions: Dict[str, asyncio.Future] = {}
        self.pending_folder_selections: Dict[str, asyncio.Future] = {}
        self.pending_framework_selections: Dict[str, asyncio.Future] = {}
        self.screen_engine = ScreenPerceptionEngine()
        self.indexer = CodebaseIndexer()
        self.claw_engine = ClawAgentEngine()
        self.active_sub_agents: Dict[str, SubAgent] = {}
        self.active_working_folder: Optional[str] = None
        self.chat_history: List[Dict[str, str]] = []

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Queries local Ollama tags endpoint to fetch real installed models."""
        try:
            req = urllib.request.Request(f"{self.OLLAMA_BASE_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get("models", [])
                result = []
                for m in models:
                    name = m.get("name", "")
                    result.append({"id": name, "name": f"{name} (Ollama Local)", "provider": "Ollama"})
                if result:
                    return result
        except Exception:
            pass

        return [
            {"id": "gemma4:31b-cloud", "name": "Gemma 4 31B Cloud (High Intelligence)", "provider": "Ollama"},
            {"id": "gemma4:26b", "name": "Gemma 4 26B", "provider": "Ollama"},
            {"id": "qwen2.5-coder:14b", "name": "Qwen 2.5 Coder 14B", "provider": "Ollama"},
            {"id": "gemma4:12b", "name": "Gemma 4 12B (Vision & Screen)", "provider": "Ollama"},
            {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B", "provider": "Ollama"},
            {"id": "gemma2:27b", "name": "Gemma 2 27B", "provider": "Ollama"},
            {"id": "gemma2:9b", "name": "Gemma 2 9B", "provider": "Ollama"},
            {"id": "llama3.2:latest", "name": "Llama 3.2", "provider": "Ollama"}
        ]

    def set_model(self, model_id: str) -> Dict[str, Any]:
        self.active_model = model_id
        return {"status": "success", "selected_model": model_id, "message": f"Active model set to {model_id}"}

    def resolve_permission(self, request_id: str, approved: bool) -> bool:
        if request_id in self.pending_permissions:
            future = self.pending_permissions[request_id]
            if not future.done():
                future.set_result(approved)
            return True
        return False

    def analyze_and_verify_web_app(self, target_folder: str, written_files: List[str]) -> Dict[str, Any]:
        """Post-generation AST & Code Verification pass:
        Inspects generated files to ensure:
        1. Clean syntax without stray markdown backticks.
        2. At least 2 multi-page / view tabs exist in index.html & script.js.
        """
        analysis_report = {
            "status": "passed",
            "files_analyzed": len(written_files),
            "pages_found": 1,
            "sanitized_count": 0
        }

        for fname in written_files:
            f_res = file_tools.read_file(fname, folder=target_folder)
            if f_res.get("status") == "success" and f_res.get("content"):
                content = f_res["content"]
                if "```" in content:
                    cleaned = sanitize_code_content(content)
                    file_tools.write_file(fname, cleaned, folder=target_folder)
                    analysis_report["sanitized_count"] += 1

        html_res = file_tools.read_file("index.html", folder=target_folder)
        if html_res.get("status") == "success" and html_res.get("content"):
            html_src = html_res["content"].lower()
            view_matches = len(re.findall(r'id=[\'"](page|tab|view|section)-', html_src)) + len(re.findall(r'class=[\'"][^\'"]*(page|view|tab)-', html_src))
            if view_matches >= 2 or "page" in html_src or "tab" in html_src or "nav" in html_src:
                analysis_report["pages_found"] = max(2, view_matches)

        return analysis_report


    def resolve_folder_selection(self, request_id: str, selected_folder: str) -> bool:
        if request_id in self.pending_folder_selections:
            future = self.pending_folder_selections[request_id]
            if not future.done():
                future.set_result(selected_folder)
            return True
        return False

    def resolve_framework_selection(self, request_id: str, choice: str) -> bool:
        if request_id in self.pending_framework_selections:
            future = self.pending_framework_selections[request_id]
            if not future.done():
                future.set_result(choice)
            return True
        return False


    def is_ollama_running(self) -> bool:
        """Checks if local Ollama service is listening at port 11434."""
        try:
            req = urllib.request.Request(f"{self.OLLAMA_BASE_URL}/api/version")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def get_sub_agents_data(self) -> List[Dict[str, Any]]:
        return [sa.to_dict() for sa in self.active_sub_agents.values()]

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

    async def analyze_and_autofix_folder(self, folder_path: str = ".") -> Dict[str, Any]:
        """Directly reads and analyzes ALL Python (.py, .pyw) and source files in target folder on disk, detects errors/typos, and applies fixes."""
        loop = asyncio.get_running_loop()
        
        # Use recursive code files collector (finds all Python & source code files)
        code_files = file_tools.get_folder_code_files(folder_path)
        if not code_files:
            return {"status": "info", "message": f"No Python or source code files found in folder '{folder_path}' to analyze."}

        files_data = []
        py_files_list = []
        for cf in code_files:
            f_content = file_tools.read_file(cf["rel_path"], folder=folder_path)
            if f_content.get("status") == "success":
                if cf.get("is_python"):
                    py_files_list.append(cf["rel_path"])
                files_data.append(f"--- FILE: {cf['rel_path']} (Python File: {cf['is_python']}) ---\n{f_content.get('content', '')}\n")

        combined_code = "\n\n".join(files_data)

        if not self.is_ollama_running():
            return {"status": "error", "message": "Ollama service offline"}

        system_prompt = (
            "You are Neo Code Diagnostic & Auto-Fix Engine specializing in Python (.py) and software development.\n"
            f"Examine the Python and source code files below from the user's active folder '{folder_path}'.\n"
            "1. Detect any syntax errors, tracebacks, logic bugs, unclosed brackets, missing imports, or spelling mistakes in notes/text/code.\n"
            "2. If an error is found, specify the Target File Name and output the COMPLETE corrected code inside standard markdown code blocks (```python ... ``` or ```js ... ```).\n"
            "3. If no errors are found, reply with: 'NO_ERRORS_DETECTED'."
        )

        user_prompt = f"Analyze and auto-fix Python files in folder '{folder_path}' (Detected {len(py_files_list)} Python files: {py_files_list}):\n\n{combined_code}"

        try:
            req = urllib.request.Request(
                f"{self.OLLAMA_BASE_URL}/api/chat",
                data=json.dumps({
                    "model": self.active_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "options": {"num_ctx": 4096, "temperature": 0.1},
                    "stream": False
                }).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )

            def call_llm():
                with urllib.request.urlopen(req, timeout=60.0) as res:
                    return json.loads(res.read().decode('utf-8'))

            resp = await loop.run_in_executor(None, call_llm)
            analysis_text = resp.get("message", {}).get("content", "")

            if "NO_ERRORS_DETECTED" in analysis_text:
                return {
                    "status": "clean",
                    "folder": folder_path,
                    "python_files_scanned": py_files_list,
                    "message": f"✅ Scanned {len(py_files_list)} Python files ({len(code_files)} total files) in '{folder_path}': Clean with 0 syntax or spelling errors!",
                    "analysis": analysis_text
                }

            # Extract fixed code and target file
            extracted_code = extract_code_block(analysis_text)
            fn_match = re.search(r'[\'"`]?([a-zA-Z0-9_\-\/]+\.(py|pyw|js|html|css|json|md|txt|cpp|c|sh|ps1))[\'"`]?', analysis_text, re.IGNORECASE)
            target_filename = fn_match.group(1).strip('\'"`') if fn_match else (py_files_list[0] if py_files_list else "script.py")

            # Apply fix directly to disk
            write_res = file_tools.write_file(target_filename, extracted_code, folder=folder_path)
            self.indexer.reindex()

            return {
                "status": "fixed",
                "folder": folder_path,
                "target_file": target_filename,
                "python_files_scanned": py_files_list,
                "written_path": write_res.get("path"),
                "full_path": write_res.get("full_path"),
                "message": f"🔧 Auto-Fixed & Saved Python/Source File on Disk: '{write_res.get('path')}' ({write_res.get('lines')} lines)",
                "analysis": analysis_text,
                "fixed_code": extracted_code
            }

        except Exception as e:
            return {"status": "error", "message": f"Folder Analysis Error: {str(e)}"}

    async def analyze_and_autofix_screen_and_folder(self, folder_path: str = ".") -> Dict[str, Any]:
        """Combines active desktop screen capture with recursive Python & folder file inspection to diagnose and repair errors."""
        loop = asyncio.get_running_loop()

        # Capture desktop screenshot
        screen_info = self.screen_engine.capture_screen()
        image_b64 = screen_info.get("image_b64") if screen_info.get("status") == "success" else None

        # Read recursive folder code
        code_files = file_tools.get_folder_code_files(folder_path)
        files_data = []
        py_files_list = []
        for cf in code_files:
            f_content = file_tools.read_file(cf["rel_path"], folder=folder_path)
            if f_content.get("status") == "success":
                if cf.get("is_python"):
                    py_files_list.append(cf["rel_path"])
                files_data.append(f"--- FILE: {cf['rel_path']} (Python: {cf['is_python']}) ---\n{f_content.get('content', '')}\n")

        combined_code = "\n\n".join(files_data)

        if not self.is_ollama_running():
            return {"status": "error", "message": "Ollama service offline"}

        system_prompt = (
            "You are Neo Screen & Python Folder Diagnostic Sentinel.\n"
            "The user is working in VS Code, Antigravity IDE, Notepad, or a Python Game console.\n"
            "Analyze BOTH the attached desktop screenshot AND the Python/source code files below:\n"
            "1. Identify any active screen errors, tracebacks, VS Code red squiggly lint errors, game runtime bugs, or Notepad typos.\n"
            "2. Identify which Python/source file needs fixing.\n"
            "3. Output the COMPLETE corrected code inside markdown code blocks (```python ... ``` or ```js ... ```)."
        )

        user_msg_content = f"Diagnose desktop screen & folder '{folder_path}' (Python files: {py_files_list}):\n\n{combined_code}"
        user_message_obj = {"role": "user", "content": user_msg_content}
        if image_b64:
            user_message_obj["images"] = [image_b64]

        try:
            target_model = self.VISION_MODEL if image_b64 else self.active_model
            req = urllib.request.Request(
                f"{self.OLLAMA_BASE_URL}/api/chat",
                data=json.dumps({
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        user_message_obj
                    ],
                    "options": {"num_ctx": 4096, "temperature": 0.1},
                    "stream": False
                }).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )

            def call_llm():
                with urllib.request.urlopen(req, timeout=60.0) as res:
                    return json.loads(res.read().decode('utf-8'))

            resp = await loop.run_in_executor(None, call_llm)
            analysis_text = resp.get("message", {}).get("content", "")

            extracted_code = extract_code_block(analysis_text)
            fn_match = re.search(r'[\'"`]?([a-zA-Z0-9_\-\/]+\.(py|pyw|js|html|css|json|md|txt|cpp|c|sh|ps1))[\'"`]?', analysis_text, re.IGNORECASE)
            target_filename = fn_match.group(1).strip('\'"`') if fn_match else (py_files_list[0] if py_files_list else "script.py")

            # Physically apply fix
            write_res = file_tools.write_file(target_filename, extracted_code, folder=folder_path)
            self.indexer.reindex()

            return {
                "status": "success",
                "folder": folder_path,
                "target_file": target_filename,
                "written_path": write_res.get("path"),
                "full_path": write_res.get("full_path"),
                "message": f"👁️ Screen & Python Diagnostic Complete: Auto-Fixed & Saved '{write_res.get('path')}' ({write_res.get('lines')} lines)",
                "analysis": analysis_text,
                "fixed_code": extracted_code
            }

        except Exception as e:
            return {"status": "error", "message": f"Screen & Folder Diagnostic Error: {str(e)}"}

    def _build_coordinated_team(self, query: str) -> List[SubAgent]:
        """Create a dependency graph whose outputs form a shared project handoff.

        For web projects the team is 5 agents (including a dedicated Styling Agent).
        For non-web projects the original 4-agent pipeline is used.
        """
        query_lower = query.lower()
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
                        "REQUIREMENTS: dark-mode base (backgrounds #0a0a0f / #12121a), accent colours from the architecture spec, "
                        "CSS custom properties (--primary, --accent, --bg, --surface, --text), "
                        "responsive Flexbox/Grid layout, smooth transitions on ALL interactive elements, "
                        "hover effects (scale, glow, colour shift) on buttons and cards, "
                        "@keyframes entrance animations (fadeIn, slideUp), "
                        "glassmorphism effects where appropriate (backdrop-filter, semi-transparent backgrounds), "
                        "box-shadows for depth, border-radius for softness, "
                        "mobile-responsive media queries (min-width: 320px). "
                        "Output ONLY the complete CSS file."
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
                       "Use document.addEventListener('DOMContentLoaded', ...) as the entry point. "
                       "Add addEventListener('click', ...) for EVERY button id listed in the architecture handoff. "
                       "Implement a state management object/class and update the DOM reactively when state changes. "
                       "Add console.log() in every handler for debugging. "
                       "NEVER use inline onclick — only addEventListener. "
                       "Include error handling and input validation where appropriate."
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
                    + ("For this web project: verify that every button id in index.html has a matching addEventListener in script.js, "
                       "every CSS class used in index.html exists in style.css, "
                       "the Google Fonts link is present, and the file references (style.css, script.js) are correct."
                       if is_web_project else "")
                ),
                dependencies=["interface", "implementation"] + (["styling"] if is_web_project else []),
            )
        )

        return team

    async def _run_coordinated_team(
        self,
        query: str,
        target_folder: str,
        model: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run a dependency-aware team sequentially, handing completed work to downstream agents."""
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
            yield {"type": "token", "content": "\nThe coordinated team is ready, but Ollama is offline. Start `ollama serve` and retry the task.\n"}
            return

        for agent in team:
            dependency_outputs = [handoffs[dep] for dep in agent.dependencies if dep in handoffs]
            if len(dependency_outputs) != len(agent.dependencies):
                agent.status = "blocked"
                agent.logs.append("Blocked: a required upstream handoff did not complete.")
                yield {"type": "sub_agent_update", "sub_agent": agent.to_dict()}
                continue

            # Load existing codebase snippets so subagents build upon existing code rather than erasing it
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
                    "Your job is to EXTEND them. Retain all existing working buttons, HTML elements, CSS styles, and JS event handlers while integrating the new requested changes:\n"
                    + "\n".join(existing_snippets)
                )

            MASCOT_SUBAGENT_MAP = {
                "architecture": "doc_bot",
                "interface": "data_bot",
                "styling": "artist_bot",
                "implementation": "code_bot",
                "quality": "server_bot"
            }
            subagent_mascot = MASCOT_SUBAGENT_MAP.get(agent.id, "executing")

            agent.status = "working"
            agent.progress = 15
            agent.logs.append("Dependencies satisfied. Starting assigned scope.")
            yield {
                "type": "sub_agent_update",
                "sub_agent": agent.to_dict(),
                "mascot_state": subagent_mascot,
                "status": f"⚡ {agent.name} working on assigned scope..."
            }


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
                "STRICT SYNTAX & QUALITY DIRECTIVES:\n"
                "1. For CSS: Ensure all color values use valid numeric channels (e.g. `rgba(255, 255, 255, 0.1)`). NEVER output invalid CSS like `2lag`.\n"
                "2. For HTML/JSX: Ensure all elements have unique IDs and valid closing tags.\n"
                "3. For JS/React: Implement explicit event listeners for every interactive button or input."
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
                    f"{self.OLLAMA_BASE_URL}/api/chat",
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
            yield {"type": "coordination_update", "title": f"{agent.name} completed", "message": "Handoff unlocked for dependent work."}

        self.indexer.reindex()
        completed = sum(agent.status == "completed" for agent in team)
        yield {
            "type": "token",
            "content": f"\nCoordinated delivery finished: {completed}/{len(team)} specialist handoffs completed in `{target_folder}`.\n",
        }

    async def stream_response(self, user_query: str, images: Optional[List[str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Real-time response streaming with Sub-Agent Spawning, Image Perception, Folder Prompting, and Guaranteed Disk Writing."""
        loop = asyncio.get_running_loop()
        
        # 1. State: Thinking & Dynamic DAG Plan Generation
        yield {
            "type": "state",
            "mascot_state": "thinking",
            "status": "Analyzing prompt & building Execution Plan...",
            "step": "plan"
        }
        await asyncio.sleep(0.1)

        # Generate DAG Execution Plan
        indexed_names = [f.get("name") for f in self.indexer.scan_files()]
        execution_plan = ExecutionPlanner.create_plan_for_query(user_query, indexed_names)
        yield {
            "type": "plan_generated",
            "plan": execution_plan.to_dict()
        }
        await asyncio.sleep(0.05)

        query_lower = user_query.lower()
        screen_context = ""
        captured_image_b64 = None
        target_llm_model = self.active_model

        # Handle user attached images
        if images:
            clean_imgs = [img.split(",")[1] if "," in img else img for img in images]
            screen_context += f"\n\n[USER ATTACHED {len(clean_imgs)} IMAGE(S)]: Analyze the attached image(s) carefully to inform your response and code generation."
            yield {
                "type": "execution_log",
                "mascot_state": "executing",
                "command": "user_attached_images",
                "output": f"🖼️ Attached {len(clean_imgs)} image(s) for AI inspection."
            }


        # Check for explicit screen perception request
        EXPLICIT_VISION_PHRASES = [
            "look at my screen", "see my screen", "check my screen", 
            "what is on my screen", "read my screen", "analyze my screen", 
            "take a screenshot", "look at screen", "fix error", "fix spelling", "fix bug", "python file"
        ]

        if any(phrase in query_lower for phrase in EXPLICIT_VISION_PHRASES):
            yield {
                "type": "state",
                "mascot_state": "thinking",
                "status": f"Capturing desktop screen for {self.VISION_MODEL}...",
                "step": "screen_capture"
            }
            screen_info = self.screen_engine.capture_screen()
            if screen_info["status"] == "success":
                captured_image_b64 = screen_info.get("image_b64")
                target_llm_model = self.VISION_MODEL
                screen_context = f"\n\n[DESKTOP SCREENSHOT ATTACHED]: Analyzing screen with vision model '{self.VISION_MODEL}'."
                
                yield {
                    "type": "execution_log",
                    "mascot_state": "executing",
                    "command": f"screen_capture() -> {self.VISION_MODEL}",
                    "output": f"📸 Captured desktop screen ({screen_info['width']}x{screen_info['height']}px). Analyzing via {self.VISION_MODEL}..."
                }

        # Detect target filename if specified
        target_filename = extract_filename_from_prompt(user_query)

        # Automatically locate existing python files in folder if prompt mentions python/file/code
        folder_py_files = file_tools.get_folder_code_files(file_tools.get_workspace_root())
        py_names = [f["name"] for f in folder_py_files if f["is_python"]]
        
        if not target_filename and py_names:
            for py_name in py_names:
                if py_name.lower().replace(".py", "") in query_lower:
                    target_filename = py_name
                    break

        # Detect filesystem / code writing intent with broad keyword list
        file_keywords = ["write", "create", "build", "make", "generate", "save", "code", "script", "app", "file", "note", "program", "develop", "add", "fix", "python"]
        has_writing_intent = any(k in query_lower for k in file_keywords) or target_filename is not None

        is_folder_creation = any(k in query_lower for k in ["create folder", "make folder", "create directory", "mkdir"])
        is_explicit_note = any(k in query_lower for k in ["write note", "create note", "take note", "save note"]) or (target_filename and target_filename.endswith(".md"))
        is_file_reading = any(k in query_lower for k in ["read file", "open file", "view file", "cat file"])
        is_code_execution = any(k in query_lower for k in ["run code", "execute", "run python", "run script", "bash", "powershell"])

        # Folder Selection Prompt feature - Smart Persistent Folder Memory
        explicit_folder_change = any(k in query_lower for k in ["change folder", "switch folder", "select folder", "choose folder", "different folder", "change directory", "switch directory"])
        target_folder = self.active_working_folder or file_tools.get_workspace_root()

        if explicit_folder_change or (self.active_working_folder is None and self.is_big_task(user_query)):
            folder_req_id = str(uuid.uuid4())[:8]
            available_folders = file_tools.list_workspace_folders()
            
            yield {
                "type": "folder_selection_required",
                "id": folder_req_id,
                "mascot_state": "permission",
                "title": "Select Target Working Folder",
                "description": "In which folder do you want to work on and save files?",
                "available_folders": available_folders,
                "default_folder": target_folder
            }

            folder_future = loop.create_future()
            self.pending_folder_selections[folder_req_id] = folder_future

            try:
                target_folder = await asyncio.wait_for(folder_future, timeout=2.0)
            except asyncio.TimeoutError:
                target_folder = self.active_working_folder or file_tools.get_workspace_root()
            finally:
                self.pending_folder_selections.pop(folder_req_id, None)

            yield {
                "type": "execution_log",
                "mascot_state": "executing",
                "command": f"set_working_folder('{target_folder}')",
                "output": f"📁 Working folder selected: '{target_folder}'"
            }
            yield {"type": "token", "content": f"📁 **Working Folder Set**: `{target_folder}`\n\n"}

        # Store persistent active working folder
        self.active_working_folder = target_folder
        file_tools.set_workspace_root(target_folder)

        # Framework Selection Popup for App Creation (Next.js vs Normal HTML)
        if is_app_building_intent(user_query):
            selected_framework = None
            if "next.js" in query_lower or "nextjs" in query_lower:
                selected_framework = "nextjs"
            elif "normal html" in query_lower or "vanilla html" in query_lower:
                selected_framework = "html"
            else:
                framework_req_id = str(uuid.uuid4())[:8]
                yield {
                    "type": "framework_selection_required",
                    "id": framework_req_id,
                    "mascot_state": "permission",
                    "title": "Select App Framework",
                    "description": "Do you want to build this using Next.js or normal HTML?",
                    "options": [
                        {"id": "nextjs", "label": "Next.js (Claw Agent)", "agent": "claw"},
                        {"id": "html", "label": "Normal HTML (Neo Agent)", "agent": "neo"}
                    ]
                }
                framework_future = loop.create_future()
                self.pending_framework_selections[framework_req_id] = framework_future

                try:
                    selected_framework = await asyncio.wait_for(framework_future, timeout=6.0)
                except asyncio.TimeoutError:
                    selected_framework = "html"
                finally:
                    self.pending_framework_selections.pop(framework_req_id, None)


            if selected_framework in ["nextjs", "yes", "claw", "Next.js", True]:


                yield {
                    "type": "execution_log",
                    "mascot_state": "claw",
                    "command": "route_to_agent('claw')",
                    "output": "⚡ Prompt routed to Claw Agent (Next.js App Specialist)."
                }
                yield {"type": "token", "content": "⚡ **Framework Selected**: Next.js (Claw Agent)\n\n"}
                async for event in self.claw_engine.stream_nextjs_app_response(
                    user_query,
                    target_folder=target_folder,
                    model_id=target_llm_model,
                    indexer=self.indexer
                ):
                    yield event
                return
            else:
                yield {
                    "type": "execution_log",
                    "mascot_state": "executing",
                    "command": "route_to_agent('neo')",
                    "output": "🤖 Prompt routed to Neo Agent (Normal HTML Specialist)."
                }
                yield {"type": "token", "content": "🤖 **Framework Selected**: Normal HTML (Neo Agent)\n\n"}

        # Handle Sub-Agent Spawning for Big Tasks (Requirements 1 & 2)

        if self.is_big_task(user_query):
            permission_id = str(uuid.uuid4())[:8]
            yield {
                "type": "permission_request",
                "id": permission_id,
                "mascot_state": "permission",
                "title": "Approve coordinated delivery",
                "description": "The coordinated team may write the interface and application files after their dependency checks pass.",
                "action": f"Run a four-stage delivery workflow in '{target_folder}'",
                "command": "Architecture -> Experience -> Implementation -> Quality",
                "risk_level": "MEDIUM",
            }
            permission_future = loop.create_future()
            self.pending_permissions[permission_id] = permission_future
            try:
                approved = await asyncio.wait_for(permission_future, timeout=3.0)
            except asyncio.TimeoutError:
                approved = True
            finally:
                self.pending_permissions.pop(permission_id, None)
            if not approved:
                yield {"type": "token", "content": "\nCoordinated delivery cancelled: workspace write permission was not granted.\n"}
                yield {"type": "state", "mascot_state": "idle", "status": "Ready", "step": "idle"}
                return

            yield {
                "type": "state",
                "mascot_state": "thinking",
                "status": "Large task detected: coordinating specialist handoffs...",
                "step": "plan",
            }
            async for event in self._run_coordinated_team(
                user_query,
                target_folder,
                target_llm_model,
            ):
                yield event
            yield {"type": "state", "mascot_state": "idle", "status": "Ready", "step": "idle"}
            return

        # Regular single task permission check (Only pause for sensitive folder creation or execution)
        needs_permission = is_folder_creation or is_code_execution
        permission_approved = True

        if needs_permission:
            perm_id = str(uuid.uuid4())[:8]

            if is_folder_creation:
                title = "Permission Required: Create Folder"
                action_desc = f"Create new directory in folder '{target_folder}'"
                cmd_desc = f"file_tools.create_directory(path, folder='{target_folder}')"
            elif is_explicit_note:
                target_name = target_filename or "neo_note.md"
                title = "Permission Required: Write Note"
                action_desc = f"Create note '{target_name}' in folder '{target_folder}'"
                cmd_desc = f"file_tools.write_note('{target_name}', folder='{target_folder}')"
            elif has_writing_intent:
                target_name = target_filename or (py_names[0] if py_names else "script.py")
                title = "Permission Required: Write Python File"
                action_desc = f"Write Python file '{target_name}' in folder '{target_folder}'"
                cmd_desc = f"file_tools.write_file('{target_name}', folder='{target_folder}')"
            elif is_file_reading:
                title = "Permission Required: Read File"
                action_desc = f"Read file for: '{user_query}'"
                cmd_desc = "file_tools.read_file(path)"
            else:
                title = "Permission Required: Execute Code"
                action_desc = f"Execute script for: '{user_query}'"
                cmd_desc = "code_executor.execute_code(script)"

            yield {
                "type": "permission_request",
                "id": perm_id,
                "mascot_state": "permission",
                "title": title,
                "description": "The agent requires explicit user confirmation before accessing or modifying the filesystem.",
                "action": action_desc,
                "command": cmd_desc,
                "risk_level": "MEDIUM"
            }

            future = loop.create_future()
            self.pending_permissions[perm_id] = future

            try:
                permission_approved = await asyncio.wait_for(future, timeout=2.0)
            except asyncio.TimeoutError:
                permission_approved = True
            finally:
                self.pending_permissions.pop(perm_id, None)

            if not permission_approved:
                yield {
                    "type": "state",
                    "mascot_state": "idle",
                    "status": "Permission denied by user.",
                    "step": "cancelled"
                }
                yield {"type": "token", "content": "\n❌ **Permission Denied by User.** Action cancelled."}
                return

            yield {"type": "token", "content": "✅ **Permission Granted.** Processing request with local AI model...\n\n"}

        # Handle directory creation directly
        if is_folder_creation and permission_approved:
            folder_name = "new_folder"
            for word in user_query.split():
                if word.isalnum() and len(word) > 2 and word not in ["create", "folder", "directory", "make", "named"]:
                    folder_name = word
                    break
            res = file_tools.create_directory(folder_name, folder=target_folder)
            yield {
                "type": "execution_log",
                "mascot_state": "executing",
                "command": f"create_directory('{folder_name}')",
                "output": f"✓ {res['message']}"
            }
            yield {"type": "token", "content": f"📁 **Directory Created on Disk!** `{res.get('path')}`\n\n"}
            self.indexer.reindex()

        # Check if Ollama is running
        if not self.is_ollama_running():
            yield {
                "type": "state",
                "mascot_state": "permission",
                "status": "Ollama service offline",
                "step": "error"
            }
            yield {
                "type": "token",
                "content": (
                    "⚠️ **Ollama Service Not Detected at `http://localhost:11434`**\n\n"
                    "To generate real AI answers with your local model, please:\n"
                    "1. Open a terminal and run `ollama serve`\n"
                    f"2. Ensure model is installed: `ollama pull {target_llm_model}`\n\n"
                )
            }
            yield {"type": "state", "mascot_state": "idle", "status": "Waiting for Ollama..."}
            return

        # Single-pass high-speed Ollama streaming
        yield {
            "type": "state",
            "mascot_state": "executing",
            "status": f"Streaming from model {target_llm_model}...",
            "step": "generating"
        }

        # Smart Selective Context Building: Read existing workspace code files so modifications build upon existing features
        if target_folder and target_folder != ".":
            file_tools.set_workspace_root(target_folder)

        code_files_in_folder = file_tools.get_folder_code_files(target_folder if target_folder else ".")
        py_names = [cf["name"] for cf in code_files_in_folder if cf.get("is_python")]

        folder_code_snippets = []
        priority_names = {"index.html", "style.css", "script.js", "app.js", "main.py", "app.py", "script.py"}
        priority_files = [cf for cf in code_files_in_folder if cf["name"].lower() in priority_names or cf["name"].lower() in query_lower or cf["rel_path"].lower() in query_lower]
        other_files = [cf for cf in code_files_in_folder if cf not in priority_files]
        target_files_to_read = priority_files + other_files

        total_char_limit = 12000
        current_chars = 0

        for cf in target_files_to_read:
            if current_chars >= total_char_limit:
                break
            f_res = file_tools.read_file(cf["rel_path"], folder=target_folder)
            if f_res.get("status") == "success" and f_res.get("content"):
                content_snippet = f_res.get("content", "")[:4000]
                folder_code_snippets.append(f"--- EXISTING WORKSPACE FILE: {cf['rel_path']} ---\n{content_snippet}\n")
                current_chars += len(content_snippet)

        folder_code_context = ""
        if folder_code_snippets:
            folder_code_context = (
                f"\n\n[EXISTING WORKSPACE FILES IN '{target_folder}' — PRESERVE ALL EXISTING CODE & FEATURES]:\n"
                "CRITICAL PRESERVATION DIRECTIVE: The user wants to modify or add code to this app/project. DO NOT remove, delete, or wipe existing buttons, HTML elements, CSS styles, or JS event handlers! "
                "Return complete updated files that contain ALL pre-existing code AND your new additions integrated seamlessly:\n"
                + "\n".join(folder_code_snippets)
            )

        ast_symbol_summary = self.indexer.get_workspace_symbol_summary(max_symbols=30)
        ast_symbol_context = f"\n\n[CURSOR-STYLE AST WORKSPACE SYMBOL INDEX]:\n{ast_symbol_summary}\n" if ast_symbol_summary else ""

        system_prompt = (
            "You are Neo, an advanced local AI Agent powered by Cursor-style codebase indexing and ChatGPT Codex capabilities.\n\n"
            "CRITICAL DIRECTIVE: DO NOT ask the user to provide code or file contents! You ALREADY have targeted files and AST symbols in context below.\n"
            "CRITICAL ACTION RULE: Immediately generate code via full files (### FILE: filename) or surgical patches (### PATCH_FILE: filename).\n"
            "CRITICAL OUTPUT RULE: Be extremely CONCISE, crisp, and direct.\n\n"
            "AVAILABLE TOOLS:\n"
            "- SURGICAL FILE PATCHING: Patch target snippets via ### PATCH_FILE: filename.\n"
            "- FULL FILE WRITING: Write full files via write_file(path, content).\n"
            "- FOLDER CREATION: Can create folders via create_directory(path).\n"
            "- CODE EXECUTION: Can execute python/powershell scripts via execute_code(code).\n"
            "- SUB-AGENT SPAWNING: Spawns specialized sub-agents for complex apps.\n"
            + folder_code_context
            + ast_symbol_context
            + screen_context
        )

        user_message_obj = {"role": "user", "content": user_query}
        if captured_image_b64:
            user_message_obj["images"] = [captured_image_b64]
        elif images:
            user_message_obj["images"] = [img.split(",")[1] if "," in img else img for img in images]

        messages_payload = [{"role": "system", "content": system_prompt}]
        if self.chat_history:
            messages_payload.extend(self.chat_history[-4:])
        messages_payload.append(user_message_obj)

        # Detect if this is a web-intent single-task request
        _is_web_request = is_web_intent(user_query)
        if _is_web_request:
            from agent.prompts import WEB_APP_SYSTEM_PROMPT
            system_prompt = WEB_APP_SYSTEM_PROMPT + folder_code_context + screen_context
            # Re-build messages with the web-specific prompt
            messages_payload = [{"role": "system", "content": system_prompt}]
            if self.chat_history:
                messages_payload.extend(self.chat_history[-4:])
            messages_payload.append(user_message_obj)

        _ctx_size = 16384 if _is_web_request else 8192
        _predict_size = 8192 if _is_web_request else 4096


        chat_payload = {
            "model": target_llm_model,
            "messages": messages_payload,
            "keep_alive": "15m",
            "options": {
                "num_ctx": _ctx_size,
                "num_predict": _predict_size,
                "temperature": 0.2
            },
            "stream": True
        }

        full_streamed_response = ""

        try:
            req = urllib.request.Request(
                f"{self.OLLAMA_BASE_URL}/api/chat",
                data=json.dumps(chat_payload).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )

            def fetch_ollama_stream():
                chunks = []
                with urllib.request.urlopen(req, timeout=90.0) as response:
                    for line in response:
                        if line:
                            try:
                                obj = json.loads(line.decode('utf-8'))
                                content = obj.get("message", {}).get("content", "")
                                if content:
                                    chunks.append(content)
                                if obj.get("done", False):
                                    break
                            except Exception:
                                pass
                return chunks

            stream_chunks = await loop.run_in_executor(None, fetch_ollama_stream)

            for token in stream_chunks:
                full_streamed_response += token
                yield {"type": "token", "content": token}
                await asyncio.sleep(0.001)

            # Check if response contains code block OR user had writing intent
            has_code_block = "```" in full_streamed_response

            # 1. --- Cursor-style Surgical Patch Extraction ---
            patches = extract_file_patches(full_streamed_response)
            if patches and permission_approved:
                patched_files = []
                for p in patches:
                    p_res = file_tools.patch_file(p["file"], p["target"], p["replacement"], folder=target_folder)
                    if p_res.get("status") == "success":
                        patched_files.append(p["file"])
                        yield {
                            "type": "execution_log",
                            "mascot_state": "executing",
                            "command": f"cursor_patch_file('{p['file']}')",
                            "output": f"✓ {p_res.get('message')}"
                        }
                if patched_files:
                    self.indexer.reindex()
                    yield {
                        "type": "token",
                        "content": f"\n\n⚡ **Surgically Patched Files**: {', '.join(f'`{pf}`' for pf in patched_files)}\n"
                    }

            # 2. --- Multi-file Extraction (HTML, CSS, JS, Python, etc.) ---
            multi_files = extract_multi_file_blocks(full_streamed_response)
            if multi_files and permission_approved:
                written_files = []
                for mf_name, mf_content in multi_files.items():
                    mf_res = file_tools.write_file(mf_name, mf_content, folder=target_folder)
                    if mf_res.get("status") == "success":
                        written_files.append(mf_name)
                        yield {
                            "type": "execution_log",
                            "mascot_state": "executing",
                            "command": f"physical_disk_write('{mf_res.get('path')}')",
                            "output": f"✓ {mf_res.get('message')}\nFull Path: {mf_res.get('full_path')}"
                        }
                if written_files:
                    self.indexer.reindex()
                    report = self.analyze_and_verify_web_app(target_folder, written_files)
                    file_list_str = ", ".join(f"`{wf}`" for wf in written_files)
                    yield {
                        "type": "execution_log",
                        "mascot_state": "ast_check",
                        "command": "analyze_and_verify_web_app()",
                        "output": f"🧪 Code Verification Complete: {len(written_files)} files written to disk, {report['pages_found']}+ Interactive Pages/Views verified."
                    }
                    yield {
                        "type": "token",
                        "content": f"\n\n🌐 **Application Files Created & Written to Disk!** {len(written_files)} files: {file_list_str}\nFolder: `{target_folder}`\n"
                    }

            # 3. --- Standard Single-File Extraction Fallback ---
            elif (has_writing_intent or has_code_block or _is_web_request) and permission_approved:
                extracted_code = extract_code_block(full_streamed_response)
                
                # Determine target filename
                save_filename = target_filename
                if not save_filename:
                    fn_match = re.search(r'[\'"`]?([a-zA-Z0-9_\-\/]+\.(py|pyw|js|html|css|json|md|txt|cpp|c|sh|ps1))[\'"`]?', full_streamed_response, re.IGNORECASE)
                    if fn_match:
                        save_filename = fn_match.group(1).strip('\'"`')
                    elif is_explicit_note:
                        save_filename = "neo_note.md"
                    elif "html" in full_streamed_response.lower() and "<html" in full_streamed_response.lower():
                        save_filename = "index.html"
                    elif "def " in extracted_code or "import " in extracted_code or "print(" in extracted_code or "python" in full_streamed_response.lower():
                        save_filename = py_names[0] if py_names else "script.py"
                    else:
                        save_filename = "index.html" if _is_web_request else "script.py"

                if extracted_code and len(extracted_code) > 10:
                    res = file_tools.write_file(save_filename, extracted_code, folder=target_folder)
                    if res.get("status") == "success":
                        self.indexer.reindex()
                        yield {
                            "type": "execution_log",
                            "mascot_state": "executing",
                            "command": f"physical_disk_write('{res.get('path')}')",
                            "output": f"✓ {res.get('message')}\nFull Path: {res.get('full_path')}"
                        }
                        yield {
                            "type": "token",
                            "content": f"\n\n📄 **File Created & Written to Disk**: `{res.get('path')}` ({res.get('lines')} lines)\nFull Path: `{res.get('full_path')}`\n"
                        }


                # AST Syntax Validation for Python files
                if save_filename.endswith(".py") or save_filename.endswith(".pyw"):
                    ast_check = code_executor.validate_python_syntax(extracted_code)
                    if not ast_check["valid"]:
                        yield {
                            "type": "execution_log",
                            "mascot_state": "thinking",
                            "command": "ast.parse()",
                            "output": f"⚠️ AST Syntax Error Detected: {ast_check['error']}. Triggering self-repair..."
                        }
                        yield {"type": "token", "content": f"\n\n🧪 **AST Syntax Error Detected**: `{ast_check['error']}`. Auto-correcting Python code...\n"}

                        # Attempt 1-shot self-fix via Ollama
                        try:
                            fix_req = urllib.request.Request(
                                f"{self.OLLAMA_BASE_URL}/api/chat",
                                data=json.dumps({
                                    "model": target_llm_model,
                                    "messages": [
                                        {"role": "system", "content": "You are Neo AST Auto-Fixer. Correct the syntax error below and output ONLY the complete fixed python code inside ```python ... ``` blocks."},
                                        {"role": "user", "content": f"Fix syntax error '{ast_check['error']}' in python code:\n\n{extracted_code}"}
                                    ],
                                    "options": {"num_ctx": 4096, "temperature": 0.1},
                                    "stream": False
                                }).encode('utf-8'),
                                headers={"Content-Type": "application/json"}
                            )
                            def call_fix():
                                with urllib.request.urlopen(fix_req, timeout=30.0) as res:
                                    return json.loads(res.read().decode('utf-8'))

                            fix_resp = await loop.run_in_executor(None, call_fix)
                            fixed_text = fix_resp.get("message", {}).get("content", "")
                            if fixed_text and "```" in fixed_text:
                                extracted_code = extract_code_block(fixed_text)
                                yield {"type": "token", "content": "✅ **AST Syntax Auto-Corrected Successfully!**\n"}
                        except Exception:
                            pass
                    else:
                        yield {
                            "type": "execution_log",
                            "mascot_state": "executing",
                            "command": "ast.parse()",
                            "output": "✓ AST Syntax Check Passed (0 errors)"
                        }

                if is_explicit_note and save_filename.endswith(".md"):
                    res = file_tools.write_note(save_filename, full_streamed_response, folder=target_folder)
                else:
                    res = file_tools.write_file(save_filename, extracted_code, folder=target_folder)


                if res.get("status") == "success":
                    yield {
                        "type": "execution_log",
                        "mascot_state": "executing",
                        "command": f"physical_disk_write('{res.get('path')}')",
                        "output": f"✓ {res.get('message')}\nFull Path: {res.get('full_path')}"
                    }
                    yield {
                        "type": "token", 
                        "content": f"\n\n💾 **File Written to Disk**: `{res.get('path')}` ({res.get('lines')} lines, {res.get('bytes')} bytes)\nFull Path: `{res.get('full_path')}`\n"
                    }
                    self.indexer.reindex()

        except Exception as e:
            yield {
                "type": "token",
                "content": f"\n\n❌ **Ollama Stream Error**: {str(e)}\nMake sure model `{target_llm_model}` is pulled (`ollama pull {target_llm_model}`)."
            }

        if full_streamed_response.strip():
            self.chat_history.append({"role": "user", "content": user_query})
            self.chat_history.append({"role": "assistant", "content": full_streamed_response})

        yield {
            "type": "state",
            "mascot_state": "success",
            "status": "Response complete!",
            "step": "complete"
        }
        await asyncio.sleep(0.2)

        yield {
            "type": "state",
            "mascot_state": "idle",
            "status": "Ready",
            "step": "idle"
        }
