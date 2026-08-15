"""Tools package initialization for my_neo-agent.

Exports file tools, code execution tools, web search tools, RAG memory search tools,
document analysis tools, vision debugging tools, and slide building tools.
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

# New: Document analysis tools (Eagle Agent)
from tools.document_tools import (
    read_pdf,
    read_pptx,
    read_excel,
    read_code_file,
    detect_document_type,
    extract_document_summary,
)

# New: Vision debugger (Eagle Agent)
from tools.vision_debugger import (
    VisionDebugger,
    DebugCard,
)

# New: Slide builder (Herald Agent)
from tools.slide_builder import (
    SlideBuilder,
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
    # File tools
    "is_safe_path",
    "read_file",
    "write_file",
    "list_directory",
    # Code execution
    "execute_code",
    "run_python_script",
    "run_powershell_script",
    # Web search
    "web_search",
    "duckduckgo_search",
    # RAG tools
    "search_codebase",
    "index_codebase",
    "get_vector_store",
    # Document tools (Eagle)
    "read_pdf",
    "read_pptx",
    "read_excel",
    "read_code_file",
    "detect_document_type",
    "extract_document_summary",
    # Vision debugger (Eagle)
    "VisionDebugger",
    "DebugCard",
    # Slide builder (Herald)
    "SlideBuilder",
    # Tool registry
    "ALL_TOOLS",
]
