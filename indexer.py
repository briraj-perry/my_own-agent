import os
import glob
from typing import List, Dict, Any

class CodebaseIndexer:
    """Manages workspace file indexing, tree generation, and metadata."""
    
    EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".chromadb", ".idea", ".vscode"}
    ALLOWED_EXTENSIONS = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".sh", ".ps1", ".yml", ".yaml"}

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.indexed_files: List[Dict[str, Any]] = []
        self.is_indexed = False

    def scan_files(self) -> List[Dict[str, Any]]:
        """Scans the directory structure and extracts basic stats."""
        files_info = []
        for root, dirs, files in os.walk(self.root_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.ALLOWED_EXTENSIONS or file in {"requirements.txt", "Dockerfile"}:
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

    def get_file_tree(self) -> List[Dict[str, Any]]:
        """Generates a nested tree representation for UI navigation."""
        if not self.is_indexed:
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
            "file_count": len(files),
            "total_lines": total_lines,
            "total_bytes": total_size,
            "message": f"Successfully indexed {len(files)} files ({total_lines} lines of code)."
        }
