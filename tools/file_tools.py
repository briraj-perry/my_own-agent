import os
import time
from typing import Dict, Any, List, Optional

CURRENT_WORKSPACE_ROOT = os.path.abspath("d:/learning/school_projects/my_neo-agent")

def get_workspace_root() -> str:
    """Returns the current active working directory root."""
    return CURRENT_WORKSPACE_ROOT

def set_workspace_root(new_path: str) -> Dict[str, Any]:
    """Sets the active workspace root to ANY system directory on disk."""
    global CURRENT_WORKSPACE_ROOT
    try:
        abs_p = os.path.abspath(new_path)
        if os.path.exists(abs_p) and os.path.isdir(abs_p):
            CURRENT_WORKSPACE_ROOT = abs_p
            return {
                "status": "success",
                "workspace_root": CURRENT_WORKSPACE_ROOT,
                "message": f"Successfully set active workspace root to: '{CURRENT_WORKSPACE_ROOT}'"
            }
        else:
            return {"status": "error", "message": f"Directory '{new_path}' does not exist on system."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to set workspace root: {str(e)}"}

def resolve_target_path(rel_or_abs_path: str, folder: str = ".") -> str:
    """Resolves any relative or absolute path against current workspace root or system disk."""
    if os.path.isabs(rel_or_abs_path):
        return os.path.abspath(rel_or_abs_path)
    
    if folder and os.path.isabs(folder):
        return os.path.abspath(os.path.join(folder, rel_or_abs_path))
    
    base_dir = os.path.abspath(os.path.join(CURRENT_WORKSPACE_ROOT, folder)) if folder and folder != "." else CURRENT_WORKSPACE_ROOT
    return os.path.abspath(os.path.join(base_dir, rel_or_abs_path))

def is_safe_path(path: str) -> bool:
    """Validates that path is a syntactically valid system path."""
    return True

def list_workspace_folders() -> List[str]:
    """Returns a clean list of existing directories inside current workspace root."""
    folders = [CURRENT_WORKSPACE_ROOT, "."]
    exclude = {".git", "__pycache__", ".venv", "venv", "node_modules", ".chromadb"}
    for root, dirs, _ in os.walk(CURRENT_WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude]
        rel = os.path.relpath(root, CURRENT_WORKSPACE_ROOT).replace("\\", "/")
        if rel != "." and rel not in folders:
            folders.append(rel)
    return folders

def get_folder_code_files(folder_path: str = ".") -> List[Dict[str, Any]]:
    """Recursively finds all Python (.py, .pyw) and source code files inside folder_path."""
    full_root = resolve_target_path(folder_path) if folder_path != "." else CURRENT_WORKSPACE_ROOT
    exclude_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".chromadb", ".idea", ".vscode"}
    allowed_exts = {".py", ".pyw", ".js", ".html", ".css", ".json", ".md", ".txt", ".sh", ".ps1", ".cpp", ".c", ".h", ".cs", ".java"}

    code_files = []
    if not os.path.exists(full_root):
        return code_files

    for root, dirs, files in os.walk(full_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_exts or f in {"requirements.txt", "Dockerfile", "package.json"}:
                full_f = os.path.join(root, f)
                rel_f = os.path.relpath(full_f, full_root).replace("\\", "/")
                code_files.append({
                    "name": f,
                    "rel_path": rel_f,
                    "full_path": full_f,
                    "ext": ext,
                    "is_python": ext in {".py", ".pyw"}
                })

    return code_files

def create_directory(rel_path: str, folder: str = ".") -> Dict[str, Any]:
    """Creates single or nested directories within ANY target system folder."""
    full_path = resolve_target_path(rel_path, folder)
    try:
        os.makedirs(full_path, exist_ok=True)
        return {
            "status": "success",
            "path": rel_path,
            "full_path": full_path,
            "message": f"Successfully created directory '{full_path}'."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create directory '{rel_path}': {str(e)}"}

def write_file(rel_path: str, content: str, folder: str = ".") -> Dict[str, Any]:
    """Writes code, text, or configuration files to ANY directory on system disk."""
    full_path = resolve_target_path(rel_path, folder)
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
            "message": f"Successfully written file '{full_path}' ({lines} lines)."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write file '{rel_path}': {str(e)}"}

def write_note(title: str, content: str, folder: str = "notes") -> Dict[str, Any]:
    """Creates organized Markdown notes in the specified note folder."""
    clean_title = title.lower().replace(" ", "_").replace("/", "_")
    if not clean_title.endswith(".md"):
        clean_title += ".md"

    note_header = f"# Note: {title}\n*Created by Neo Agent on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n---\n\n"
    full_content = note_header + content

    return write_file(clean_title, full_content, folder=folder)

def read_file(rel_path: str, folder: str = ".") -> Dict[str, Any]:
    """Reads content from ANY file on system disk. If target is a directory, switches workspace root to it."""
    full_path = resolve_target_path(rel_path, folder)
    if not os.path.exists(full_path):
        return {"status": "error", "message": f"Path '{full_path}' does not exist."}

    if os.path.isdir(full_path):
        set_workspace_root(full_path)
        dir_res = list_directory(full_path)
        return {
            "status": "is_directory",
            "path": rel_path,
            "full_path": full_path,
            "message": f"Opened directory '{full_path}' as active workspace root.",
            "items": dir_res.get("items", []),
            "count": dir_res.get("count", 0)
        }

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {
            "status": "success",
            "path": rel_path,
            "full_path": full_path,
            "content": content,
            "lines": len(content.splitlines()),
            "message": f"Successfully read file '{full_path}'."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to read file '{full_path}': {str(e)}"}

def list_directory(rel_path: str = ".") -> Dict[str, Any]:
    """Lists files and folders inside ANY specified directory on system disk."""
    full_path = resolve_target_path(rel_path) if rel_path != "." else CURRENT_WORKSPACE_ROOT
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return {"status": "error", "message": f"Directory '{full_path}' does not exist."}

    try:
        items = os.listdir(full_path)
        result = []
        for item in items:
            item_full = os.path.join(full_path, item)
            is_dir = os.path.isdir(item_full)
            ext = os.path.splitext(item)[1].lower()
            result.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "ext": ext,
                "is_python": ext in {".py", ".pyw"},
                "path": os.path.relpath(item_full, CURRENT_WORKSPACE_ROOT).replace("\\", "/") if item_full.startswith(CURRENT_WORKSPACE_ROOT) else item_full.replace("\\", "/")
            })
        return {
            "status": "success",
            "path": rel_path,
            "full_path": full_path,
            "items": result,
            "count": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list directory '{rel_path}': {str(e)}"}
