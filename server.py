import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import NeoAgentCore
from agent.orchestrator import MasterOrchestrator
from agent.base_agent import AgentName
from indexer import CodebaseIndexer
from tools import file_tools

app = FastAPI(title="my_neo-agent Dashboard API", version="1.0.0")

# Enable CORS for flexible local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the orchestrator (replaces direct NeoAgentCore usage)
orchestrator = MasterOrchestrator()
agent_engine = orchestrator  # Backward compatibility alias
indexer = CodebaseIndexer()

# Data Models
class ModelSelectRequest(BaseModel):
    model_id: str

class PermissionResponseRequest(BaseModel):
    request_id: str
    approved: bool

class FolderResponseRequest(BaseModel):
    request_id: str
    folder: str

class FrameworkResponseRequest(BaseModel):
    request_id: str
    choice: str

class SetRootRequest(BaseModel):

    folder: str

class FolderAnalyzeRequest(BaseModel):
    folder: str = "."

# REST API Endpoints
@app.get("/api/status")
async def get_status():
    file_count = len(indexer.indexed_files) if indexer.is_indexed else len(indexer.scan_files())
    return {
        "agent": "my_neo-agent",
        "status": "online",
        "active_model": agent_engine.active_model,
        "active_workspace_root": file_tools.get_workspace_root(),
        "indexed_files": file_count,
        "active_subagents_count": len(agent_engine.active_sub_agents),
        "mascot": "purple-pixel-robot"
    }

@app.get("/api/models")
async def get_models():
    return {
        "active_model": agent_engine.active_model,
        "available_models": agent_engine.get_available_models()
    }

@app.post("/api/models/select")
async def select_model(req: ModelSelectRequest):
    result = agent_engine.set_model(req.model_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/reindex")
async def reindex_codebase():
    summary = indexer.reindex()
    return summary

@app.get("/api/files")
async def get_file_tree():
    return {"tree": indexer.get_file_tree(), "workspace_root": file_tools.get_workspace_root()}

@app.get("/api/file/content")
async def get_file_content(path: str = Query(..., description="File path to open and read")):
    res = file_tools.read_file(path)
    if res.get("status") != "success":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@app.get("/api/workspace/folders")
async def get_workspace_folders():
    return {"folders": file_tools.list_workspace_folders(), "current_root": file_tools.get_workspace_root()}

@app.post("/api/workspace/set_root")
async def set_workspace_root(req: SetRootRequest):
    res = file_tools.set_workspace_root(req.folder)
    if res.get("status") == "success":
        indexer.update_root_dir(req.folder)
    return res

@app.get("/api/subagents")
async def get_sub_agents():
    return {"sub_agents": agent_engine.get_sub_agents_data()}

@app.post("/api/permission")
async def handle_permission(req: PermissionResponseRequest):
    success = agent_engine.resolve_permission(req.request_id, req.approved)
    if not success:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Permission request ID not found or already resolved."})
    return {"status": "success", "request_id": req.request_id, "approved": req.approved}

@app.post("/api/folder_selection")
async def handle_folder_selection(req: FolderResponseRequest):
    file_tools.set_workspace_root(req.folder)
    success = agent_engine.resolve_folder_selection(req.request_id, req.folder)
    return {"status": "success", "request_id": req.request_id, "folder": req.folder}

@app.post("/api/framework_selection")
async def handle_framework_selection(req: FrameworkResponseRequest):
    success = agent_engine.resolve_framework_selection(req.request_id, req.choice)
    return {"status": "success", "request_id": req.request_id, "choice": req.choice}

@app.post("/api/analyze/folder")

async def analyze_folder(req: FolderAnalyzeRequest):
    result = await agent_engine.analyze_and_autofix_folder(req.folder)
    return result

@app.post("/api/analyze/screen")
async def analyze_screen(req: FolderAnalyzeRequest):
    result = await agent_engine.analyze_and_autofix_screen_and_folder(req.folder)
    return result


# --- New Multi-Agent Endpoints ---

class DocumentAnalyzeRequest(BaseModel):
    file_path: str
    query: str = ""

class PresentationRequest(BaseModel):
    topic: str
    num_slides: int = 10
    format: str = "both"
    target_folder: str = "."

class ScreenDebugRequest(BaseModel):
    code_context: str = ""


@app.get("/api/agents")
async def list_agents():
    """List available agents and their capabilities."""
    return {
        "agents": [
            {"name": "neo", "description": "Single-file web apps, Canvas games, and general coding help", "icon": "🤖"},
            {"name": "claw", "description": "Full-stack Next.js/React applications", "icon": "⚡"},
            {"name": "eagle", "description": "Code analysis, document parsing, bug fixing, and vision debugging", "icon": "🦅"},
            {"name": "herald", "description": "School presentation slide decks (Reveal.js + PowerPoint)", "icon": "📊"},
        ],
        "orchestrator": "active",
    }


@app.post("/api/analyze-document")
async def analyze_document(req: DocumentAnalyzeRequest):
    """Upload a document path for Eagle analysis."""
    from agent.base_agent import AgentTask
    task = AgentTask(
        prompt=req.query or f"Analyze and summarize this document: {req.file_path}",
        files=[req.file_path],
        context={"task_type": "document_analysis"},
    )
    eagle = orchestrator._get_agent(AgentName.EAGLE)
    response = await eagle.execute(task)
    return response.to_dict()


@app.post("/api/generate-presentation")
async def generate_presentation(req: PresentationRequest):
    """Generate a presentation via Herald agent."""
    from agent.base_agent import AgentTask
    task = AgentTask(
        prompt=f"Create a presentation about: {req.topic}",
        target_folder=req.target_folder,
        context={"task_type": "presentation", "num_slides": req.num_slides, "format": req.format},
    )
    herald = orchestrator._get_agent(AgentName.HERALD)
    response = await herald.execute(task)
    return response.to_dict()


@app.post("/api/debug-screen")
async def debug_screen(req: ScreenDebugRequest):
    """Trigger vision debug via Eagle agent."""
    from agent.base_agent import AgentTask
    task = AgentTask(
        prompt="Debug my screen - analyze the current desktop for errors",
        context={"task_type": "vision_debug", "code_context": req.code_context},
    )
    eagle = orchestrator._get_agent(AgentName.EAGLE)
    response = await eagle.execute(task)
    return response.to_dict()


# WebSocket Chat Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected to my_neo-agent Dashboard WebSocket.")
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = msg.get("type")

            if msg_type == "chat":
                query = msg.get("message", "").strip()
                images = msg.get("images", [])
                if not query and not images:
                    continue
                
                # Stream responses from agent engine with attached images
                async for event in agent_engine.stream_response(query, images=images):
                    await websocket.send_json(event)

            elif msg_type == "permission_response":
                req_id = msg.get("id")
                approved = msg.get("approved", False)
                agent_engine.resolve_permission(req_id, approved)
                await websocket.send_json({"type": "permission_acknowledged", "id": req_id, "approved": approved})

            elif msg_type == "folder_response":
                req_id = msg.get("id")
                folder = msg.get("folder", ".")
                file_tools.set_workspace_root(folder)
                agent_engine.resolve_folder_selection(req_id, folder)
                await websocket.send_json({"type": "folder_acknowledged", "id": req_id, "folder": folder})

            elif msg_type == "framework_response":
                req_id = msg.get("id")
                choice = msg.get("choice", "nextjs")
                agent_engine.resolve_framework_selection(req_id, choice)
                await websocket.send_json({"type": "framework_acknowledged", "id": req_id, "choice": choice})

            elif msg_type == "ping":

                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print("[WS] Client disconnected.")
    except Exception as e:
        print(f"[WS Error] {e}")

# Mount UI static files directory
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.exists(ui_dir):
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")