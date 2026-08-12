import os
import glob
from typing import List, Dict, Any, Optional
from tools import file_tools

class CodebaseIndexer:
    """Manages workspace file indexing, tree generation, and metadata for ANY directory on disk."""
    
    EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".chromadb", ".idea", ".vscode"}
    ALLOWED_EXTENSIONS = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".sh", ".ps1", ".yml", ".yaml", ".cpp", ".c", ".h", ".cs", ".java"}

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir) if root_dir else file_tools.get_workspace_root()
        self.indexed_files: List[Dict[str, Any]] = []
        self.is_indexed = False

    def update_root_dir(self, new_root: str):
        """Updates indexer root directory to point to ANY system folder."""
        file_tools.set_workspace_root(new_root)
        self.root_dir = os.path.abspath(new_root)
        self.is_indexed = False
        return self.scan_files()

    def scan_files(self) -> List[Dict[str, Any]]:
        """Scans the directory structure and extracts basic stats."""
        self.root_dir = file_tools.get_workspace_root()
        files_info = []
        for root, dirs, files in os.walk(self.root_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.ALLOWED_EXTENSIONS or file in {"requirements.txt", "Dockerfile", "package.json"}:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    try:
                        size = os.path.getsize(full_path)
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                    except Exception:
                        size = 0
                        lines = 0

                    files_info.append({
                        "name": file,
                        "path": rel_path.replace("\\", "/"),
                        "abs_path": full_path,
                        "size": size,
                        "lines": lines,
                        "ext": ext
                    })
        self.indexed_files = files_info
        self.is_indexed = True
        return files_info

    def get_file_tree(self, force_refresh: bool = True) -> List[Dict[str, Any]]:
        """Generates a nested tree representation for UI navigation."""
        if force_refresh or not self.is_indexed:
            self.scan_files()

        tree = []
        path_dict = {}

        for item in self.indexed_files:
            parts = item["path"].split("/")
            curr = tree
            accum_path = ""
            for i, part in enumerate(parts):
                accum_path = f"{accum_path}/{part}" if accum_path else part
                if i == len(parts) - 1:
                    curr.append({
                        "name": part,
                        "path": item["path"],
                        "type": "file",
                        "size": item["size"],
                        "lines": item["lines"]
                    })
                else:
                    if accum_path not in path_dict:
                        dir_node = {"name": part, "path": accum_path, "type": "directory", "children": []}
                        path_dict[accum_path] = dir_node["children"]
                        curr.append(dir_node)
                    curr = path_dict[accum_path]

        return tree

    def reindex(self) -> Dict[str, Any]:
        """Re-scans files and returns summary statistics."""
        files = self.scan_files()
        total_lines = sum(f["lines"] for f in files)
        total_size = sum(f["size"] for f in files)
        return {
            "status": "success",
            "workspace_root": self.root_dir,
            "file_count": len(files),
            "total_lines": total_lines,
            "total_bytes": total_size,
            "message": f"Successfully indexed {len(files)} files ({total_lines} lines of code) in '{self.root_dir}'."
        }
