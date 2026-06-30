# Forge — Smart Content Creation Assistant

An end-to-end, multi-agent AI content platform: SEO-optimized blogs, articles, and
marketing copy generated through a pipeline of cooperating agents (Planner →
Researcher/RAG → Writer → SEO → Fact-Checker → Reviewer), with live progress
streaming, human-in-the-loop editing, multi-format export, and an analytics
dashboard.

Built with **open-source LLMs** (Ollama / Llama 3 by default — Gemini and any
OpenAI-compatible endpoint, e.g. vLLM, are supported as drop-in alternatives),
a **multi-agent architecture** with an A2A (agent-to-agent) message protocol,
an **MCP-style tool registry** for web search / RAG, **Retrieval-Augmented
Generation** via ChromaDB, a **FastAPI** backend, and a **React + Vite**
frontend.

## Architecture

```
React (Vite) UI  ──SSE──▶  FastAPI  ──▶  Orchestrator
                                            │
        ┌───────────────┬───────────────┬──┴──────────┬───────────────┬───────────────┐
   Planner Agent   Research Agent   Writer Agent    SEO Agent   Fact-Checker Agent  Reviewer Agent
        │                │                                                              │
        │           ┌────┴────┐                                                         │
        │       Web Search  RAG / ChromaDB                                       Quality Evaluator
        │        (MCP tool) (MCP tool)                                            (Ragas/DeepEval-
        └──────────────────────────────────────────────────────────────────────────style heuristics)
                                            │
                                  LLM Client (pluggable)
                                  Ollama | Gemini | OpenAI-compatible
```

Each agent emits structured `AgentMessage` objects (the **A2A protocol**, see
`backend/app/agents/base.py`). Tools (`web_search`, `rag_query`, `rag_ingest`)
are exposed through a small **MCP-style registry** (`backend/app/mcp_tools.py`)
so they can later be wired into a real MCP server for external MCP clients.

## Workflow implemented

1. User submits a topic/content request (React form)
2. Intent detection & prompt enrichment
3. **Planner Agent** produces a structured content plan (JSON: sections, audience, keywords, search queries)
4. **Research Agent** runs web search (DuckDuckGo, no API key needed) + RAG retrieval from ChromaDB
5. Knowledge retrieval is hybrid: vector similarity + keyword re-rank
6. **Writer Agent** drafts each section in Markdown with inline citation markers
7. **SEO Agent** generates meta title/description, slug, keywords, and an SEO score
8. **Fact-Checker Agent** flags unsupported/fabricated claims and scores citation coverage
9. **Reviewer Agent** polishes grammar/tone/readability and computes Flesch scores
10. **Quality Evaluator** scores faithfulness / relevancy / context precision (Ragas/DeepEval-style)
11. Human-in-the-loop: edit the draft in the UI and save (versioned)
12. Export to **PDF, DOCX, HTML, or Markdown**

Progress streams live to the UI via Server-Sent Events, visualized as a
"press line" of agent stations lighting up as they work.

## Project layout

```
smart-content-platform/
├── backend/
│   ├── app/
│   │   ├── agents/            # Planner, Research, Writer, SEO, FactChecker, Reviewer, base (A2A), quality eval
│   │   ├── llm/                # Pluggable LLM client (Ollama / Gemini / OpenAI-compatible)
│   │   ├── rag/                # ChromaDB vector store + hybrid retrieval
│   │   ├── export/              # PDF / DOCX / HTML / Markdown exporters
│   │   ├── mcp_tools.py        # MCP-style tool registry (web_search, rag_query, rag_ingest)
│   │   ├── orchestrator.py     # Runs the full agent pipeline, streams progress
│   │   ├── models.py           # Pydantic request/response schemas
│   │   └── main.py             # FastAPI app & routes
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/         # ContentForm, PressLine, ResultView, Dashboard
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css           # "Press room" editorial design system
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

## Quick start (Docker, recommended)

```bash
docker compose up -d --build
# Pull an open-source model into Ollama (first run only):
docker exec -it forge-ollama ollama pull llama3
```

Open the UI at **http://localhost:5173**. The API is at **http://localhost:8000**
(docs at `/docs`).

## Quick start (local dev, no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Install & run Ollama separately (https://ollama.com), then:
ollama pull llama3

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173**.

## Switching LLM providers

Set `LLM_PROVIDER` in `backend/.env` (or override per-request from the UI's
"LLM backend" dropdown):

- `ollama` — fully open-source, local, default (`llama3`, `mistral`, `qwen2`, etc.)
- `gemini` — set `GEMINI_API_KEY`
- `openai_compatible` — point `OPENAI_COMPATIBLE_BASE_URL` at vLLM, LM Studio, TGI, Groq, etc.

## Key API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/content/generate` | Run the full multi-agent pipeline (SSE stream) |
| GET | `/api/content/{job_id}` | Fetch a job's status/result |
| POST | `/api/knowledge/ingest` | Add documents to the RAG knowledge base |
| GET | `/api/knowledge/stats` | Vector DB stats |
| POST | `/api/feedback` | Human-in-the-loop edits / approval |
| GET | `/api/export/{job_id}?format=pdf\|docx\|html\|markdown` | Export final content |
| GET | `/api/analytics/overview` | Dashboard metrics |
| GET | `/api/tools` | MCP-style tool discovery |

## Notes & production hardening ideas

- Job/version storage is in-memory (`JOBS` dict) — swap for Postgres/Redis for production.
- `quality_evaluator.py` uses fast heuristics inspired by Ragas/DeepEval metrics
  with zero extra dependencies; swap in real `ragas`/`deepeval` LLM-judge calls
  if you have an evaluation budget.
- `mcp_tools.py` is a minimal MCP-style registry; wire it into the official
  `mcp` Python SDK to expose these tools to external MCP clients (Claude
  Desktop, Claude Code, etc.) over stdio/SSE.
- Web search uses DuckDuckGo (no API key). Swap in Tavily/SerpAPI/Bing for
  higher-volume production use.
