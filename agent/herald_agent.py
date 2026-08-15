import os
import json
import re
from typing import AsyncGenerator, Dict, Any, List

from agent.base_agent import BaseAgent, AgentName, AgentTask, AgentResponse, AgentArtifact
from agent.prompts import HERALD_SYSTEM_PROMPT
from tools.slide_builder import SlideBuilder

class HeraldAgent(BaseAgent):
    name = AgentName.HERALD
    description = "School presentation slide decks (Reveal.js + PowerPoint)"
    
    def __init__(self):
        super().__init__()
        self.system_prompt = HERALD_SYSTEM_PROMPT
        self.slide_builder = SlideBuilder()
        
    def _is_update_request(self, prompt: str) -> bool:
        lower_prompt = prompt.lower()
        keywords = ["update", "change", "modify", "edit"]
        return any(kw in lower_prompt for kw in keywords) and not self._is_add_slide_request(prompt)
        
    def _is_add_slide_request(self, prompt: str) -> bool:
        lower_prompt = prompt.lower()
        return "add slide" in lower_prompt or "new slide" in lower_prompt
        
    def _parse_slide_json(self, llm_response: str) -> dict:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', llm_response, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r'(\{.*\})', llm_response, re.DOTALL)
            json_str = match.group(1) if match else llm_response
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse slide JSON: {e}")
            
    async def execute(self, task: AgentTask) -> AgentResponse:
        prompt = task.prompt
        
        if task.files:
            file_path = task.files[0]
            if self._is_add_slide_request(prompt):
                return await self.add_slide(file_path, prompt)
            if self._is_update_request(prompt):
                return await self.update_presentation(file_path, prompt)
                
        return await self.generate_presentation(prompt, task.target_folder)
        
    async def stream_execute(self, task: AgentTask) -> AsyncGenerator[Dict[str, Any], None]:
        yield {"type": "state", "mascot_state": "Herald is creating slides..."}
        
        prompt = task.prompt
        target_folder = task.target_folder
        
        if task.files:
            file_path = task.files[0]
            if self._is_add_slide_request(prompt):
                yield {"type": "token", "content": f"Adding slide to {os.path.basename(file_path)}...\n"}
                response = await self.add_slide(file_path, prompt)
            elif self._is_update_request(prompt):
                yield {"type": "token", "content": f"Updating {os.path.basename(file_path)}...\n"}
                response = await self.update_presentation(file_path, prompt)
            else:
                yield {"type": "token", "content": "Generating presentation...\n"}
                response = await self.generate_presentation(prompt, target_folder)
                
            for artifact in response.artifacts:
                yield {"type": "artifact", "artifact": artifact.to_dict()}
            yield {"type": "token", "content": f"\n{response.content}"}
            yield {"type": "execution_log", "message": "Presentation task completed."}
        else:
            yield {"type": "token", "content": "Generating presentation...\n"}
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Create a presentation based on this topic/instruction: {prompt}"}
            ]
            
            full_response = ""
            async for token in self._stream_ollama_tokens(messages):
                full_response += token
                yield {"type": "token", "content": token}
                
            try:
                slide_data = self._parse_slide_json(full_response)
                base_name = slide_data.get("title", "presentation").replace(" ", "_").lower()
                base_name = re.sub(r'[^a-z0-9_]', '', base_name)
                if not base_name:
                    base_name = "presentation"
                
                yield {"type": "state", "mascot_state": "Building files..."}
                result = self.slide_builder.build_both(slide_data, target_folder, base_name=base_name)
                
                artifacts = []
                if result.get("revealjs_path") and result.get("status") in ["success", "partial_success"]:
                    artifacts.append(AgentArtifact(
                        artifact_type="slide_deck",
                        title="Reveal.js Presentation",
                        content="HTML presentation generated.",
                        file_path=result["revealjs_path"],
                        metadata={"format": "html", "slide_count": result.get("slide_count", 0)}
                    ))
                    yield {"type": "artifact", "artifact": artifacts[-1].to_dict()}
                    
                if result.get("pptx_path") and result.get("status") in ["success", "partial_success"]:
                    artifacts.append(AgentArtifact(
                        artifact_type="slide_deck",
                        title="PowerPoint Presentation",
                        content="PPTX presentation generated.",
                        file_path=result["pptx_path"],
                        metadata={"format": "pptx", "slide_count": result.get("slide_count", 0)}
                    ))
                    yield {"type": "artifact", "artifact": artifacts[-1].to_dict()}
                    
                yield {"type": "execution_log", "message": "Presentation built successfully."}
                
            except ValueError as e:
                yield {"type": "token", "content": f"\n\nError parsing slide data: {e}"}
            except Exception as e:
                yield {"type": "token", "content": f"\n\nError generating files: {e}"}
                
        yield {"type": "state", "mascot_state": "idle"}
        
    async def generate_presentation(self, topic: str, target_folder: str, 
                                     num_slides: int = 10, format: str = "both") -> AgentResponse:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Create a presentation about: {topic}. Target around {num_slides} slides."}
        ]
        
        response_text = await self._call_ollama_complete(messages)
        
        try:
            slide_data = self._parse_slide_json(response_text)
        except ValueError as e:
            return AgentResponse(
                agent_name=self.name,
                content="I failed to generate valid slide data.",
                error=str(e)
            )
            
        base_name = slide_data.get("title", "presentation").replace(" ", "_").lower()
        base_name = re.sub(r'[^a-z0-9_]', '', base_name)
        if not base_name:
            base_name = "presentation"
            
        artifacts = []
        if format in ["both", "revealjs", "html"]:
            result = self.slide_builder.build_revealjs(slide_data, os.path.join(target_folder, f"{base_name}.html"))
            if result.get("status") in ["success", "partial_success"]:
                artifacts.append(AgentArtifact(
                    artifact_type="slide_deck",
                    title="Reveal.js Presentation",
                    content="HTML presentation generated.",
                    file_path=result["file_path"],
                    metadata={"format": "html", "slide_count": result.get("slide_count", 0)}
                ))
                
        if format in ["both", "pptx"]:
            result = self.slide_builder.build_pptx(slide_data, os.path.join(target_folder, f"{base_name}.pptx"))
            if result.get("status") in ["success", "partial_success"]:
                artifacts.append(AgentArtifact(
                    artifact_type="slide_deck",
                    title="PowerPoint Presentation",
                    content="PPTX presentation generated.",
                    file_path=result["file_path"],
                    metadata={"format": "pptx", "slide_count": result.get("slide_count", 0)}
                ))
                
        return AgentResponse(
            agent_name=self.name,
            content="Presentation generated successfully.",
            artifacts=artifacts
        )

    async def add_slide(self, file_path: str, slide_content: str, position: int = -1) -> AgentResponse:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Create a SINGLE slide based on this instruction: {slide_content}. Return ONLY the JSON for one slide object (not the full deck)."}
        ]
        
        response_text = await self._call_ollama_complete(messages)
        
        try:
            slide_data = self._parse_slide_json(response_text)
        except ValueError as e:
            return AgentResponse(
                agent_name=self.name,
                content="I failed to generate valid slide data for the new slide.",
                error=str(e)
            )
            
        if file_path.endswith(".pptx"):
            result = self.slide_builder.add_slide_to_pptx(file_path, slide_data, position)
            if result["status"] == "success":
                return AgentResponse(
                    agent_name=self.name,
                    content="Slide added successfully.",
                    artifacts=[AgentArtifact(
                        artifact_type="slide_deck",
                        title="Updated PowerPoint",
                        content="PPTX updated with new slide.",
                        file_path=file_path,
                        metadata={"format": "pptx"}
                    )]
                )
            else:
                return AgentResponse(agent_name=self.name, content="Failed to add slide.", error=result.get("error_message"))
        else:
            return AgentResponse(agent_name=self.name, content="Adding slides currently only supported for .pptx files directly.", error="Unsupported format")

    async def update_presentation(self, file_path: str, instruction: str) -> AgentResponse:
        content_preview = ""
        try:
            if file_path.endswith(".html") or file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content_preview = f.read()[:2000]
        except Exception:
            pass

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Update the presentation based on this instruction: {instruction}.\nExisting content preview:\n{content_preview}\nReturn the COMPLETE updated JSON slide deck."}
        ]
        
        response_text = await self._call_ollama_complete(messages)
        try:
            slide_data = self._parse_slide_json(response_text)
        except ValueError as e:
            return AgentResponse(agent_name=self.name, content="Failed to parse updated slide data.", error=str(e))
            
        artifacts = []
        if file_path.endswith(".html"):
            result = self.slide_builder.build_revealjs(slide_data, file_path)
            if result.get("status") in ["success", "partial_success"]:
                artifacts.append(AgentArtifact(
                    artifact_type="slide_deck", title="Updated Reveal.js Presentation",
                    content="HTML presentation updated.", file_path=result.get("file_path", file_path),
                    metadata={"format": "html"}
                ))
        elif file_path.endswith(".pptx"):
            result = self.slide_builder.build_pptx(slide_data, file_path)
            if result.get("status") in ["success", "partial_success"]:
                artifacts.append(AgentArtifact(
                    artifact_type="slide_deck", title="Updated PowerPoint Presentation",
                    content="PPTX presentation updated.", file_path=result.get("file_path", file_path),
                    metadata={"format": "pptx"}
                ))
        
        return AgentResponse(agent_name=self.name, content="Presentation updated successfully.", artifacts=artifacts)
