import React from "react"
import { Episode } from "../types"

export default function EpisodeDetails({ ep }: { ep: Episode | null }) {
  if (!ep) return null
  return (
    <div className="card">
      <div className="badge">{ep.start_date} → {ep.end_date}</div>
      <h3 style={{ marginTop: 8 }}>{ep.title}</h3>
      <p><strong>Goal:</strong> {ep.goal}</p>
      <p><strong>Triggered by:</strong> {ep.triggered_by}</p>
      <p><strong>Outcome:</strong> {ep.outcome}</p>
      <div className="row">
        <div className="item">
          <div className="badge">Response Time</div>
          <h2>{Math.round(ep.response_time_minutes)} min</h2>
        </div>
        <div className="item">
          <div className="badge">Time to Resolution</div>
          <h2>{Math.round(ep.time_to_resolution_minutes/1440)} days</h2>
        </div>
      </div>
      {ep.friction_points.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <strong>Friction Points</strong>
          <ul>
            {ep.friction_points.map((fp) => <li key={fp.id ?? fp.text}>{fp.text}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
