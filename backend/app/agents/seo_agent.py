from .base import BaseAgent, AgentMessage
import json
import re


class SEOAgent(BaseAgent):
    name = "seo_agent"

    SYSTEM = (
        "You are an SEO specialist. Given a Markdown article and target keywords, optimize "
        "headings and suggest metadata. Return STRICT JSON only with schema: "
        "{\"meta_title\": str (max 60 chars), \"meta_description\": str (max 160 chars), "
        "\"slug\": str, \"primary_keyword\": str, \"secondary_keywords\": [str], "
        "\"seo_suggestions\": [str], \"readability_tips\": [str], \"seo_score\": int (0-100)}"
    )

    async def run(self, task_payload: dict) -> AgentMessage:
        draft = task_payload["draft_markdown"]
        target_keywords = task_payload.get("target_keywords", [])

        prompt = (
            f"Target keywords: {', '.join(target_keywords) if target_keywords else 'infer from content'}\n\n"
            f"Article (Markdown):\n{draft[:6000]}\n\n"
            "Analyze and return the JSON now."
        )
        raw = await self.llm.generate(self.SYSTEM, prompt, temperature=0.2)
        seo_meta = self._safe_json(raw)

        return AgentMessage(sender=self.name, receiver="orchestrator", type="result", payload=seo_meta)

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
            return {
                "meta_title": "Untitled",
                "meta_description": "",
                "slug": "untitled",
                "primary_keyword": "",
                "secondary_keywords": [],
                "seo_suggestions": [],
                "readability_tips": [],
                "seo_score": 50,
            }
