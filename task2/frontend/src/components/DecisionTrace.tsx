import React, { useMemo } from "react"
import { ChatMessage, Decision } from "../types"

export default function DecisionTrace({ decisions, chats }: { decisions: Decision[]; chats: ChatMessage[] }) {
  const chatIndex = useMemo(() => {
    const m = new Map<number, ChatMessage>()
    chats.forEach((c) => m.set(c.id, c))
    return m
  }, [chats])

  return (
    <div className="card">
      <h3>Decisions & Traceback</h3>
      {decisions.map((d) => (
        <div key={d.id} style={{ marginBottom: 16, borderTop: "1px solid #203056", paddingTop: 12 }}>
          <div className="badge">{d.date}</div>
          <h4 style={{ margin: "8px 0" }}>{d.title}</h4>
          <p style={{ color: "#cbd5e1" }}>{d.description}</p>
          <div>
            <strong>Reasons</strong>
            <ul>
              {d.reasons.map((r, idx) => (
                <li key={idx}>
                  {r.text}{" "}
                  {r.evidence_ids.length > 0 && (
                    <span style={{ color: "#93c5fd" }}>
                      (evidence: {r.evidence_ids.map((id) => `[${id}]`).join(", ")})
                    </span>
                  )}
                  {r.evidence_ids.length > 0 && (
                    <div className="code" style={{ marginTop: 6 }}>
                      {r.evidence_ids.map((cid) => {
                        const c = chatIndex.get(cid)
                        return c ? (
                          <div key={cid}>
                            [{c.id}] {c.date} <strong>{c.sender}:</strong> {c.text}
                          </div>
                        ) : null
                      })}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ))}
    </div>
  )
}
