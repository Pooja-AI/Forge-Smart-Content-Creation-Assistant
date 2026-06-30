"""
Quality evaluation layer inspired by Ragas / DeepEval metrics:
- faithfulness (claims grounded in sources)
- answer_relevancy (content matches the planned topic/keywords)
- context_precision (how much of retrieved context was actually used)

Implemented as fast heuristics so the project runs with zero extra API
dependencies; swap in real `ragas`/`deepeval` calls here if you have an
evaluation LLM budget.
"""
import re


def evaluate(final_markdown: str, plan: dict, research: dict, fact_report: dict) -> dict:
    word_count = len(final_markdown.split())
    keyword_hits = 0
    keywords = plan.get("target_keywords", []) or []
    lowered = final_markdown.lower()
    for kw in keywords:
        if kw.lower() in lowered:
            keyword_hits += 1
    answer_relevancy = round((keyword_hits / max(len(keywords), 1)) * 100, 1) if keywords else 75.0

    citation_markers = len(re.findall(r"\[\d+\]", final_markdown))
    sources_available = len(research.get("web_results", [])) + len(research.get("rag_results", []))
    context_precision = round(min(citation_markers / max(sources_available, 1), 1.0) * 100, 1)

    high_severity_flags = len([c for c in fact_report.get("flagged_claims", []) if c.get("severity") == "high"])
    faithfulness = max(0, 100 - high_severity_flags * 20 - len(fact_report.get("flagged_claims", [])) * 5)

    overall = round((answer_relevancy + context_precision + faithfulness) / 3, 1)

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "overall_quality_score": overall,
        "word_count": word_count,
        "citation_markers_used": citation_markers,
    }
