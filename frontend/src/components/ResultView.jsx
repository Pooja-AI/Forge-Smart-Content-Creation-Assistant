import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download, ShieldCheck, Search, Gauge } from 'lucide-react'

const API = ''

export default function ResultView({ result, jobId }) {
  const [editText, setEditText] = useState(result.final_markdown)
  const [savedMsg, setSavedMsg] = useState('')

  if (!result) return null
  const { plan, seo, fact_check, readability, quality, citations, research_summary } = result

  async function exportAs(format) {
    window.open(`/api/export/${jobId}?format=${format}`, '_blank')
  }

  async function saveEdit() {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, section_edits: editText, approve: true }),
    })
    if (res.ok) setSavedMsg('Saved — version updated.')
  }

  return (
    <div className="two-col" style={{ marginTop: 24 }}>
      <div>
        <div className="card">
          <span className="card-label">Final draft — editable</span>
          <textarea
            style={{ width: '100%', minHeight: 420, fontFamily: 'var(--mono)', fontSize: 13, lineHeight: 1.6, border: '1px solid var(--rule)', padding: 14, background: 'var(--paper)' }}
            value={editText}
            onChange={e => setEditText(e.target.value)}
          />
          <div className="export-row">
            <button className="btn-ghost" onClick={saveEdit}>Save edit (human review)</button>
            {savedMsg && <span className="muted" style={{ alignSelf: 'center' }}>{savedMsg}</span>}
          </div>
        </div>

        <div className="card">
          <span className="card-label">Rendered preview</span>
          <div className="article-render">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{editText}</ReactMarkdown>
          </div>
          <hr className="divider" />
          <div className="export-row">
            <button className="btn-primary" onClick={() => exportAs('markdown')}><Download size={13} /> Markdown</button>
            <button className="btn-primary" onClick={() => exportAs('html')}><Download size={13} /> HTML</button>
            <button className="btn-primary" onClick={() => exportAs('docx')}><Download size={13} /> DOCX</button>
            <button className="btn-primary" onClick={() => exportAs('pdf')}><Download size={13} /> PDF</button>
          </div>
        </div>
      </div>

      <div>
        <div className="card">
          <span className="card-label"><Gauge size={12} style={{ verticalAlign: -2 }} /> Quality evaluation</span>
          <div className="metric-grid">
            <div className="metric-box"><div className="val">{quality.overall_quality_score}</div><div className="lbl">Overall</div></div>
            <div className="metric-box"><div className="val">{quality.faithfulness}</div><div className="lbl">Faithfulness</div></div>
            <div className="metric-box"><div className="val">{quality.answer_relevancy}</div><div className="lbl">Relevancy</div></div>
            <div className="metric-box"><div className="val">{quality.context_precision}</div><div className="lbl">Ctx. precision</div></div>
          </div>
          <hr className="divider" />
          <p className="muted">Readability: Flesch ease {readability.flesch_reading_ease} · Grade {readability.flesch_kincaid_grade} · {readability.word_count} words</p>
        </div>

        <div className="card">
          <span className="card-label"><Search size={12} style={{ verticalAlign: -2 }} /> SEO metadata</span>
          <p><strong>{seo.meta_title}</strong></p>
          <p className="muted">{seo.meta_description}</p>
          <p className="muted">/{seo.slug}</p>
          <div style={{ marginTop: 10 }}>
            {[seo.primary_keyword, ...(seo.secondary_keywords || [])].filter(Boolean).map((k, i) => (
              <span className="tag" key={i}>{k}</span>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 10 }}>SEO score: <strong>{seo.seo_score}</strong>/100</p>
        </div>

        <div className="card">
          <span className="card-label"><ShieldCheck size={12} style={{ verticalAlign: -2 }} /> Fact-check report</span>
          <p className="muted">{fact_check.overall_verdict}</p>
          <p className="muted">Citation coverage: {fact_check.citation_coverage_pct}%</p>
          {(fact_check.flagged_claims || []).map((c, i) => (
            <div key={i} style={{ marginTop: 8 }}>
              <span className={`tag severity-${c.severity}`}>{c.severity}</span>
              <p style={{ fontSize: 13, margin: '4px 0' }}>{c.claim}</p>
              <p className="muted" style={{ fontSize: 12 }}>{c.issue}</p>
            </div>
          ))}
        </div>

        <div className="card">
          <span className="card-label">Sources used</span>
          {citations.length === 0 && <p className="muted">No external sources cited.</p>}
          {citations.map((c, i) => (
            <div className="source-item" key={i}>
              <div className="src-title">[{c.id}] {c.title}</div>
              {c.url && <div className="src-url">{c.url}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
