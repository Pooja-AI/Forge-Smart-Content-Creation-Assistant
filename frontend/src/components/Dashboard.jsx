import React, { useEffect, useState } from 'react'

export default function Dashboard() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetch('/api/analytics/overview').then(r => r.json()).then(setStats)
  }, [])

  if (!stats) return <div className="card"><p className="muted">Loading analytics…</p></div>

  return (
    <div className="card">
      <span className="card-label">Production analytics</span>
      <div className="metric-grid">
        <div className="metric-box"><div className="val">{stats.total_jobs}</div><div className="lbl">Total jobs</div></div>
        <div className="metric-box"><div className="val">{stats.completed_jobs || 0}</div><div className="lbl">Completed</div></div>
        <div className="metric-box"><div className="val">{stats.avg_quality_score}</div><div className="lbl">Avg quality</div></div>
        <div className="metric-box"><div className="val">{stats.avg_seo_score}</div><div className="lbl">Avg SEO score</div></div>
      </div>
      <p className="muted" style={{ marginTop: 14 }}>Avg word count per piece: {stats.avg_word_count}</p>
    </div>
  )
}
