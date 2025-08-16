import React, { useMemo } from "react"
import { InternalMetrics } from "../types"
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, BarChart, Bar, Legend } from "recharts"

const COLORS = {
  doctorLine: "#38bdf8", // sky-400
  coachLine:  "#a78bfa", // violet-400
  doctorBar:  "#22c55e", // green-500
  coachBar:   "#f59e0b", // amber-500
  grid:       "#334155", // slate-700
  axis:       "#94a3b8", // slate-400
  tooltipBg:  "#0f1930",
  tooltipBd:  "#203056",
}

export default function MetricsDashboard({ metrics }: { metrics: InternalMetrics | null }) {
  const dayData = useMemo(() => {
    if (!metrics) return []
    const grouped: Record<string, { date: string; doctor: number; coach: number }> = {}
    for (const it of metrics.per_day_hours) {
      if (!grouped[it.date]) grouped[it.date] = { date: it.date, doctor: 0, coach: 0 }
      if (it.role === "doctor") grouped[it.date].doctor += it.hours
      if (it.role === "coach") grouped[it.date].coach += it.hours
    }
    const arr = Object.values(grouped)
    arr.sort((a, b) => a.date.localeCompare(b.date))
    return arr
  }, [metrics])

  if (!metrics) return null

  const barData = [
    { name: "Doctor", hours: metrics.doctor_hours_total, fill: COLORS.doctorBar },
    { name: "Coach",  hours: metrics.coach_hours_total,  fill: COLORS.coachBar  },
  ]

  return (
    <div className="card">
      <h3>Internal Metrics</h3>
      <div className="kpi">
        <div className="item"><div className="badge">Doctor Hours</div><h2>{metrics.doctor_hours_total.toFixed(2)}</h2></div>
        <div className="item"><div className="badge">Coach Hours</div><h2>{metrics.coach_hours_total.toFixed(2)}</h2></div>
        <div className="item"><div className="badge">Doctor Consults</div><h2>{metrics.doctor_consults}</h2></div>
        <div className="item"><div className="badge">Coach Sessions</div><h2>{metrics.coach_sessions}</h2></div>
      </div>

      <div className="row">
        <div className="item">
          <h4>Hours per Day</h4>
          <LineChart width={520} height={300} data={dayData}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
            <XAxis dataKey="date" tick={{ fill: COLORS.axis }} stroke={COLORS.grid} />
            <YAxis tick={{ fill: COLORS.axis }} stroke={COLORS.grid} />
            <Tooltip contentStyle={{ backgroundColor: COLORS.tooltipBg, borderColor: COLORS.tooltipBd }} />
            <Legend />
            <Line type="monotone" dataKey="doctor" name="Doctor" stroke={COLORS.doctorLine} dot={{ r: 3 }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="coach"  name="Coach"  stroke={COLORS.coachLine}  dot={{ r: 3 }} activeDot={{ r: 6 }} />
          </LineChart>
        </div>
        <div className="item">
          <h4>Workload Snapshot</h4>
          <BarChart width={520} height={300} data={barData}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
            <XAxis dataKey="name" tick={{ fill: COLORS.axis }} stroke={COLORS.grid} />
            <YAxis tick={{ fill: COLORS.axis }} stroke={COLORS.grid} />
            <Tooltip contentStyle={{ backgroundColor: COLORS.tooltipBg, borderColor: COLORS.tooltipBd }} />
            {/* Each bar takes its color from the row's `fill` */}
            <Bar dataKey="hours" />
          </BarChart>
        </div>
      </div>
    </div>
  )
}
