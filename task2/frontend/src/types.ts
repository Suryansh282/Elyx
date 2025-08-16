export type FrictionPoint = { id: number; text: string }
export type DecisionReason = { text: string; evidence_ids: number[] }
export type Decision = {
  id: number
  title: string
  date: string
  description: string
  reasons: DecisionReason[]
}
export type Episode = {
  id: number
  title: string
  start_date: string
  end_date: string
  goal: string
  triggered_by: string
  outcome: string
  persona_before: string
  persona_after: string
  response_time_minutes: number
  time_to_resolution_minutes: number
  friction_points: FrictionPoint[]
  decisions: Decision[]
}
export type ChatMessage = { id: number; date: string; sender: string; text: string }
export type MemberJourney = {
  member_id: number
  member_name: string
  episodes: Episode[]
  chats: ChatMessage[]
}
export type StaffActivity = { date: string; role: string; hours: number }
export type InternalMetrics = {
  member_id: number
  doctor_hours_total: number
  coach_hours_total: number
  doctor_consults: number
  coach_sessions: number
  per_day_hours: StaffActivity[]
}
export type WhyResponse = {
  answer: string
  matched_decision_id?: number | null
  evidence_chat: ChatMessage[]
}
