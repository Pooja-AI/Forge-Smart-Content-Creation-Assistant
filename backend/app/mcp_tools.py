"""
Minimal MCP-style tool registry.

This mimics the Model Context Protocol pattern: a set of named tools with
JSON-schema-like descriptions that agents/orchestrator can discover and call
uniformly, rather than importing implementation modules directly. A real MCP
server (e.g. via the `mcp` Python SDK) can be dropped in here later, exposing
the same tool names over stdio/SSE for external MCP clients (Claude Desktop,
Claude Code, etc.) to use against this content platform.
"""
from ..rag import vector_store
from duckduckgo_search import DDGS

TOOLS = {
    "web_search": {
        "description": "Search the web for a query and return top results (title, snippet, url).",
        "input_schema": {"query": "string", "max_results": "integer"},
    },
    "rag_query": {
        "description": "Query the internal knowledge base (vector DB) for relevant context chunks.",
        "input_schema": {"query": "string", "top_k": "integer"},
    },
    "rag_ingest": {
        "description": "Ingest raw text documents into the knowledge base for future retrieval.",
        "input_schema": {"texts": "list[string]", "source": "string"},
    },
}


def list_tools():
    return TOOLS


def call_tool(name: str, args: dict):
    if name == "web_search":
        with DDGS() as ddgs:
            return [
                {"title": r.get("title"), "snippet": r.get("body"), "url": r.get("href")}
                for r in ddgs.text(args["query"], max_results=args.get("max_results", 5))
            ]
    elif name == "rag_query":
        return vector_store.query(args["query"], top_k=args.get("top_k", 5))
    elif name == "rag_ingest":
        n = vector_store.add_documents(args["texts"], source=args.get("source", "mcp_ingest"))
        return {"chunks_ingested": n}
    else:
        raise ValueError(f"Unknown tool: {name}")
