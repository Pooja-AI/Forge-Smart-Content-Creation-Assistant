import React from 'react'

const STAGES = [
  { key: 'intent_detection', name: 'Intent' },
  { key: 'planning', name: 'Planner' },
  { key: 'research', name: 'Research' },
  { key: 'writing', name: 'Writer' },
  { key: 'seo_optimization', name: 'SEO' },
  { key: 'fact_checking', name: 'Fact-Check' },
  { key: 'review', name: 'Reviewer' },
  { key: 'quality_evaluation', name: 'Quality' },
]

export default function PressLine({ stageStatus }) {
  return (
    <div className="press-line">
      {STAGES.map((s, i) => {
        const status = stageStatus[s.key] || 'pending'
        return (
          <div key={s.key} className={`press-station ${status}`}>
            <span className="num">{String(i + 1).padStart(2, '0')}</span>
            <span className="name">{s.name}</span>
            <span>
              <span className="status-dot" />
              <span className="status-text">
                {status === 'pending' && 'Waiting'}
                {status === 'running' && 'Working'}
                {status === 'done' && 'Done'}
                {status === 'failed' && 'Failed'}
              </span>
            </span>
          </div>
        )
      })}
    </div>
  )
}
