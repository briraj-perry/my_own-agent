"""RAG tools module for codebase search and indexing.

Wraps LocalVectorStore in LangChain tools (search_codebase, index_codebase)
for semantic code search and context retrieval.
"""

from typing import Optional
from memory.vector_store import LocalVectorStore

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

# Global vector store instance lazy-initialized
_VECTOR_STORE_INSTANCE: Optional[LocalVectorStore] = None


def get_vector_store(db_path: str = "./.vector_db") -> LocalVectorStore:
    """Returns or initializes the singleton LocalVectorStore instance."""
    global _VECTOR_STORE_INSTANCE
    if _VECTOR_STORE_INSTANCE is None:
        _VECTOR_STORE_INSTANCE = LocalVectorStore(db_path=db_path)
    return _VECTOR_STORE_INSTANCE


@tool
def search_codebase(query: str, k: int = 4, db_path: str = "./.vector_db") -> str:
    """Searches the local codebase/notes using RAG vector similarity search.

    Args:
        query: Code or documentation search query.
        k: Maximum number of relevant code chunks to return (default 4).
        db_path: Path to local vector store.

    Returns:
        Formatted summary string containing matching file paths, line ranges, score, and code snippets.
    """
    try:
        store = get_vector_store(db_path=db_path)
        results = store.similarity_search(query=query, k=k)

        if not results:
            return (
                f"No vector matches found for query '{query}'.\n"
                "Tip: Make sure to index the codebase first using `index_codebase()`."
            )

        formatted_output = [
            f"=== Codebase Vector Search Results for: '{query}' ({len(results)} matches) ==="
        ]

        for idx, item in enumerate(results, 1):
            meta = item.get("metadata", {})
            file_path = meta.get("file_path", "unknown_file")
            start_line = meta.get("start_line", "?")
            end_line = meta.get("end_line", "?")
            score = item.get("score", 0.0)

            formatted_output.append(
                f"\n[{idx}] File: {file_path} (Lines {start_line}-{end_line}) | Similarity Score: {score}\n"
                "```\n"
                f"{item['content'].strip()}\n"
                "```"
            )

        return "\n".join(formatted_output)

    except Exception as e:
        return f"Error conducting codebase search for '{query}': {type(e).__name__}: {str(e)}"


@tool
def index_codebase(directory_path: str = ".", db_path: str = "./.vector_db") -> str:
    """Indexes or re-indexes local repository files and notes into vector memory.

    Args:
        directory_path: Base path of repository to index (default '.').
        db_path: Path for vector database storage.

    Returns:
        Summary message of indexed files, chunk counts, and database status.
    """
    try:
        store = get_vector_store(db_path=db_path)
        summary = store.index_directory(dir_path=directory_path)

        if "error" in summary:
            return f"Indexing Error: {summary['error']}"

        return (
            f"=== Codebase Indexing Complete ===\n"
            f"Engine: {summary.get('engine', 'Local')}\n"
            f"Files Scanned & Indexed: {summary['file_count']}\n"
            f"Total Vector Chunks: {summary['chunk_count']}\n"
            f"Indexed Files Sample: {', '.join(summary['indexed_files'][:5])}"
            f"{'...' if len(summary['indexed_files']) > 5 else ''}"
        )

    except Exception as e:
        return f"Error indexing codebase at '{directory_path}': {type(e).__name__}: {str(e)}"
