import React, { useState } from 'react'
import { Feather } from 'lucide-react'

export default function ContentForm({ onSubmit, busy }) {
  const [topic, setTopic] = useState('')
  const [contentType, setContentType] = useState('blog')
  const [tone, setTone] = useState('professional, engaging')
  const [keywords, setKeywords] = useState('')
  const [provider, setProvider] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!topic.trim()) return
    onSubmit({
      topic,
      content_type: contentType,
      tone,
      keywords: keywords.split(',').map(k => k.trim()).filter(Boolean),
      llm_provider: provider || null,
    })
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <span className="card-label">Commission a piece</span>
      <div className="field">
        <label>Topic / brief</label>
        <textarea
          placeholder="e.g. The state of on-device AI in 2026, written for a developer audience"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          required
        />
      </div>
      <div className="row-2">
        <div className="field">
          <label>Content type</label>
          <select value={contentType} onChange={e => setContentType(e.target.value)}>
            <option value="blog">Blog post</option>
            <option value="article">Long-form article</option>
            <option value="social_post">Social media post</option>
            <option value="marketing_copy">Marketing copy</option>
            <option value="landing_page">Landing page copy</option>
          </select>
        </div>
        <div className="field">
          <label>Tone</label>
          <input value={tone} onChange={e => setTone(e.target.value)} placeholder="professional, witty, technical..." />
        </div>
      </div>
      <div className="field">
        <label>Target keywords (comma separated, optional)</label>
        <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="on-device AI, edge inference, llama" />
      </div>
      <div className="field">
        <label>LLM backend (optional override)</label>
        <select value={provider} onChange={e => setProvider(e.target.value)}>
          <option value="">Use server default</option>
          <option value="ollama">Ollama (Llama 3 / local, open-source)</option>
          <option value="gemini">Google Gemini</option>
          <option value="openai_compatible">OpenAI-compatible endpoint</option>
        </select>
      </div>
      <button className="btn-primary" type="submit" disabled={busy}>
        <Feather size={14} />
        {busy ? 'Running the press…' : 'Generate content'}
      </button>
    </form>
  )
}
