import os
import json
import ast
import re
from typing import AsyncGenerator, Dict, Any, List, Optional

from agent.base_agent import BaseAgent, AgentName, AgentTask, AgentResponse, AgentArtifact
from agent.prompts import EAGLE_SYSTEM_PROMPT
from tools.document_tools import detect_document_type, extract_document_summary, read_code_file
from tools.vision_debugger import VisionDebugger, DebugCard
from tools import file_tools
from agent.core import extract_multi_file_blocks, extract_file_patches, extract_code_block, extract_filename_from_prompt
from indexer import CodebaseIndexer

class EagleAgent(BaseAgent):
    """Eagle Agent: Specializes in code review, bug analysis, auto-fixing errors to disk, document extraction, and screen vision debugging."""

    name = AgentName.EAGLE
    description = "Code analysis, document parsing, bug fixing, and vision debugging"

    def __init__(self):
        super().__init__()
        self.system_prompt = EAGLE_SYSTEM_PROMPT
        self.vision_debugger = VisionDebugger()
        self.indexer = CodebaseIndexer()

    def _build_analysis_context(self, task: AgentTask) -> Dict[str, Any]:
        """Gathers all available code, document, and workspace context for the Eagle LLM."""
        context_data = {
            "code_snippets": [],
            "documents": [],
            "workspace_summary": "",
            "language": "python",
            "primary_file": None
        }

        # 1. Check explicit files attached
        if task.files:
            for file_path in task.files:
                ftype = detect_document_type(file_path)
                if ftype == "code":
                    res = read_code_file(file_path)
                    if res.get("status") == "success":
                        context_data["code_snippets"].append({
                            "path": file_path,
                            "language": res.get("language", "python"),
                            "content": res.get("content", "")
                        })
                        context_data["language"] = res.get("language", "python")
                        if not context_data["primary_file"]:
                            context_data["primary_file"] = file_path
                elif ftype in ["pdf", "pptx", "xlsx", "csv"]:
                    doc_res = extract_document_summary(file_path)
                    if doc_res.get("status") == "success":
                        context_data["documents"].append({
                            "path": file_path,
                            "type": ftype,
                            "summary": doc_res.get("summary_text", "")
                        })

        # 2. Check if prompt mentions a specific filename in workspace
        prompt_fn = extract_filename_from_prompt(task.prompt)
        target_dir = task.target_folder or file_tools.get_workspace_root()
        if prompt_fn and not context_data["code_snippets"]:
            full_fn = os.path.join(target_dir, prompt_fn)
            if os.path.exists(full_fn):
                res = read_code_file(full_fn)
                if res.get("status") == "success":
                    context_data["code_snippets"].append({
                        "path": prompt_fn,
                        "language": res.get("language", "python"),
                        "content": res.get("content", "")
                    })
                    context_data["language"] = res.get("language", "python")
                    context_data["primary_file"] = prompt_fn

        # 3. Check if workspace review is requested or target_folder is set
        prompt_lower = task.prompt.lower()
        needs_workspace_scan = any(kw in prompt_lower for kw in ["workspace", "project", "folder", "all files", "check my code", "review code", "find bugs", "fix error", "debug"])
        
        if needs_workspace_scan and os.path.exists(target_dir):
            try:
                tree = file_tools.list_directory(target_dir)
                items = tree.get("items", [])
                code_files = [it["name"] for it in items if it.get("type") == "file" and any(it["name"].endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md"])]
                
                ws_snippets = []
                for cf in code_files[:8]:
                    full_p = os.path.join(target_dir, cf)
                    f_res = file_tools.read_file(full_p)
                    if f_res.get("status") == "success":
                        content = f_res.get("content", "")
                        lines = content.splitlines()
                        if len(lines) > 150:
                            content = "\n".join(lines[:150]) + f"\n... [{len(lines)-150} lines truncated]"
                        ws_snippets.append(f"--- File: {cf} ---\n{content}\n")
                        if not context_data["primary_file"]:
                            context_data["primary_file"] = cf
                
                if ws_snippets:
                    context_data["workspace_summary"] = f"Workspace Root: {target_dir}\nFiles:\n" + "\n".join(ws_snippets)
            except Exception:
                pass

        # 4. Check for inline markdown code blocks in prompt
        if "```" in task.prompt:
            parts = task.prompt.split("```")
            for i in range(1, len(parts), 2):
                block = parts[i].strip()
                if not block:
                    continue
                lines = block.splitlines()
                first_line = lines[0].strip().lower()
                known_langs = ["python", "py", "javascript", "js", "typescript", "ts", "html", "css", "json", "sql", "bash", "sh", "c", "cpp", "java", "rust", "go"]
                if first_line in known_langs:
                    lang = first_line
                    code_text = "\n".join(lines[1:])
                else:
                    lang = "python"
                    code_text = block

                if code_text.strip():
                    context_data["code_snippets"].append({
                        "path": "inline_snippet",
                        "language": lang,
                        "content": code_text.strip()
                    })
                    context_data["language"] = lang

        return context_data

    def _assemble_prompt(self, task: AgentTask, context_data: Dict[str, Any]) -> str:
        """Constructs the prompt for Eagle analysis."""
        prompt_parts = []

        prompt_parts.append(f"Student Request:\n{task.prompt}\n")

        if context_data["documents"]:
            prompt_parts.append("=== EXTRACTED DOCUMENTS ===")
            for doc in context_data["documents"]:
                prompt_parts.append(f"Document ({doc['type']}): {doc['path']}\n{doc['summary']}\n")

        if context_data["code_snippets"]:
            prompt_parts.append("=== ATTACHED CODE SNIPPETS ===")
            for snippet in context_data["code_snippets"]:
                prompt_parts.append(f"File: {snippet['path']} ({snippet['language']})\n```{snippet['language']}\n{snippet['content']}\n```\n")

        if context_data["workspace_summary"]:
            prompt_parts.append("=== CURRENT WORKSPACE CONTEXT ===")
            prompt_parts.append(context_data["workspace_summary"])

        prompt_parts.append(
            "\nProvide a clear, student-friendly explanation, highlight any errors, why they occur, and provide the complete corrected code. "
            "CRITICAL: If you are fixing a file or providing a solution, always provide the 100% complete corrected file using: `### FILE: <filename>` followed by the code block so it can be saved to disk!"
        )

        return "\n".join(prompt_parts)

    def _apply_autofixes_to_disk(self, text: str, target_folder: str, primary_file: Optional[str] = None) -> List[AgentArtifact]:
        """Extracts corrected code blocks from Eagle's response and writes them directly to disk."""
        written_artifacts = []
        target_dir = target_folder or file_tools.get_workspace_root()

        # 1. Multi-file blocks: ### FILE: filename
        file_blocks = extract_multi_file_blocks(text)
        
        # 2. If no multi-file blocks, but there is a clear single code block and a known target file being fixed
        if not file_blocks and primary_file and ("```" in text or "fix" in text.lower()):
            code = extract_code_block(text)
            if code and len(code.strip().splitlines()) >= 2:
                # Check if it looks like actual code
                file_blocks[os.path.basename(primary_file)] = code

        for filename, code_content in file_blocks.items():
            if not code_content.strip():
                continue
            
            # Syntax validation if python
            if filename.endswith(".py"):
                try:
                    ast.parse(code_content)
                except SyntaxError:
                    pass  # Write anyway or let user inspect

            res = file_tools.write_file(filename, code_content, folder=target_dir)
            if res.get("status") == "success":
                written_artifacts.append(AgentArtifact(
                    artifact_type="file",
                    title=filename,
                    content=code_content,
                    file_path=res.get("full_path") or res.get("path") or filename,
                    metadata={"lines": res.get("lines", 0), "bytes": res.get("bytes", 0)}
                ))

        if written_artifacts:
            try:
                self.indexer.reindex()
            except Exception:
                pass

        return written_artifacts

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Non-streaming execution."""
        is_vision = bool(task.images) or "debug screen" in task.prompt.lower()
        if is_vision:
            return await self.vision_debug(task)

        context_data = self._build_analysis_context(task)
        full_user_prompt = self._assemble_prompt(task, context_data)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]

        response_text = await self._call_ollama_complete(messages)

        artifacts = []
        # Parse potential DebugCard
        try:
            card = self.vision_debugger._parse_debug_card_from_llm(
                response_text,
                fallback_code=context_data["code_snippets"][0]["content"] if context_data["code_snippets"] else ""
            )
            if card and card.bug_title and card.bug_title != "Error Analysis":
                artifact = AgentArtifact(
                    artifact_type="debug_card",
                    title=card.bug_title,
                    content=json.dumps(card.to_dict()),
                    metadata={"severity": card.severity, "language": context_data["language"]}
                )
                artifacts.append(artifact)
        except Exception:
            pass

        # Apply autofixes to disk
        written_files = self._apply_autofixes_to_disk(
            response_text,
            task.target_folder,
            primary_file=context_data.get("primary_file")
        )
        artifacts.extend(written_files)

        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            artifacts=artifacts
        )

    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming execution yielding tokens, live code fixes to disk, and structured artifacts."""
        yield {"type": "state", "mascot_state": "analyzing"}

        is_vision = bool(task.images) or "debug screen" in task.prompt.lower()
        if is_vision:
            yield {"type": "token", "content": "🔍 Eagle Agent is analyzing screen and image perception...\n\n"}
            resp = await self.vision_debug(task)
            yield {"type": "token", "content": resp.content}
            for art in resp.artifacts:
                yield {"type": "artifact", "artifact": art.to_dict()}
            yield {"type": "state", "mascot_state": "idle"}
            return

        context_data = self._build_analysis_context(task)
        full_user_prompt = self._assemble_prompt(task, context_data)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]

        full_response = ""
        try:
            async for token in self._stream_ollama_tokens(messages):
                full_response += token
                yield {"type": "token", "content": token}
        except Exception as ex:
            err_msg = f"Eagle Agent encountered an error communicating with Ollama: {ex}"
            full_response = err_msg
            yield {"type": "token", "content": err_msg}

        # 1. Check if response contains a structured DebugCard to render in UI
        try:
            card = self.vision_debugger._parse_debug_card_from_llm(
                full_response,
                fallback_code=context_data["code_snippets"][0]["content"] if context_data["code_snippets"] else ""
            )
            if card and card.bug_title and card.bug_title != "Error Analysis":
                artifact = AgentArtifact(
                    artifact_type="debug_card",
                    title=card.bug_title,
                    content=json.dumps(card.to_dict()),
                    metadata={"severity": card.severity, "language": context_data["language"]}
                )
                yield {"type": "artifact", "artifact": artifact.to_dict()}
        except Exception:
            pass

        # 2. AUTO-FIX DISK APPLICATION: Write corrected files directly to disk!
        written_files = self._apply_autofixes_to_disk(
            full_response,
            task.target_folder,
            primary_file=context_data.get("primary_file")
        )

        for art in written_files:
            yield {
                "type": "execution_log",
                "mascot_state": "executing",
                "command": f"eagle_autofix('{art.title}')",
                "output": f"✓ Corrected code written to disk ({art.metadata.get('lines', 0)} lines)"
            }
            yield {
                "type": "token",
                "content": f"\n\n💾 **[EAGLE AUTO-FIX APPLIED]**: Successfully patched `{art.title}` on disk!\n"
            }
            yield {
                "type": "artifact",
                "artifact": art.to_dict()
            }

        yield {"type": "state", "mascot_state": "idle"}

    async def analyze_code(self, code: str, language: str, file_path: str = "") -> AgentResponse:
        """Dedicated code analysis."""
        if language.lower() in ['python', 'py']:
            try:
                ast.parse(code)
            except SyntaxError:
                pass

        prompt = f"Please analyze this {language} code for issues, logic bugs, style, and potential improvements:\n\n```{language}\n{code}\n```"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response_text = await self._call_ollama_complete(messages)
        card = self.vision_debugger._parse_debug_card_from_llm(response_text, fallback_code=code)
        if file_path:
            card.file_path = file_path
            
        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            file_path=file_path,
            metadata={"severity": card.severity, "language": language}
        )
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            artifacts=[artifact]
        )

    async def analyze_document(self, file_path: str, query: str = "") -> AgentResponse:
        """Dedicated document extraction and analysis."""
        summary_result = extract_document_summary(file_path)
        if summary_result.get('status') == 'error':
            return AgentResponse(
                agent_name=self.name,
                content=f"Could not read the document: {summary_result.get('message')}"
            )

        summary_text = summary_result.get('summary_text', '')
        prompt = f"Document content from {os.path.basename(file_path)}:\n\n{summary_text}\n\n"
        if query:
            prompt += f"Student Question: '{query}'\nPlease answer clearly and educationally based on the document."
        else:
            prompt += "Please provide a clear, educational summary of this document."

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response_text = await self._call_ollama_complete(messages)
        return AgentResponse(
            agent_name=self.name,
            content=response_text
        )

    async def vision_debug(self, task: AgentTask) -> AgentResponse:
        """Performs vision-based diagnosis of screenshots or images."""
        if task.images:
            card = await self.vision_debugger.analyze_image(task.images[0], code_context=task.prompt)
        else:
            card = await self.vision_debugger.capture_and_analyze(code_context=task.prompt)

        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            metadata={"severity": card.severity, "language": card.language}
        )
        
        return AgentResponse(
            agent_name=self.name,
            content=f"### 🦅 Eagle Vision Diagnostics\n\n**Issue Detected:** {card.bug_title}\n\n{card.what_happened}\n\n**Why it happened:** {card.why_it_happened}",
            artifacts=[artifact]
        )

    async def debug_and_fix(self, code: str, error: str, language: str) -> AgentResponse:
        """Debugs a specific error message and code snippet."""
        card = await self.vision_debugger.analyze_code_for_bugs(code, error, language)
        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            metadata={"severity": card.severity, "language": language}
        )
        return AgentResponse(
            agent_name=self.name,
            content=f"### 🦅 Eagle Debug Analysis\n\n**{card.bug_title}**\n\n{card.what_happened}\n\n**Fix Recommendation:**\n{card.why_it_happened}",
            artifacts=[artifact]
        )
