from .base import BaseAgent, AgentMessage
import textstat


class ReviewerAgent(BaseAgent):
    name = "reviewer_agent"

    SYSTEM = (
        "You are a senior editor. Improve grammar, clarity, flow, and tone consistency of the "
        "given Markdown article without changing factual content or removing citation markers "
        "like [1], [2]. Keep all headings. Return the FULL improved Markdown article only, no commentary."
    )

    async def run(self, task_payload: dict) -> AgentMessage:
        draft = task_payload["draft_markdown"]
        tone = task_payload.get("tone", "professional")

        prompt = f"Target tone: {tone}\n\nArticle:\n{draft[:7000]}\n\nReturn the improved full article now."
        improved = await self.llm.generate(self.SYSTEM, prompt, temperature=0.3, max_tokens=2500)

        readability = {
            "flesch_reading_ease": round(textstat.flesch_reading_ease(improved), 1),
            "flesch_kincaid_grade": round(textstat.flesch_kincaid_grade(improved), 1),
            "word_count": len(improved.split()),
        }

        return AgentMessage(
            sender=self.name,
            receiver="orchestrator",
            type="result",
            payload={"final_markdown": improved, "readability": readability},
        )
