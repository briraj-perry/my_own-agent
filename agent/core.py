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

def extract_filename_from_prompt(query: str) -> Optional[str]:
    """Extracts explicit filename from user query (e.g. test.py, notes.md, index.html)."""
    match = re.search(r'[\'"]?([a-zA-Z0-9_\-\/\\]+\.(py|js|html|css|json|md|txt|cpp|c|sh|ps1))[\'"]?', query, re.IGNORECASE)
    if match:
        filename = match.group(1).strip('\'"')
        return filename
    return None

def extract_code_block(text: str) -> str:
    """Extracts clean code contained inside markdown code blocks ``` ... ```."""
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            block = parts[1].strip()
            lines = block.splitlines()
            if lines and lines[0].strip().isalnum():
                return "\n".join(lines[1:]).strip()
            return block
    return text.strip()





class NeoAgentCore:
    """High-Performance Core Agent Engine with instant streaming, physical disk writing & RAG re-indexing."""
    
    OLLAMA_BASE_URL = "http://localhost:11434"
    VISION_MODEL = "gemma4:12b"

    def __init__(self):
        self.active_model = "qwen2.5-coder:14b"
        self.pending_permissions: Dict[str, asyncio.Future] = {}
        self.screen_engine = ScreenPerceptionEngine()
        self.indexer = CodebaseIndexer()

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

    def is_ollama_running(self) -> bool:
        """Checks if local Ollama service is listening at port 11434."""
        try:
            req = urllib.request.Request(f"{self.OLLAMA_BASE_URL}/api/version")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    async def stream_response(self, user_query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """High-speed real-time response streaming with physical disk creation and permission management."""
        loop = asyncio.get_running_loop()
        
        # 1. State: Thinking
        yield {
            "type": "state",
            "mascot_state": "thinking",
            "status": "Analyzing prompt & workspace tools...",
            "step": "plan"
        }
        await asyncio.sleep(0.1)

        query_lower = user_query.lower()
        screen_context = ""
        captured_image_b64 = None
        target_llm_model = self.active_model

        # Check for explicit screen perception request
        EXPLICIT_VISION_PHRASES = [
            "look at my screen", "see my screen", "check my screen", 
            "what is on my screen", "read my screen", "analyze my screen", 
            "take a screenshot", "look at screen"
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

        # Detect filesystem / code execution intent
        is_folder_creation = any(k in query_lower for k in ["create folder", "make folder", "create directory", "mkdir"])
        
        is_explicit_note = any(k in query_lower for k in ["write note", "create note", "take note", "save note"]) or (target_filename and target_filename.endswith(".md"))
        is_explicit_file = (target_filename is not None and not target_filename.endswith(".md")) or any(k in query_lower for k in ["create file", "write file", "make file", "save file", "write python", "script", "code for", "file named"])

        if is_explicit_file:
            is_file_writing = True
            is_note_writing = False
        elif is_explicit_note:
            is_note_writing = True
            is_file_writing = False
        else:
            is_file_writing = False
            is_note_writing = False

        is_file_reading = any(k in query_lower for k in ["read file", "open file", "view file", "cat file"])
        is_code_execution = any(k in query_lower for k in ["run code", "execute", "run python", "run script", "bash", "powershell"])


        needs_permission = is_folder_creation or is_note_writing or is_file_writing or is_file_reading or is_code_execution

        permission_approved = True

        if needs_permission:
            perm_id = str(uuid.uuid4())[:8]

            if is_folder_creation:
                title = "Permission Required: Create Folder"
                action_desc = f"Create a new directory in workspace for: '{user_query}'"
                cmd_desc = "file_tools.create_directory(path)"
            elif is_note_writing:
                target_name = target_filename or "note.md"
                title = "Permission Required: Write Note"
                action_desc = f"Create note '{target_name}' in notes folder"
                cmd_desc = f"file_tools.write_note('{target_name}')"
            elif is_file_writing:
                target_name = target_filename or "script.py"
                title = "Permission Required: Write File"
                action_desc = f"Write file '{target_name}' in workspace"
                cmd_desc = f"file_tools.write_file('{target_name}')"
            elif is_file_reading:
                title = "Permission Required: Read File"
                action_desc = f"Read workspace file for: '{user_query}'"
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
                permission_approved = await asyncio.wait_for(future, timeout=120.0)
            except asyncio.TimeoutError:
                permission_approved = False
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
            res = file_tools.create_directory(folder_name)
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

        system_prompt = (
            "You are Neo, a local AI Personal Agent for coding and general knowledge running locally on the user's computer.\n\n"
            "CRITICAL OUTPUT RULE: Be extremely CONCISE, crisp, and direct. Do NOT output long unnecessary speeches or multi-page fluff.\n"
            "CRITICAL PERMISSION RULE: DO NOT write text questions asking for permission in the chat. Interactive buttons ([Accept & Create File] / [Deny]) are automatically rendered in the user interface for the user to click.\n\n"
            "WHEN WRITING CODE OR FILES: Output complete, production-ready code inside standard markdown code blocks (```python ... ``` or ```js ... ```).\n\n"
            "AVAILABLE TOOLS:\n"
            "- FOLDER CREATION: Can create single or nested folders via create_directory(path).\n"
            "- FILE WRITING: Can write source code and files via write_file(path, content).\n"
            "- NOTE WRITING: Can create Markdown notes via write_note(title, content).\n"
            "- FILE READING: Can read files via read_file(path).\n"
            "- CODE EXECUTION: Can execute python/powershell scripts via execute_code(code).\n"
            "- SELF-CORRECTION: Automatically diagnose stack traces and auto-repair broken code.\n"
            "- WEB SEARCH: Retrieve real-time information for general knowledge.\n"
            "- RAG MEMORY: Search local repository files & past conversation context.\n"
            + screen_context
        )

        user_message_obj = {"role": "user", "content": user_query}
        if captured_image_b64:
            user_message_obj["images"] = [captured_image_b64]

        chat_payload = {
            "model": target_llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                user_message_obj
            ],
            "options": {
                "num_ctx": 4096,
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

            # Physically write file or note to disk if user requested writing and permission was approved
            if (is_file_writing or is_note_writing) and permission_approved:
                extracted_code = extract_code_block(full_streamed_response)
                
                if is_note_writing:
                    save_title = target_filename or "neo_note.md"
                    res = file_tools.write_note(save_title, full_streamed_response, folder="notes")
                else:
                    save_path = target_filename or "script.py"
                    res = file_tools.write_file(save_path, extracted_code)

                if res.get("status") == "success":
                    yield {
                        "type": "execution_log",
                        "mascot_state": "executing",
                        "command": f"physical_disk_write('{res.get('path')}')",
                        "output": f"✓ {res.get('message')}\nFull Path: {res.get('full_path')}"
                    }
                    yield {
                        "type": "token", 
                        "content": f"\n\n💾 **Physically Written to Disk**: `{res.get('path')}` ({res.get('lines')} lines, {res.get('bytes')} bytes)\nLocation: `{res.get('full_path')}`\n"
                    }
                    # Update workspace indexer so it shows up in Workspace Explorer immediately!
                    self.indexer.reindex()

        except Exception as e:
            yield {
                "type": "token",
                "content": f"\n\n❌ **Ollama Stream Error**: {str(e)}\nMake sure model `{target_llm_model}` is pulled (`ollama pull {target_llm_model}`)."
            }

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
