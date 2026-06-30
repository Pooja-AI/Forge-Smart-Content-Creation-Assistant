from .base import BaseAgent, AgentMessage


class WriterAgent(BaseAgent):
    name = "writer_agent"

    SYSTEM = (
        "You are an expert long-form content writer. Write clear, well-structured, accurate, "
        "engaging Markdown content for the given section. Use the provided research context "
        "(web + knowledge base) to ground factual claims, and add inline citation markers like "
        "[1], [2] that map to the provided source list when you use a specific fact. "
        "Do not fabricate statistics. If context is insufficient, write from general knowledge "
        "but keep claims conservative. Output Markdown only for this section (start with the '## ' heading)."
    )

    async def run(self, task_payload: dict) -> AgentMessage:
        plan = task_payload["plan"]
        research = task_payload["research"]
        tone = plan.get("tone", "professional")

        sources_text = self._format_sources(research)

        sections_md = []
        citation_map = self._build_citation_map(research)

        for section in plan.get("sections", []):
            prompt = (
                f"Article title: {plan.get('title')}\n"
                f"Audience: {plan.get('audience')}\n"
                f"Tone: {tone}\n"
                f"Section heading: {section['heading']}\n"
                f"Key points to cover: {', '.join(section.get('key_points', []))}\n\n"
                f"Available research sources (numbered, use [n] inline when citing):\n{sources_text}\n\n"
                "Write this section now (300-500 words), Markdown, starting with '## ' heading."
            )
            content = await self.llm.generate(self.SYSTEM, prompt, temperature=0.55, max_tokens=900)
            sections_md.append(content.strip())

        full_draft = f"# {plan.get('title')}\n\n" + "\n\n".join(sections_md)

        return AgentMessage(
            sender=self.name,
            receiver="orchestrator",
            type="result",
            payload={"draft_markdown": full_draft, "citation_map": citation_map},
        )

    @staticmethod
    def _format_sources(research: dict) -> str:
        lines = []
        idx = 1
        for r in research.get("web_results", []):
            if r.get("url"):
                lines.append(f"[{idx}] {r.get('title')} - {r.get('snippet', '')[:200]} ({r.get('url')})")
                idx += 1
        for r in research.get("rag_results", []):
            lines.append(f"[{idx}] Knowledge base: {r['text'][:200]}")
            idx += 1
        return "\n".join(lines) if lines else "No external sources retrieved; rely on general knowledge."

    @staticmethod
    def _build_citation_map(research: dict) -> list[dict]:
        citations = []
        idx = 1
        for r in research.get("web_results", []):
            if r.get("url"):
                citations.append({"id": idx, "title": r.get("title"), "url": r.get("url")})
                idx += 1
        for r in research.get("rag_results", []):
            citations.append({"id": idx, "title": "Knowledge base excerpt", "url": r["metadata"].get("source", "")})
            idx += 1
        return citations
