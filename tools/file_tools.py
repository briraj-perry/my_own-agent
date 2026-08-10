import os
import time
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath("d:/learning/school_projects/my_neo-agent")

def is_safe_path(path: str) -> bool:
    """Ensures paths remain strictly inside the workspace boundary."""
    abs_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    return abs_path.startswith(WORKSPACE_ROOT)

def create_directory(rel_path: str) -> Dict[str, Any]:
    """Creates single or nested directories within workspace bounds."""
    if not is_safe_path(rel_path):
        return {"status": "error", "message": f"Security Error: Path '{rel_path}' is outside workspace bounds."}

    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, rel_path))
    try:
        os.makedirs(full_path, exist_ok=True)
        return {
            "status": "success",
            "path": rel_path,
            "full_path": full_path,
            "message": f"Successfully created directory '{rel_path}'."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create directory '{rel_path}': {str(e)}"}

def write_file(rel_path: str, content: str) -> Dict[str, Any]:
    """Writes code, text, or configuration files to disk within workspace bounds."""
    if not is_safe_path(rel_path):
        return {"status": "error", "message": f"Security Error: Path '{rel_path}' is outside workspace bounds."}

    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, rel_path))
    dir_name = os.path.dirname(full_path)
    
    try:
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        lines = len(content.splitlines())
        return {
            "status": "success",
            "path": rel_path,
            "full_path": full_path,
            "lines": lines,
            "bytes": len(content.encode("utf-8")),
            "message": f"Successfully written file '{rel_path}' ({lines} lines)."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write file '{rel_path}': {str(e)}"}

def write_note(title: str, content: str, folder: str = "notes") -> Dict[str, Any]:
    """Creates organized Markdown notes in the specified workspace note folder."""
    # Clean filename
    clean_title = title.lower().replace(" ", "_").replace("/", "_")
    if not clean_title.endswith(".md"):
        clean_title += ".md"

    note_rel_path = os.path.join(folder, clean_title)
    
    note_header = f"# Note: {title}\n*Created by Neo Agent on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n"
    full_content = note_header + content

    return write_file(note_rel_path, full_content)

def read_file(rel_path: str) -> Dict[str, Any]:
    """Reads content from a workspace file."""
    if not is_safe_path(rel_path):
        return {"status": "error", "message": f"Security Error: Path '{rel_path}' is outside workspace bounds."}

    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, rel_path))
    if not os.path.exists(full_path):
        return {"status": "error", "message": f"File '{rel_path}' does not exist."}

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {
            "status": "success",
            "path": rel_path,
            "content": content,
            "lines": len(content.splitlines()),
            "message": f"Successfully read file '{rel_path}'."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to read file '{rel_path}': {str(e)}"}

def list_directory(rel_path: str = ".") -> Dict[str, Any]:
    """Lists files and folders inside the specified directory."""
    if not is_safe_path(rel_path):
        return {"status": "error", "message": f"Security Error: Path '{rel_path}' is outside workspace bounds."}

    full_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, rel_path))
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return {"status": "error", "message": f"Directory '{rel_path}' does not exist."}

    try:
        items = os.listdir(full_path)
        result = []
        for item in items:
            item_full = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_full)
            result.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "path": os.path.relpath(item_full, WORKSPACE_ROOT).replace("\\", "/")
            })
        return {
            "status": "success",
            "path": rel_path,
            "items": result,
            "count": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list directory '{rel_path}': {str(e)}"}
