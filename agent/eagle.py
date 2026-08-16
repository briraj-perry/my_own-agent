"""Eagle Agent — Autonomous Full-Folder Code Auditor, Auto-Repair Sentinel & Application Reviewer.

Eagle Agent is responsible for Stage 3 (Checking & Auto-Repair) and Stage 4 (Application Review) in the pipeline:
1. Implementation Plan
2. Specialist Coding
3. Eagle Agent Check & Fix (Cross-file ID validation, syntax repair, disk write)
4. Comprehensive App Review (What was fixed, architecture overview, how the app functions)
"""

import os
import re
import json
import asyncio
import urllib.request
from typing import Dict, Any, List, Optional, AsyncGenerator

from tools import file_tools, code_executor
from agent.prompts import EAGLE_AGENT_SYSTEM_PROMPT, sanitize_code_content


def extract_eagle_fixes(text: str) -> Dict[str, str]:
    """Extracts all corrected files from Eagle Agent output.
    
    Supports:
      ### FIX_FILE: filename.ext
      ### FILE: filename.ext
      --- FILE: filename.ext
    """
    files: Dict[str, str] = {}
    pattern = re.compile(
        r'(?:###\s*(?:FIX_)?FILE:\s*|---\s*(?:FIX_)?FILE:\s*|\/\/\s*(?:FIX_)?FILE:\s*|#\s*(?:FIX_)?FILE:\s*)'
        r'([a-zA-Z0-9_\-\/\\.]+\.(?:html|css|jsx?|tsx?|json|py|pyw|md|mjs|cjs|txt|cpp|c|sh|ps1))'
        r'[\s\-\*\/]*\n'
        r'(?:```[a-zA-Z]*\n)?'
        r'(.*?)'
        r'(?:\n```|\n(?=###|\/\/\s*(?:FIX_)?FILE|#\s*(?:FIX_)?FILE|---\s*(?:FIX_)?FILE)|$)',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        filename = match.group(1).strip()
        raw_code = match.group(2)
        content = sanitize_code_content(raw_code) if callable(sanitize_code_content) else raw_code.strip()
        files[filename] = content
    return files


class EagleAgentEngine:
    """Specialized engine for deep whole-folder inspection, syntax/linkage verification, auto-repair, and app review."""

    OLLAMA_BASE_URL = "http://localhost:11434"

    def __init__(self, default_model: str = "gemma4:26b"):
        self.default_model = default_model

    def is_ollama_running(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.OLLAMA_BASE_URL}/api/version")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def perform_static_precheck(self, folder_path: str = ".") -> Dict[str, Any]:
        """Performs fast heuristic and AST pre-checks across all code files in folder."""
        code_files = file_tools.get_folder_code_files(folder_path)
        issues = []
        html_button_ids = set()
        js_listeners = set()
        html_classes = set()
        css_classes = set()

        for cf in code_files:
            rel = cf["rel_path"]
            f_res = file_tools.read_file(rel, folder=folder_path)
            if f_res.get("status") != "success" or not f_res.get("content"):
                continue
            content = f_res["content"]

            # 1. Python AST check
            if cf.get("is_python") or rel.endswith((".py", ".pyw")):
                ast_check = code_executor.validate_python_syntax(content)
                if not ast_check.get("valid", True):
                    issues.append({
                        "file": rel,
                        "type": "python_syntax_error",
                        "detail": ast_check.get("error", "Syntax error")
                    })

            # 2. Extract HTML button IDs and classes
            if rel.endswith((".html", ".htm")):
                # Extract button/input/element IDs
                for m in re.finditer(r'<[a-zA-Z0-9_\-]+[^>]*\bid=[\'"]([a-zA-Z0-9_\-]+)[\'"]', content, re.IGNORECASE):
                    html_button_ids.add(m.group(1))
                # Extract classes
                for m in re.finditer(r'\bclass=[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE):
                    for cls in m.group(1).split():
                        html_classes.add(cls.strip())

            # 3. Extract JS addEventListener targets and getElementById
            if rel.endswith((".js", ".jsx", ".ts", ".tsx")):
                for m in re.finditer(r'getElementById\([\'"]([a-zA-Z0-9_\-]+)[\'"]\)', content):
                    js_listeners.add(m.group(1))
                for m in re.finditer(r'querySelector\([\'"]#([a-zA-Z0-9_\-]+)[\'"]\)', content):
                    js_listeners.add(m.group(1))

            # 4. Extract CSS classes
            if rel.endswith(".css"):
                for m in re.finditer(r'\.([a-zA-Z0-9_\-]+)\s*[\{,:]', content):
                    css_classes.add(m.group(1))

        # Check for HTML button IDs that lack JS handlers
        unhandled_ids = [btn_id for btn_id in html_button_ids if btn_id not in js_listeners and ("btn" in btn_id.lower() or "button" in btn_id.lower() or "action" in btn_id.lower())]
        if unhandled_ids:
            issues.append({
                "file": "script.js / index.html",
                "type": "unhandled_button_ids",
                "detail": f"Interactive HTML element ID(s) without matching JS handlers: {', '.join(unhandled_ids[:8])}"
            })

        return {
            "files_scanned": len(code_files),
            "html_button_ids": list(html_button_ids),
            "js_listeners": list(js_listeners),
            "detected_issues": issues
        }

    async def audit_and_repair_folder(
        self,
        folder_path: str = ".",
        model: Optional[str] = None,
        upstream_plan: Optional[str] = None
    ) -> Dict[str, Any]:
        """Audits all files in folder, prompts Eagle Agent LLM to repair mistakes, writes fixes to disk, and generates review."""
        loop = asyncio.get_running_loop()
        target_model = model or self.default_model

        code_files = file_tools.get_folder_code_files(folder_path)
        if not code_files:
            return {
                "status": "clean",
                "folder": folder_path,
                "fixed_files": [],
                "message": f"🦅 Eagle Agent: No source code files found in '{folder_path}' to audit.",
                "review": "No code files present."
            }

        # Gather all file contents
        files_data = []
        for cf in code_files:
            f_res = file_tools.read_file(cf["rel_path"], folder=folder_path)
            if f_res.get("status") == "success":
                content_snip = f_res.get("content", "")
                files_data.append(f"=== FILE: {cf['rel_path']} (Type: {cf['ext']}) ===\n{content_snip}\n")

        combined_code = "\n\n".join(files_data)
        precheck = self.perform_static_precheck(folder_path)
        precheck_text = ""
        if precheck.get("detected_issues"):
            precheck_text = "\n[EAGLE STATIC PRE-CHECK FINDINGS]:\n" + "\n".join(
                f"- [{iss['type']}] in {iss['file']}: {iss['detail']}" for iss in precheck["detected_issues"]
            )

        if not self.is_ollama_running():
            return {
                "status": "error",
                "folder": folder_path,
                "fixed_files": [],
                "message": "🦅 Eagle Agent: Local Ollama service is offline.",
                "review": "Ollama service unavailable."
            }

        plan_context = f"\n[ORIGINAL IMPLEMENTATION PLAN]:\n{upstream_plan}\n" if upstream_plan else ""

        user_prompt = (
            f"Audit and verify the full application in folder '{folder_path}' ({len(code_files)} files total).\n"
            f"{plan_context}\n"
            f"{precheck_text}\n\n"
            f"[WORKSPACE CODEBASE CONTENT]:\n"
            f"{combined_code}\n\n"
            "Follow your system instructions: pinpoint any mistakes, output fixed files with `### FIX_FILE: filename`, and provide a comprehensive final review of the application!"
        )

        try:
            req = urllib.request.Request(
                f"{self.OLLAMA_BASE_URL}/api/chat",
                data=json.dumps({
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": EAGLE_AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "options": {"num_ctx": 8192, "num_predict": 4096, "temperature": 0.15},
                    "stream": False
                }).encode('utf-8'),
                headers={"Content-Type": "application/json"}
            )

            def call_llm():
                with urllib.request.urlopen(req, timeout=90.0) as res:
                    return json.loads(res.read().decode('utf-8'))

            resp = await loop.run_in_executor(None, call_llm)
            analysis_text = resp.get("message", {}).get("content", "").strip()

            # Extract and write repaired files
            fixes = extract_eagle_fixes(analysis_text)
            fixed_file_records = []

            for fix_name, fix_content in fixes.items():
                if len(fix_content.strip()) > 10:
                    write_res = file_tools.write_file(fix_name, fix_content, folder=folder_path)
                    if write_res.get("status") == "success":
                        fixed_file_records.append({
                            "file": fix_name,
                            "path": write_res.get("path"),
                            "full_path": write_res.get("full_path"),
                            "lines": write_res.get("lines")
                        })

            return {
                "status": "success",
                "folder": folder_path,
                "fixed_files": fixed_file_records,
                "analysis": analysis_text,
                "message": (
                    f"🦅 Eagle Agent Audit Complete: Repaired {len(fixed_file_records)} file(s) on disk."
                    if fixed_file_records else
                    f"🦅 Eagle Agent Audit Complete: 0 critical errors found in {len(code_files)} file(s)."
                )
            }

        except Exception as e:
            return {
                "status": "error",
                "folder": folder_path,
                "fixed_files": [],
                "message": f"🦅 Eagle Agent Error: {str(e)}",
                "review": f"Audit failed: {str(e)}"
            }
