from .base import BaseAgent, AgentMessage
import json
import re


class FactCheckerAgent(BaseAgent):
    name = "fact_checker_agent"

    SYSTEM = (
        "You are a meticulous fact-checker. Given a Markdown article and a numbered list of "
        "available sources, identify factual claims that are NOT adequately supported by the "
        "sources, flag any claim that looks fabricated or overly specific (numbers, dates, stats) "
        "without citation, and verify citation markers [n] correspond to plausible source content. "
        "Return STRICT JSON only: {\"flagged_claims\": [{\"claim\": str, \"issue\": str, \"severity\": "
        "\"low\"|\"medium\"|\"high\"}], \"citation_coverage_pct\": int, \"overall_verdict\": str}"
    )

    async def run(self, task_payload: dict) -> AgentMessage:
        draft = task_payload["draft_markdown"]
        citation_map = task_payload.get("citation_map", [])
        sources_text = "\n".join(f"[{c['id']}] {c['title']} ({c.get('url','')})" for c in citation_map) or "No sources available."

        prompt = f"Sources:\n{sources_text}\n\nArticle:\n{draft[:6000]}\n\nReturn the JSON now."
        raw = await self.llm.generate(self.SYSTEM, prompt, temperature=0.1)
        report = self._safe_json(raw)

        return AgentMessage(sender=self.name, receiver="orchestrator", type="result", payload=report)

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
            return {"flagged_claims": [], "citation_coverage_pct": 0, "overall_verdict": "unable to verify"}
