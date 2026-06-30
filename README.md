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

**Author:** Pooja Sunkara

---

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

---

## Steps to Run

### Option A — Docker (recommended)

**1. Unzip the project**
```bash
unzip smart-content-platform.zip
cd smart-content-platform
```

**2. Make sure Docker + Docker Compose are installed, then build and start everything**
```bash
docker compose up -d --build
```
This builds and starts 3 containers: `forge-ollama`, `forge-backend`, `forge-frontend`.

**3. Pull an open-source LLM into Ollama (first time only)**
```bash
docker exec -it forge-ollama ollama pull llama3
```
Wait for the download to finish (~4.7GB for llama3).

**4. Open the app**
- UI: http://localhost:5173
- API docs: http://localhost:8000/docs

**5. Check logs if something fails**
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

**Stop everything**
```bash
docker compose down
```

### Option B — Run locally without Docker

**1. Install and start Ollama**
- Download from https://ollama.com
```bash
ollama serve          # starts the Ollama server (often auto-starts)
ollama pull llama3    # downloads the model
```

**2. Backend setup**
```bash
cd smart-content-platform/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Leave `.env` as-is for Ollama defaults (already points to `http://localhost:11434`, model `llama3`).

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```
Check it's up: http://localhost:8000/api/health

**3. Frontend setup (new terminal)**
```bash
cd smart-content-platform/frontend
npm install
npm run dev
```
Open http://localhost:5173 — Vite proxies `/api` calls to the backend automatically (see `vite.config.js`).

### Using a different LLM (no local GPU? skip Ollama)

Edit `backend/.env`:

- **Gemini** (cloud, just needs an API key):
  ```
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=your_key_here
  ```
- **Any OpenAI-compatible host** (Groq, LM Studio, vLLM):
  ```
  LLM_PROVIDER=openai_compatible
  OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1
  OPENAI_COMPATIBLE_API_KEY=your_key
  OPENAI_COMPATIBLE_MODEL=llama-3.1-70b-versatile
  ```
You can also override the provider per-request from the "LLM backend" dropdown in the UI without restarting anything.

### Quick smoke test once it's running

1. Go to http://localhost:5173
2. Type a topic, e.g. "Benefits of intermittent fasting for software engineers"
3. Click **Generate content** and watch the press line light up stage by stage
4. When done, review the draft, check the SEO/fact-check panels, and try exporting as PDF or DOCX

If a stage hangs at "Working" for a long time, it's almost always Ollama still loading the model into memory on first request — check `docker compose logs -f ollama`.

---

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

---

## Credits

Designed and built by **Pooja Sunkara**.
