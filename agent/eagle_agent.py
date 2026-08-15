import json
import ast
from typing import AsyncGenerator, Dict, Any

from agent.base_agent import BaseAgent, AgentName, AgentTask, AgentResponse, AgentArtifact
from agent.prompts import EAGLE_SYSTEM_PROMPT
from tools.document_tools import detect_document_type, extract_document_summary, read_code_file
from tools.vision_debugger import VisionDebugger, DebugCard

class EagleAgent(BaseAgent):
    name = AgentName.EAGLE
    description = "Code analysis, document parsing, bug fixing, and vision debugging"

    def __init__(self):
        super().__init__()
        self.system_prompt = EAGLE_SYSTEM_PROMPT
        self.vision_debugger = VisionDebugger()

    async def execute(self, task: AgentTask) -> AgentResponse:
        # Detect task type from context/files:
        is_vision = bool(task.images) or "debug screen" in task.prompt.lower()
        if is_vision:
            return await self.vision_debug(task)

        if task.files:
            file_path = task.files[0]
            file_type = detect_document_type(file_path)
            
            if file_type == 'code':
                code_res = read_code_file(file_path)
                if code_res.get('status') == 'error':
                    return AgentResponse(agent_name=self.name, content=f"Error reading file: {code_res.get('message')}")
                
                code = code_res.get('content', '')
                lang = code_res.get('language', 'python')
                
                # Check for errors/bugs in prompt
                if "error" in task.prompt.lower() or "exception" in task.prompt.lower() or "bug" in task.prompt.lower():
                    return await self.debug_and_fix(code, task.prompt, lang)
                else:
                    return await self.analyze_code(code, lang, file_path)
                    
            elif file_type in ['pdf', 'pptx', 'xlsx', 'csv']:
                return await self.analyze_document(file_path, task.prompt)
            else:
                return AgentResponse(agent_name=self.name, content="Unsupported file type for analysis.")

        # Fallback: Check if there's inline code in the prompt
        if "```" in task.prompt:
            parts = task.prompt.split("```")
            if len(parts) >= 3:
                code_block = parts[1]
                if "\n" in code_block:
                    lang_line, code_content = code_block.split("\n", 1)
                    lang = lang_line.strip() or "python"
                else:
                    lang = "python"
                    code_content = code_block
                return await self.analyze_code(code_content, lang)

        return AgentResponse(
            agent_name=self.name,
            content="Please provide a code snippet, attach an image, or upload a document file (PDF/PPTX/XLSX) for me to analyze!"
        )

    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        # Yield state transition
        yield {"type": "state", "mascot_state": "analyzing"}
        
        # Execute fully (non-streaming inner task for this agent's structure)
        response = await self.execute(task)
        
        # Stream out the text content
        yield {"type": "token", "content": response.content}
        
        # Stream out any structured artifacts (e.g. DebugCard)
        for artifact in response.artifacts:
            yield {"type": "artifact", "artifact": artifact.to_dict()}
            
        # Return to idle state
        yield {"type": "state", "mascot_state": "idle"}

    async def analyze_code(self, code: str, language: str, file_path: str = "") -> AgentResponse:
        # Perform structural AST parsing if python
        if language.lower() in ['python', 'py']:
            try:
                ast.parse(code)
            except SyntaxError as e:
                pass  # We let the LLM explain the syntax error to the student

        prompt = f"Please analyze this {language} code for issues, style, and potential improvements:\n\n```\n{code}\n```"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Call Ollama for code analysis
        response_text = await self._call_ollama_complete(messages)

        # Parse LLM response into a DebugCard
        card = self.vision_debugger._parse_debug_card_from_llm(response_text, fallback_code=code)
        if file_path:
            card.file_path = file_path
            
        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            file_path=file_path,
            metadata={"language": language}
        )
        
        return AgentResponse(
            agent_name=self.name,
            content="I've carefully analyzed your code and prepared a DebugCard with my findings. Let me know if you want to dive deeper into any of the concepts!",
            artifacts=[artifact]
        )

    async def analyze_document(self, file_path: str, query: str = "") -> AgentResponse:
        # Extract content using the document tools
        summary_result = extract_document_summary(file_path)
        if summary_result.get('status') == 'error':
            return AgentResponse(
                agent_name=self.name,
                content=f"Oops! I couldn't read the document: {summary_result.get('message')}"
            )

        summary_text = summary_result.get('summary_text', '')
        prompt = f"Here is the content extracted from the document:\n\n{summary_text}\n\n"
        
        if query:
            prompt += f"The user asked: '{query}'\nPlease answer clearly and educationally based on the document content."
        else:
            prompt += "Please provide a clear, educational, and structured summary of this document."

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Call LLM for document summary/Q&A
        response_text = await self._call_ollama_complete(messages)
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text
        )

    async def vision_debug(self, task: AgentTask) -> AgentResponse:
        if task.images:
            # Analyze provided image
            card = await self.vision_debugger.analyze_image(task.images[0], code_context=task.prompt)
        else:
            # Live screen capture and analyze
            card = await self.vision_debugger.capture_and_analyze(code_context=task.prompt)

        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            metadata={"language": card.language}
        )
        
        return AgentResponse(
            agent_name=self.name,
            content="I've looked at the screen and created a DebugCard detailing what I found. I hope this helps you fix the issue!",
            artifacts=[artifact]
        )

    async def debug_and_fix(self, code: str, error: str, language: str) -> AgentResponse:
        # Use vision debugger's code analysis method which also outputs a DebugCard
        card = await self.vision_debugger.analyze_code_for_bugs(code, error, language)
        
        artifact = AgentArtifact(
            artifact_type="debug_card",
            title=card.bug_title,
            content=json.dumps(card.to_dict()),
            metadata={"language": language}
        )
        
        return AgentResponse(
            agent_name=self.name,
            content="I've reviewed the error and prepared a DebugCard. It explains why this happens and shows how to fix it step-by-step.",
            artifacts=[artifact]
        )
