from .base import BaseAgent, AgentMessage
import json
import re


class PlannerAgent(BaseAgent):
    name = "planner_agent"

    SYSTEM = (
        "You are a senior content strategist. Given a topic/request, you produce a tight "
        "content plan as STRICT JSON only (no markdown fences, no commentary). "
        "Schema: {\"title\": str, \"audience\": str, \"tone\": str, \"content_type\": str, "
        "\"target_keywords\": [str], \"search_queries\": [str], \"sections\": [{\"heading\": str, \"key_points\": [str]}]}"
        " Produce 4-7 sections. search_queries should be 3-5 concise web search queries to research the topic."
    )

    async def run(self, task_payload: dict) -> AgentMessage:
        topic = task_payload["topic"]
        content_type = task_payload.get("content_type", "blog")
        tone = task_payload.get("tone", "professional, engaging")
        keywords = task_payload.get("keywords", [])

        prompt = (
            f"Topic/request: {topic}\n"
            f"Desired content type: {content_type}\n"
            f"Desired tone: {tone}\n"
            f"Seed keywords (optional): {', '.join(keywords) if keywords else 'none provided'}\n\n"
            "Return the JSON plan now."
        )
        raw = await self.llm.generate(self.SYSTEM, prompt, temperature=0.3)
        plan = self._safe_json(raw)
        return AgentMessage(sender=self.name, receiver="orchestrator", type="result", payload=plan)

    @staticmethod
    def _safe_json(raw: str) -> dict:
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            # Fallback minimal plan so pipeline never hard-fails
            return {
                "title": "Untitled Content",
                "audience": "general readers",
                "tone": "professional",
                "content_type": "blog",
                "target_keywords": [],
                "search_queries": [raw[:80]],
                "sections": [{"heading": "Introduction", "key_points": ["Overview"]}],
            }
