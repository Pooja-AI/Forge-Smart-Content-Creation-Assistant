import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from sse_starlette.sse import EventSourceResponse

from .models import ContentRequest, FeedbackRequest, IngestRequest
from .orchestrator import Orchestrator, JOBS, new_job_id
from .rag import vector_store
from .export import exporters
from . import mcp_tools

app = FastAPI(title="Smart Content Creation Assistant API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "vector_db": vector_store.stats()}


@app.get("/api/tools")
async def list_tools():
    """MCP-style tool discovery endpoint."""
    return mcp_tools.list_tools()


@app.post("/api/content/generate")
async def generate_content(req: ContentRequest):
    """
    Kicks off the multi-agent pipeline and streams progress via SSE.
    Frontend connects to this endpoint with EventSource-compatible POST-then-stream
    pattern (we return job_id immediately is avoided; instead we stream directly).
    """
    job_id = new_job_id()
    orchestrator = Orchestrator(provider=req.llm_provider)
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event):
        await queue.put(event)

    async def run_and_close():
        try:
            await orchestrator.run_pipeline(req.model_dump(), job_id, on_event=on_event)
        except Exception as e:
            await queue.put({"stage": "error", "status": "failed", "data": {"message": str(e)}})
        finally:
            await queue.put(None)  # sentinel

    task = asyncio.create_task(run_and_close())

    async def event_generator():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield {"event": "progress", "data": json.dumps(event)}
        result = JOBS.get(job_id, {}).get("result")
        yield {"event": "result", "data": json.dumps(result or {})}

    return EventSourceResponse(event_generator())


@app.get("/api/content/{job_id}")
async def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/knowledge/ingest")
async def ingest(req: IngestRequest):
    n = vector_store.add_documents(req.texts, source=req.source)
    return {"chunks_ingested": n, "stats": vector_store.stats()}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    return vector_store.stats()


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    job = JOBS.get(req.job_id)
    if not job or not job.get("result"):
        raise HTTPException(404, "Job not found or not completed")
    if req.section_edits:
        job["result"]["final_markdown"] = req.section_edits
        job["result"]["version"] = job["result"].get("version", 1) + 1
    job["result"]["human_approved"] = req.approve
    return {"status": "updated", "version": job["result"]["version"]}


@app.get("/api/export/{job_id}")
async def export_content(job_id: str, format: str = "markdown"):
    job = JOBS.get(job_id)
    if not job or not job.get("result"):
        raise HTTPException(404, "Job not found or not completed")

    md_text = job["result"]["final_markdown"]
    title = job["result"]["plan"].get("title", "content")
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_") or "content"

    if format == "markdown":
        data = exporters.to_markdown_bytes(md_text)
        media_type, ext = "text/markdown", "md"
    elif format == "html":
        data = exporters.to_html_bytes(md_text, title)
        media_type, ext = "text/html", "html"
    elif format == "docx":
        data = exporters.to_docx_bytes(md_text, title)
        media_type, ext = "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
    elif format == "pdf":
        data = exporters.to_pdf_bytes(md_text, title)
        media_type, ext = "application/pdf", "pdf"
    else:
        raise HTTPException(400, "Unsupported format. Use markdown|html|docx|pdf")

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.{ext}"'},
    )


@app.get("/api/analytics/overview")
async def analytics_overview():
    """Aggregate simple analytics across all generated jobs (for the dashboard)."""
    completed = [j for j in JOBS.values() if j.get("status") == "completed" and j.get("result")]
    if not completed:
        return {"total_jobs": 0, "avg_quality_score": 0, "avg_word_count": 0, "avg_seo_score": 0}

    avg_quality = sum(j["result"]["quality"]["overall_quality_score"] for j in completed) / len(completed)
    avg_words = sum(j["result"]["quality"]["word_count"] for j in completed) / len(completed)
    avg_seo = sum(j["result"]["seo"].get("seo_score", 0) for j in completed) / len(completed)

    return {
        "total_jobs": len(JOBS),
        "completed_jobs": len(completed),
        "avg_quality_score": round(avg_quality, 1),
        "avg_word_count": round(avg_words, 1),
        "avg_seo_score": round(avg_seo, 1),
    }
