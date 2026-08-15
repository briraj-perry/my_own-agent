"""ChromaDB local vector store indexer for repository files and notes.

Scans codebase files, splits them into code/text chunks, generates embeddings,
and performs similarity search queries with persistent storage and fallbacks.
"""

import os
import re
import json
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

# Try importing ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    chromadb = None
    HAS_CHROMADB = False


def default_text_chunker(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """Splits text into chunks while preserving line number boundaries.

    Args:
        text: File text content.
        chunk_size: Target character limit per chunk.
        chunk_overlap: Character overlap between consecutive chunks.

    Returns:
        List of dicts with 'content', 'start_line', 'end_line'.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    chunks = []
    current_lines = []
    current_length = 0
    start_line = 1

    for idx, line in enumerate(lines, 1):
        current_lines.append(line)
        current_length += len(line)

        if current_length >= chunk_size:
            chunk_content = "".join(current_lines)
            end_line = idx
            chunks.append({
                "content": chunk_content,
                "start_line": start_line,
                "end_line": end_line
            })

            # Calculate overlap lines
            overlap_length = 0
            overlap_lines = []
            for rev_line in reversed(current_lines):
                if overlap_length + len(rev_line) > chunk_overlap:
                    break
                overlap_lines.insert(0, rev_line)
                overlap_length += len(rev_line)

            current_lines = overlap_lines
            current_length = overlap_length
            start_line = max(1, idx - len(overlap_lines) + 1)

    if current_lines:
        chunk_content = "".join(current_lines)
        end_line = len(lines)
        chunks.append({
            "content": chunk_content,
            "start_line": start_line,
            "end_line": end_line
        })

    return chunks


class FallbackVectorStore:
    """Lightweight persistent fallback vector store when ChromaDB is unavailable.

    Uses character n-gram TF-IDF vectorization with cosine similarity.
    """

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_file = self.storage_path / "fallback_store.json"
        self.documents: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []

    def _save(self):
        self.storage_path.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2)

    def _vectorize(self, text: str) -> Dict[str, float]:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return {}
        counts: Dict[str, float] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0.0) + 1.0
        norm = math.sqrt(sum(v * v for v in counts.values()))
        if norm > 0:
            for k in counts:
                counts[k] /= norm
        return counts

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        score = 0.0
        for k, v in vec1.items():
            if k in vec2:
                score += v * vec2[k]
        return score

    def add_documents(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        added_ids = []
        for idx, text in enumerate(contents):
            doc_id = ids[idx] if ids and idx < len(ids) else hashlib.md5(text.encode()).hexdigest()
            meta = metadatas[idx] if metadatas and idx < len(metadatas) else {}
            vec = self._vectorize(text)
            self.documents.append({
                "id": doc_id,
                "content": text,
                "metadata": meta,
                "vector": vec
            })
            added_ids.append(doc_id)
        self._save()
        return added_ids

    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        q_vec = self._vectorize(query)
        scored = []
        for doc in self.documents:
            sim = self._cosine_similarity(q_vec, doc["vector"])
            scored.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": round(sim, 4)
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def clear(self):
        self.documents = []
        if self.storage_file.exists():
            try:
                os.remove(self.storage_file)
            except OSError:
                pass


class LocalVectorStore:
    """ChromaDB-backed local vector database indexer with fallback support."""

    DEFAULT_IGNORE_DIRS = {
        ".git", "__pycache__", ".venv", "venv", "env", ".idea",
        ".vscode", "node_modules", ".vector_db", "dist", "build"
    }
    DEFAULT_EXTENSIONS = {
        ".py", ".md", ".txt", ".json", ".yaml", ".yml",
        ".rst", ".html", ".css", ".js", ".ts"
    }

    def __init__(
        self,
        db_path: str = "./.vector_db",
        collection_name: str = "neo_agent_memory"
    ):
        """Initializes ChromaDB persistent store or fallback vector store.

        Args:
            db_path: Directory path for vector database persistence.
            collection_name: Name of ChromaDB collection.
        """
        self.db_path = Path(db_path).resolve()
        self.collection_name = collection_name
        self.use_chroma = HAS_CHROMADB
        self.fallback_store = None
        self.chroma_collection = None

        if self.use_chroma:
            try:
                self.db_path.mkdir(parents=True, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=str(self.db_path))
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name
                )
            except Exception as e:
                # Fall back gracefully if ChromaDB fails initialization
                self.use_chroma = False
                self.fallback_store = FallbackVectorStore(str(self.db_path))
        else:
            self.fallback_store = FallbackVectorStore(str(self.db_path))

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Adds text documents and metadata into the vector store.

        Args:
            documents: List of text chunk strings.
            metadatas: List of associated metadata dicts.
            ids: Optional document IDs. Generated automatically if omitted.

        Returns:
            List of document IDs added.
        """
        if not documents:
            return []

        if ids is None:
            ids = [
                hashlib.sha256(f"{doc}_{i}".encode()).hexdigest()[:16]
                for i, doc in enumerate(documents)
            ]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Convert complex metadata values to strings/numbers to avoid ChromaDB serialization issues
        clean_metadatas = []
        for meta in metadatas:
            clean_m = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                else:
                    clean_m[k] = str(v)
            clean_metadatas.append(clean_m)

        if self.use_chroma and self.chroma_collection:
            try:
                self.chroma_collection.add(
                    documents=documents,
                    metadatas=clean_metadatas,
                    ids=ids
                )
                return ids
            except Exception:
                # Switch to fallback if ChromaDB insertion throws runtime exception
                if self.fallback_store is None:
                    self.fallback_store = FallbackVectorStore(str(self.db_path))
                return self.fallback_store.add_documents(documents, clean_metadatas, ids)
        else:
            return self.fallback_store.add_documents(documents, clean_metadatas, ids)

    def index_directory(
        self,
        dir_path: str = ".",
        extensions: Optional[Set[str]] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 100
    ) -> Dict[str, Any]:
        """Scans directory, splits eligible code/note files into chunks, and stores embeddings.

        Args:
            dir_path: Root directory to index.
            extensions: Allowed file extensions set.
            chunk_size: Character size limit for text chunks.
            chunk_overlap: Overlap size between chunks.

        Returns:
            Summary dict with file_count, chunk_count, and indexed_files list.
        """
        root_dir = Path(dir_path).resolve()
        valid_exts = extensions if extensions else self.DEFAULT_EXTENSIONS

        indexed_files = []
        all_chunks = []
        all_metadatas = []

        if not root_dir.exists() or not root_dir.is_dir():
            return {
                "file_count": 0,
                "chunk_count": 0,
                "error": f"Directory '{dir_path}' does not exist or is not a directory."
            }

        for root, dirs, files in os.walk(root_dir):
            # Exclude default ignored directories
            dirs[:] = [d for d in dirs if d not in self.DEFAULT_IGNORE_DIRS and not d.startswith(".")]

            for file_name in files:
                file_path = Path(root) / file_name
                if file_path.suffix.lower() not in valid_exts:
                    continue

                try:
                    rel_path = str(file_path.relative_to(root_dir))
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()

                    if not text.strip():
                        continue

                    chunks = default_text_chunker(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                    for chunk in chunks:
                        all_chunks.append(chunk["content"])
                        all_metadatas.append({
                            "file_path": rel_path,
                            "file_name": file_name,
                            "file_ext": file_path.suffix,
                            "start_line": chunk["start_line"],
                            "end_line": chunk["end_line"]
                        })

                    indexed_files.append(rel_path)

                except Exception:
                    continue

        if all_chunks:
            self.add_documents(all_chunks, metadatas=all_metadatas)

        return {
            "file_count": len(indexed_files),
            "chunk_count": len(all_chunks),
            "indexed_files": indexed_files,
            "engine": "ChromaDB" if (self.use_chroma and self.chroma_collection) else "FallbackStore"
        }

    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Queries vector database for top matching code/note chunks.

        Args:
            query: Search query text.
            k: Top-k results limit.

        Returns:
            List of result dicts containing 'content', 'metadata', 'score', and 'id'.
        """
        if not query.strip():
            return []

        if self.use_chroma and self.chroma_collection:
            try:
                results = self.chroma_collection.query(
                    query_texts=[query],
                    n_results=min(k, max(1, self.chroma_collection.count()))
                )

                output = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                    distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
                    ids = results["ids"][0] if "ids" in results else [""] * len(docs)

                    for idx, doc in enumerate(docs):
                        dist = distances[idx] if idx < len(distances) else 0.0
                        score = round(1.0 / (1.0 + dist), 4)  # Normalize distance to similarity score
                        output.append({
                            "id": ids[idx],
                            "content": doc,
                            "metadata": metas[idx],
                            "score": score
                        })
                return output

            except Exception:
                if self.fallback_store is None:
                    self.fallback_store = FallbackVectorStore(str(self.db_path))
                return self.fallback_store.similarity_search(query, k=k)

        else:
            return self.fallback_store.similarity_search(query, k=k)

    def clear(self) -> bool:
        """Clears the collection database."""
        try:
            if self.use_chroma and self.chroma_collection:
                self.chroma_client.delete_collection(self.collection_name)
                self.chroma_collection = self.chroma_client.get_or_create_collection(self.collection_name)
            elif self.fallback_store:
                self.fallback_store.clear()
            return True
        except Exception:
            return False
