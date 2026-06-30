import time
import uuid
from .agents.planner_agent import PlannerAgent
from .agents.research_agent import ResearchAgent
from .agents.writer_agent import WriterAgent
from .agents.seo_agent import SEOAgent
from .agents.fact_checker_agent import FactCheckerAgent
from .agents.reviewer_agent import ReviewerAgent
from .agents import quality_evaluator
from .llm.llm_client import get_llm_client

# In-memory job + version store (swap for Postgres/Redis in production)
JOBS: dict[str, dict] = {}


class Orchestrator:
    def __init__(self, provider: str = None):
        self.llm = get_llm_client(provider)
        self.planner = PlannerAgent(self.llm)
        self.researcher = ResearchAgent(self.llm)
        self.writer = WriterAgent(self.llm)
        self.seo = SEOAgent(self.llm)
        self.fact_checker = FactCheckerAgent(self.llm)
        self.reviewer = ReviewerAgent(self.llm)

    async def run_pipeline(self, request: dict, job_id: str, on_event=None):
        async def emit(stage, status, data=None):
            event = {"stage": stage, "status": status, "data": data, "ts": time.time()}
            JOBS[job_id]["events"].append(event)
            if on_event:
                await on_event(event)

        JOBS[job_id] = {"status": "running", "events": [], "result": None, "created_at": time.time()}

        try:
            await emit("intent_detection", "running")
            topic = request["topic"]
            await emit("intent_detection", "done", {"topic": topic})

            await emit("planning", "running")
            plan_msg = await self.planner.run(request)
            plan = plan_msg.payload
            await emit("planning", "done", plan)

            await emit("research", "running")
            research_msg = await self.researcher.run({"search_queries": plan.get("search_queries", []), "topic": topic})
            research = research_msg.payload
            await emit("research", "done", {
                "web_count": len(research.get("web_results", [])),
                "rag_count": len(research.get("rag_results", [])),
            })

            await emit("writing", "running")
            writer_msg = await self.writer.run({"plan": plan, "research": research})
            draft = writer_msg.payload
            await emit("writing", "done", {"word_count": len(draft["draft_markdown"].split())})

            await emit("seo_optimization", "running")
            seo_msg = await self.seo.run({
                "draft_markdown": draft["draft_markdown"],
                "target_keywords": plan.get("target_keywords", []),
            })
            seo_meta = seo_msg.payload
            await emit("seo_optimization", "done", seo_meta)

            await emit("fact_checking", "running")
            fact_msg = await self.fact_checker.run({
                "draft_markdown": draft["draft_markdown"],
                "citation_map": draft["citation_map"],
            })
            fact_report = fact_msg.payload
            await emit("fact_checking", "done", fact_report)

            await emit("review", "running")
            review_msg = await self.reviewer.run({"draft_markdown": draft["draft_markdown"], "tone": plan.get("tone")})
            review = review_msg.payload
            await emit("review", "done", {"readability": review["readability"]})

            await emit("quality_evaluation", "running")
            quality = quality_evaluator.evaluate(review["final_markdown"], plan, research, fact_report)
            await emit("quality_evaluation", "done", quality)

            result = {
                "job_id": job_id,
                "plan": plan,
                "research_summary": {
                    "web_results": research.get("web_results", []),
                    "rag_results": research.get("rag_results", []),
                },
                "citations": draft["citation_map"],
                "seo": seo_meta,
                "fact_check": fact_report,
                "readability": review["readability"],
                "quality": quality,
                "final_markdown": review["final_markdown"],
                "version": 1,
            }
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["result"] = result
            await emit("complete", "done", {"job_id": job_id})
            return result

        except Exception as e:
            JOBS[job_id]["status"] = "failed"
            await emit("error", "failed", {"message": str(e)})
            raise


def new_job_id() -> str:
    return str(uuid.uuid4())
