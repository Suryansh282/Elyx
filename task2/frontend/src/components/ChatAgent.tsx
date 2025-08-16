import React, { useState } from "react"
import { askWhy } from "../api"
import { WhyResponse } from "../types"

export default function ChatAgent({ memberId }: { memberId: number }) {
  const [q, setQ] = useState("Why was the Hotel Gym Workout Plan chosen?")
  const [resp, setResp] = useState<WhyResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const onAsk = async () => {
    setLoading(true)
    try {
      const r = await askWhy(memberId, q)
      setResp(r)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h3>Ask “Why?” (Traceback)</h3>
      <textarea className="textarea" value={q} onChange={(e)=>setQ(e.target.value)} />
      <div style={{ marginTop: 8 }}>
        <button className="btn" onClick={onAsk} disabled={loading}>{loading ? "Thinking..." : "Ask"}</button>
      </div>
      {resp && (
        <div style={{ marginTop: 12 }}>
          <div className="badge">Answer</div>
          <div className="code" style={{ marginTop: 6 }}>{resp.answer}</div>
          {resp.evidence_chat?.length > 0 && (
            <>
              <div className="badge" style={{ marginTop: 8 }}>Evidence</div>
              <div className="code" style={{ marginTop: 6 }}>
                {resp.evidence_chat.map(c => (
                  <div key={c.id}>
                    [{c.id}] {c.date} <strong>{c.sender}:</strong> {c.text}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
