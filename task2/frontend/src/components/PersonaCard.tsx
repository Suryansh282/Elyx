import React from "react"

export default function PersonaCard({ before, after }: { before: string; after: string }) {
  return (
    <div className="card">
      <h3>Persona Analysis</h3>
      <div className="row">
        <div className="item">
          <div className="badge">Before</div>
          <p>{before}</p>
        </div>
        <div className="item">
          <div className="badge">After</div>
          <p>{after}</p>
        </div>
      </div>
    </div>
  )
}
