"""Integration test script for tools and RAG memory engine.

Tests file tools, code executor, web search fallback, and vector store RAG tools.
"""

import sys
from pathlib import Path

# Ensure root workspace directory is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

def test_all():
    print("=== Testing my_neo-agent Tools & Local RAG Engine ===")
    
    # 1. Imports check
    print("[1/5] Importing package tools...")
    from tools import (
        read_file, write_file, list_directory, is_safe_path,
        execute_code, run_python_script, run_powershell_script,
        web_search, search_codebase, index_codebase, ALL_TOOLS
    )
    from memory.vector_store import LocalVectorStore
    print(f"  -> Successfully imported {len(ALL_TOOLS)} tools.")

    # 2. Test File Tools
    print("\n[2/5] Testing File Tools...")
    sample_file = WORKSPACE_ROOT / "sample_test.txt"
    w_res = write_file.invoke({"file_path": str(sample_file), "content": "Hello World!\nNeo Agent RAG Engine Test Line 2"})
    print("  -> Write file:", "Success" if "Success" in w_res else w_res)
    
    r_res = read_file.invoke({"file_path": str(sample_file)})
    print("  -> Read file output sample:\n", r_res[:150])
    
    l_res = list_directory.invoke({"directory_path": str(WORKSPACE_ROOT)})
    print("  -> List directory output sample:\n", l_res[:200])

    # 3. Test Code Executor
    print("\n[3/5] Testing Code Execution Engine...")
    py_code = "import math\nprint(f'Math test sqrt(16) = {math.sqrt(16)}')"
    py_res = execute_code(py_code, language="python")
    print("  -> Python execution stdout:", py_res['stdout'].strip(), "| success:", py_res['success'])

    # 4. Test Web Search
    print("\n[4/5] Testing Web Search Tool...")
    ws_res = web_search.invoke({"query": "Python programming", "max_results": 2})
    print("  -> Web search output sample:\n", ws_res[:200])

    # 5. Test Vector Store & RAG
    print("\n[5/5] Testing Vector Store & RAG Tools...")
    idx_res = index_codebase.invoke({"directory_path": str(WORKSPACE_ROOT)})
    print("  -> Codebase indexing output:\n", idx_res)

    rag_res = search_codebase.invoke({"query": "Neo Agent RAG Engine Test"})
    print("  -> RAG search output:\n", rag_res)

    # Cleanup test file
    if sample_file.exists():
        sample_file.unlink()

    print("\n=== All Tools & RAG Engine Tests Completed Successfully ===")

if __name__ == "__main__":
    test_all()
