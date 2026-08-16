import os
import glob
import ast
import re
from typing import List, Dict, Any, Optional
from tools import file_tools

class CodebaseIndexer:
    """Manages workspace file indexing, tree generation, AST symbol navigation, and metadata for ANY directory on disk."""
    
    EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".chromadb", ".idea", ".vscode"}
    ALLOWED_EXTENSIONS = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".sh", ".ps1", ".yml", ".yaml", ".cpp", ".c", ".h", ".cs", ".java"}

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir) if root_dir else file_tools.get_workspace_root()
        self.indexed_files: List[Dict[str, Any]] = []
        self.symbol_index: Dict[str, List[Dict[str, Any]]] = {}
        self.is_indexed = False

    def update_root_dir(self, new_root: str):
        """Updates indexer root directory to point to ANY system folder."""
        file_tools.set_workspace_root(new_root)
        self.root_dir = os.path.abspath(new_root)
        self.is_indexed = False
        return self.scan_files()

    def scan_files(self) -> List[Dict[str, Any]]:
        """Scans directory structure, extracts basic stats, and builds AST symbol index."""
        self.root_dir = file_tools.get_workspace_root()
        files_info = []
        self.symbol_index = {}

        for root, dirs, files in os.walk(self.root_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.ALLOWED_EXTENSIONS or file in {"requirements.txt", "Dockerfile", "package.json"}:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                    try:
                        size = os.path.getsize(full_path)
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = len(content.splitlines())
                            self._extract_file_symbols(rel_path, full_path, ext, content)
                    except Exception:
                        size = 0
                        lines = 0

                    files_info.append({
                        "name": file,
                        "path": rel_path,
                        "abs_path": full_path,
                        "size": size,
                        "lines": lines,
                        "ext": ext
                    })
        self.indexed_files = files_info
        self.is_indexed = True
        return files_info

    def _extract_file_symbols(self, rel_path: str, full_path: str, ext: str, content: str):
        """Extracts AST symbols (classes, functions, methods, routes) from Python and JS files."""
        if ext in {".py", ".pyw"}:
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        sym_name = node.name
                        self.symbol_index.setdefault(sym_name, []).append({
                            "name": sym_name,
                            "type": "function",
                            "file": rel_path,
                            "line": node.lineno,
                            "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                        })
                    elif isinstance(node, ast.ClassDef):
                        sym_name = node.name
                        self.symbol_index.setdefault(sym_name, []).append({
                            "name": sym_name,
                            "type": "class",
                            "file": rel_path,
                            "line": node.lineno,
                            "kind": "class"
                        })
            except Exception:
                pass
        elif ext in {".js", ".jsx", ".ts", ".tsx"}:
            # Regex symbol extraction for JavaScript / TypeScript
            js_fn_matches = re.finditer(r'(?:function\s+([a-zA-Z0-9_$]+)|class\s+([a-zA-Z0-9_$]+)|(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>)', content)
            lines = content.splitlines()
            for m in js_fn_matches:
                sym_name = m.group(1) or m.group(2) or m.group(3)
                if sym_name:
                    # Estimate line number
                    start_pos = m.start()
                    line_no = content[:start_pos].count('\n') + 1
                    sym_type = "class" if m.group(2) else "function"
                    self.symbol_index.setdefault(sym_name, []).append({
                        "name": sym_name,
                        "type": sym_type,
                        "file": rel_path,
                        "line": line_no,
                        "kind": sym_type
                    })

    def find_symbol_references(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Returns all AST definitions matching symbol_name across workspace."""
        if not self.is_indexed:
            self.scan_files()
        return self.symbol_index.get(symbol_name, [])

    def get_workspace_symbol_summary(self, max_symbols: int = 40) -> str:
        """Generates a concise markdown summary of workspace functions and classes for LLM context."""
        if not self.is_indexed:
            self.scan_files()

        if not self.symbol_index:
            return "No AST symbols indexed."

        symbols_list = []
        count = 0
        for name, defs in self.symbol_index.items():
            for d in defs:
                symbols_list.append(f"- `{d['name']}` ({d['type']}) in `{d['file']}:{d['line']}`")
                count += 1
                if count >= max_symbols:
                    break
            if count >= max_symbols:
                break

        return "\n".join(symbols_list)

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
        symbol_count = sum(len(v) for v in self.symbol_index.values())
        return {
            "status": "success",
            "workspace_root": self.root_dir,
            "file_count": len(files),
            "symbol_count": symbol_count,
            "total_lines": total_lines,
            "total_bytes": total_size,
            "message": f"Successfully indexed {len(files)} files ({total_lines} lines of code, {symbol_count} AST symbols) in '{self.root_dir}'."
        }
