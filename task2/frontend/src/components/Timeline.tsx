import React from "react"
import { Episode } from "../types"

type Props = {
  episodes: Episode[]
  currentId?: number
  onSelect: (id: number) => void
}

export default function Timeline({ episodes, currentId, onSelect }: Props) {
  return (
    <div className="card">
      <h3>Member Journey Timeline</h3>
      <div className="timeline">
        {episodes.map((e) => (
          <div
            key={e.id}
            className={"dot " + (e.id === currentId ? "active" : "")}
            data-label={`${e.title}`}
            onClick={() => onSelect(e.id)}
            title={`${e.title} (${e.start_date} → ${e.end_date})`}
          />
        ))}
      </div>
    </div>
  )
}
