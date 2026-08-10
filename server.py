import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import NeoAgentCore
from indexer import CodebaseIndexer

app = FastAPI(title="my_neo-agent Dashboard API", version="1.0.0")

# Enable CORS for flexible local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_engine = NeoAgentCore()
indexer = CodebaseIndexer(root_dir=os.path.dirname(__file__))

# Data Models
class ModelSelectRequest(BaseModel):
    model_id: str

class PermissionResponseRequest(BaseModel):
    request_id: str
    approved: bool

# REST API Endpoints
@app.get("/api/status")
async def get_status():
    file_count = len(indexer.indexed_files) if indexer.is_indexed else len(indexer.scan_files())
    return {
        "agent": "my_neo-agent",
        "status": "online",
        "active_model": agent_engine.active_model,
        "indexed_files": file_count,
        "mascot": "purple-pixel-robot"
    }

@app.get("/api/models")
async def get_models():
    return {
        "active_model": agent_engine.active_model,
        "available_models": agent_engine.AVAILABLE_MODELS
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
    return {"tree": indexer.get_file_tree()}

@app.post("/api/permission")
async def handle_permission(req: PermissionResponseRequest):
    success = agent_engine.resolve_permission(req.request_id, req.approved)
    if not success:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Permission request ID not found or already resolved."})
    return {"status": "success", "request_id": req.request_id, "approved": req.approved}

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
                if not query:
                    continue
                
                # Stream responses from agent engine
                async for event in agent_engine.stream_response(query):
                    await websocket.send_json(event)

            elif msg_type == "permission_response":
                req_id = msg.get("id")
                approved = msg.get("approved", False)
                agent_engine.resolve_permission(req_id, approved)
                await websocket.send_json({"type": "permission_acknowledged", "id": req_id, "approved": approved})

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
