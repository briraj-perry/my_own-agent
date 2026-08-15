import json
import re
import urllib.request
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from config import settings
from tools.screen_perception import ScreenPerceptionEngine

@dataclass
class DebugCard:
    """Student-friendly bug explanation card.
    
    This structured output is rendered as a styled card in the UI,
    making debugging educational rather than frustrating.
    """
    bug_title: str
    severity: str
    what_happened: str
    why_it_happened: str
    code_before: str
    code_after: str
    pro_tip: str
    related_concepts: List[str]
    file_path: str = ""
    language: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bug_title": self.bug_title,
            "severity": self.severity,
            "what_happened": self.what_happened,
            "why_it_happened": self.why_it_happened,
            "code_before": self.code_before,
            "code_after": self.code_after,
            "pro_tip": self.pro_tip,
            "related_concepts": self.related_concepts,
            "file_path": self.file_path,
            "language": self.language
        }

    def to_markdown(self) -> str:
        lang = self.language or ""
        tags = ", ".join(f"`{concept}`" for concept in self.related_concepts)
        file_info = f"\n**File:** `{self.file_path}`" if self.file_path else ""
        return f"""### 🐛 {self.bug_title}
**Severity:** {self.severity}

**What Happened:**
{self.what_happened}

**Why It Happened (The 'Ah-ha!' Moment):**
{self.why_it_happened}

**Code Before (The Bug):**
```{lang}
{self.code_before}
```

**Code After (The Fix):**
```{lang}
{self.code_after}
```

**💡 Pro Tip:** {self.pro_tip}

**Related Concepts:** {tags}{file_info}
"""


class VisionDebugger:
    """Captures screenshots and generates educational debug cards using vision LLM."""
    
    def __init__(self):
        self.screen_engine = ScreenPerceptionEngine()
        self.ollama_url = getattr(settings, 'ollama_base_url', 'http://127.0.0.1:11434')
        self.vision_model = 'gemma4:12b'
        self.text_model = getattr(settings, 'primary_model', 'gemma4:12b')
    
    async def _call_ollama(self, prompt: str, model: str, images: Optional[List[str]] = None) -> str:
        loop = asyncio.get_running_loop()
        
        url = f"{self.ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        if images:
            payload["images"] = images
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
        
        def fetch():
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_body = response.read().decode('utf-8')
                    res_json = json.loads(res_body)
                    return res_json.get("response", "")
            except Exception as e:
                return f"Error connecting to Ollama: {str(e)}"
        
        return await loop.run_in_executor(None, fetch)

    def _get_system_prompt(self, context_type: str = "visual") -> str:
        return f"""You are an expert, friendly mentor helping a student debug their {context_type} issue.
You MUST respond with ONLY a valid JSON object. Do not include markdown codeblocks around the JSON.
Do not include any introductory or concluding text.

The JSON MUST have the following keys exactly:
- "bug_title": A short, catchy title for the bug.
- "severity": Choose from "🟢 Minor", "🟡 Moderate", or "🔴 Critical".
- "what_happened": A plain English explanation of the issue.
- "why_it_happened": An educational explanation of the underlying cause.
- "code_before": The buggy code snippet.
- "code_after": The fixed code snippet.
- "pro_tip": A short, practical tip to avoid this in the future.
- "related_concepts": A list of strings (e.g. ["CSS Flexbox", "overflow", "responsive-design"]).
- "file_path": The name of the file if known, else an empty string.
- "language": The primary programming language (e.g., "python", "javascript", "css", "html").
"""

    async def capture_and_analyze(self, code_context: str = "", window_title: Optional[str] = None) -> DebugCard:
        """Full pipeline: capture screen → send to vision LLM → parse into DebugCard.
        
        Args:
            code_context: Optional source code from the active project for more accurate diagnosis.
            window_title: Optional specific window to capture.
        """
        capture_result = self.screen_engine.capture_screen()
        
        if capture_result.get("status") != "success":
            return self._create_error_card(
                f"Could not capture the screen. Error: {capture_result.get('error', 'Unknown error')}"
            )
            
        b64_image = capture_result.get("image_b64")
        if not b64_image:
            return self._create_error_card("No image data found in screen capture.")
             
        prompt = self._get_system_prompt("UI/visual")
        prompt += "\n\nPlease analyze the provided screenshot to find the bug."
        if code_context:
            prompt += f"\n\nHere is the relevant code context:\n```\n{code_context}\n```"
            
        llm_response = await self._call_ollama(prompt, model=self.vision_model, images=[b64_image])
        
        if llm_response.startswith("Error connecting to Ollama"):
            return self._create_error_card(llm_response)
            
        return self._parse_debug_card_from_llm(llm_response, fallback_code=code_context)
    
    async def analyze_image(self, image_path: str, code_context: str = "") -> DebugCard:
        """Analyze a provided screenshot/image (not live capture)."""
        import base64
        import os
        
        if not os.path.exists(image_path):
            return self._create_error_card(f"Image not found at path: {image_path}")
            
        try:
            with open(image_path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return self._create_error_card(f"Could not read image: {str(e)}")
            
        prompt = self._get_system_prompt("UI/visual")
        prompt += "\n\nPlease analyze the provided screenshot to find the bug."
        if code_context:
            prompt += f"\n\nHere is the relevant code context:\n```\n{code_context}\n```"
            
        llm_response = await self._call_ollama(prompt, model=self.vision_model, images=[b64_image])
        
        if llm_response.startswith("Error connecting to Ollama"):
            return self._create_error_card(llm_response)
            
        return self._parse_debug_card_from_llm(llm_response, fallback_code=code_context)
    
    async def analyze_code_for_bugs(self, code: str, error_message: str = "", language: str = "python") -> DebugCard:
        """Analyze code text (no screenshot) and generate a DebugCard.
        This is used when the student pastes code with an error."""
        
        prompt = self._get_system_prompt("code")
        prompt += f"\n\nPlease analyze the following {language} code for bugs."
        prompt += f"\n\nCode:\n```\n{code}\n```"
        if error_message:
            prompt += f"\n\nError Message:\n```\n{error_message}\n```"
            
        llm_response = await self._call_ollama(prompt, model=self.text_model)
        
        if llm_response.startswith("Error connecting to Ollama"):
            return self._create_error_card(llm_response)
            
        return self._parse_debug_card_from_llm(llm_response, fallback_code=code)
    
    def _create_error_card(self, msg: str) -> DebugCard:
        return DebugCard(
            bug_title="Analysis Failed",
            severity="🟡 Moderate",
            what_happened=msg,
            why_it_happened="An internal error prevented the analysis from completing. We couldn't reach the AI model or capture the screen.",
            code_before="",
            code_after="",
            pro_tip="Try restarting the Neo Mascot or checking if Ollama is running.",
            related_concepts=["Debugging Tools", "System Processes"],
            file_path="",
            language=""
        )
        
    def _parse_debug_card_from_llm(self, llm_response: str, fallback_code: str = "") -> DebugCard:
        """Parse structured LLM response into a DebugCard dataclass.
        The LLM is prompted to return JSON, but we handle malformed responses gracefully."""
        
        # Try extracting JSON block if there is extra text
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        json_str = json_match.group(0) if json_match else llm_response
        
        try:
            data = json.loads(json_str)
            return DebugCard(
                bug_title=data.get("bug_title", "Unknown Bug"),
                severity=data.get("severity", "🟡 Moderate"),
                what_happened=data.get("what_happened", "Could not determine what happened."),
                why_it_happened=data.get("why_it_happened", "Could not determine why it happened."),
                code_before=data.get("code_before", fallback_code),
                code_after=data.get("code_after", ""),
                pro_tip=data.get("pro_tip", "Keep coding! You'll figure it out."),
                related_concepts=data.get("related_concepts", []),
                file_path=data.get("file_path", ""),
                language=data.get("language", "")
            )
        except json.JSONDecodeError:
            # Fallback regex extraction if JSON decoding fails
            bug_title = self._extract_regex(r'"bug_title"\s*:\s*"(.*?)"', llm_response, "Unknown Bug")
            severity = self._extract_regex(r'"severity"\s*:\s*"(.*?)"', llm_response, "🟡 Moderate")
            what = self._extract_regex(r'"what_happened"\s*:\s*"(.*?)"', llm_response, "Could not determine what happened.")
            why = self._extract_regex(r'"why_it_happened"\s*:\s*"(.*?)"', llm_response, "Could not determine why it happened.")
            code_before = self._extract_regex(r'"code_before"\s*:\s*"(.*?)"', llm_response, fallback_code)
            code_after = self._extract_regex(r'"code_after"\s*:\s*"(.*?)"', llm_response, "")
            pro_tip = self._extract_regex(r'"pro_tip"\s*:\s*"(.*?)"', llm_response, "Keep coding! You'll figure it out.")
            
            concepts_match = re.search(r'"related_concepts"\s*:\s*\[(.*?)\]', llm_response, re.DOTALL)
            related_concepts = []
            if concepts_match:
                concepts_str = concepts_match.group(1)
                related_concepts = [c.strip(' "\'\n\r') for c in concepts_str.split(',')]
                # Filter out empties
                related_concepts = [c for c in related_concepts if c]
            
            file_path = self._extract_regex(r'"file_path"\s*:\s*"(.*?)"', llm_response, "")
            language = self._extract_regex(r'"language"\s*:\s*"(.*?)"', llm_response, "")
            
            return DebugCard(
                bug_title=bug_title,
                severity=severity,
                what_happened=what,
                why_it_happened=why,
                code_before=code_before,
                code_after=code_after,
                pro_tip=pro_tip,
                related_concepts=related_concepts,
                file_path=file_path,
                language=language
            )

    def _extract_regex(self, pattern: str, text: str, default: str) -> str:
        # Avoid greedy match on quotes by using .*?
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            # Replace escaped newlines if any to format correctly
            return match.group(1).replace('\\n', '\n').strip()
        return default
