"""Tools package initialization for my_neo-agent.

Exports file tools, code execution tools, web search tools, and RAG memory search tools.
"""

from tools.file_tools import (
    is_safe_path,
    read_file,
    write_file,
    list_directory,
)

from tools.code_executor import (
    execute_code,
    run_python_script,
    run_powershell_script,
)

from tools.web_search import (
    web_search,
    duckduckgo_search,
)

from tools.rag_tools import (
    search_codebase,
    index_codebase,
    get_vector_store,
)

# Exported list of all agent tools for LangChain agent initialization
ALL_TOOLS = [
    read_file,
    write_file,
    list_directory,
    run_python_script,
    run_powershell_script,
    web_search,
    search_codebase,
    index_codebase,
]

__all__ = [
    "is_safe_path",
    "read_file",
    "write_file",
    "list_directory",
    "execute_code",
    "run_python_script",
    "run_powershell_script",
    "web_search",
    "duckduckgo_search",
    "search_codebase",
    "index_codebase",
    "get_vector_store",
    "ALL_TOOLS",
]
