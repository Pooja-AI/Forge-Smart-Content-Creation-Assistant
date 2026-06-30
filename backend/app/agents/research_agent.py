import os
from .base import BaseAgent, AgentMessage
from ..rag import vector_store

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"


class ResearchAgent(BaseAgent):
    name = "research_agent"

    async def run(self, task_payload: dict) -> AgentMessage:
        queries = task_payload.get("search_queries", [])[:5]
        topic = task_payload.get("topic", "")

        web_results = []
        if ENABLE_WEB_SEARCH:
            web_results = await self._web_search(queries or [topic])

        rag_results = vector_store.query(topic, top_k=5)

        return AgentMessage(
            sender=self.name,
            receiver="orchestrator",
            type="result",
            payload={"web_results": web_results, "rag_results": rag_results},
        )

    async def _web_search(self, queries: list[str]):
        """Uses the duckduckgo_search MCP-style tool (no API key required, open-source friendly)."""
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for q in queries:
                    for r in ddgs.text(q, max_results=3):
                        results.append(
                            {
                                "query": q,
                                "title": r.get("title"),
                                "snippet": r.get("body"),
                                "url": r.get("href"),
                            }
                        )
        except Exception as e:
            results.append({"query": "error", "title": "Web search unavailable", "snippet": str(e), "url": ""})
        return results
