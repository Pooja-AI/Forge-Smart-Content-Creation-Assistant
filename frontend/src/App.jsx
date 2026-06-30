import React, { useState, useRef } from 'react'
import { Printer, BarChart3 } from 'lucide-react'
import ContentForm from './components/ContentForm.jsx'
import PressLine from './components/PressLine.jsx'
import ResultView from './components/ResultView.jsx'
import Dashboard from './components/Dashboard.jsx'

export default function App() {
  const [view, setView] = useState('studio') // studio | dashboard
  const [busy, setBusy] = useState(false)
  const [stageStatus, setStageStatus] = useState({})
  const [result, setResult] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  async function handleGenerate(payload) {
    setBusy(true)
    setResult(null)
    setError(null)
    setStageStatus({})

    try {
      const resp = await fetch('/api/content/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop()

        for (const chunk of chunks) {
          const lines = chunk.split('\n')
          let eventType = 'message'
          let data = ''
          for (const line of lines) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            if (line.startsWith('data:')) data += line.slice(5).trim()
          }
          if (!data) continue
          const parsed = JSON.parse(data)

          if (eventType === 'progress') {
            setStageStatus(prev => ({ ...prev, [parsed.stage]: parsed.status === 'done' ? 'done' : (parsed.status === 'failed' ? 'failed' : 'running') }))
            if (parsed.stage === 'error') setError(parsed.data?.message || 'Pipeline failed')
          } else if (eventType === 'result') {
            if (parsed && parsed.job_id) {
              setResult(parsed)
              setJobId(parsed.job_id)
            }
          }
        }
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="masthead">
        <div>
          <div className="masthead-title">
            <Printer size={30} />
            FORGE <span className="accent">Content Studio</span>
          </div>
          <div className="masthead-sub">Multi-agent · RAG · SEO · Fact-checked content production</div>
        </div>
        <div className="masthead-nav">
          <button className={view === 'studio' ? 'active' : ''} onClick={() => setView('studio')}>Studio</button>
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}><BarChart3 size={12} style={{ verticalAlign: -1 }} /> Dashboard</button>
        </div>
      </div>

      {view === 'dashboard' ? (
        <Dashboard />
      ) : (
        <>
          <ContentForm onSubmit={handleGenerate} busy={busy} />

          {(busy || Object.keys(stageStatus).length > 0) && (
            <div style={{ marginTop: 20 }}>
              <h3 className="section-title">Production line</h3>
              <PressLine stageStatus={stageStatus} />
            </div>
          )}

          {error && (
            <div className="card" style={{ borderColor: 'var(--crimson)', marginTop: 20 }}>
              <p style={{ color: 'var(--crimson)' }}>⚠ {error}</p>
            </div>
          )}

          {!busy && !result && !error && (
            <div className="empty-state">
              <Printer size={40} className="icon" />
              <p>Commission a piece above and watch the agent press run — plan, research, write, optimize, fact-check, and review.</p>
            </div>
          )}

          {result && <ResultView result={result} jobId={jobId} />}
        </>
      )}
    </div>
  )
}
