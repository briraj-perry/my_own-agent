"""DuckDuckGo web search tool module for my_neo-agent.

Provides free web search capability using `duckduckgo_search` (DDGS) with clean fallback handling.
"""

from typing import List, Dict, Any, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func


def perform_ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Performs DuckDuckGo web search using duckduckgo_search package if available.

    Args:
        query: Search query string.
        max_results: Maximum number of search results to return.

    Returns:
        List of dictionaries with 'title', 'href'/'link', and 'body'/'snippet'.
    """
    results = []

    # Attempt 1: Modern duckduckgo_search with DDGS context manager
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                results.append({
                    "title": item.get("title", "No Title"),
                    "link": item.get("href", item.get("link", "")),
                    "snippet": item.get("body", item.get("snippet", ""))
                })
            if results:
                return results
    except ImportError:
        pass
    except Exception as e:
        # If DDGS failed with runtime error, attempt alternate syntax or capture error
        pass

    # Attempt 2: Older duckduckgo_search module function fallback
    try:
        import duckduckgo_search
        if hasattr(duckduckgo_search, "ddg"):
            raw_results = duckduckgo_search.ddg(query, max_results=max_results)
            if raw_results:
                for item in raw_results:
                    results.append({
                        "title": item.get("title", "No Title"),
                        "link": item.get("href", item.get("link", "")),
                        "snippet": item.get("body", item.get("snippet", ""))
                    })
                return results
    except Exception:
        pass

    return results


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Searches the web via DuckDuckGo and returns concise summaries of top results.

    Args:
        query: Search query string.
        max_results: Max results to retrieve (default 5).

    Returns:
        Formatted string containing titles, snippets, and source links.
    """
    try:
        results = perform_ddg_search(query, max_results=max_results)
        
        if not results:
            return (
                f"Web Search Results for '{query}':\n"
                "No results found or search package missing/unavailable.\n"
                "Note: Ensure `pip install duckduckgo_search` is installed for live web search capability."
            )

        formatted_output = [f"=== Web Search Results for: '{query}' ({len(results)} results) ==="]
        for idx, item in enumerate(results, 1):
            formatted_output.append(
                f"\n[{idx}] {item['title']}\n"
                f"    Link: {item['link']}\n"
                f"    Snippet: {item['snippet']}"
            )

        return "\n".join(formatted_output)

    except Exception as e:
        return f"Error executing web search for '{query}': {type(e).__name__}: {str(e)}"


# Alias tool function for backward compatibility
duckduckgo_search = web_search
