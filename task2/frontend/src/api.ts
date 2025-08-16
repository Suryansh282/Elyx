import axios from "axios"
import { InternalMetrics, MemberJourney, WhyResponse } from "./types"

const API_BASE = "http://127.0.0.1:8000/api"

export async function fetchMembers() {
  const { data } = await axios.get(`${API_BASE}/members`)
  return data as { id: number; name: string }[]
}

export async function fetchJourney(memberId: number) {
  const { data } = await axios.get(`${API_BASE}/members/${memberId}/journey`)
  return data as MemberJourney
}

export async function fetchMetrics(memberId: number) {
  const { data } = await axios.get(`${API_BASE}/members/${memberId}/metrics`)
  return data as InternalMetrics
}

export async function askWhy(memberId: number, question: string, decisionId?: number | null) {
  const { data } = await axios.post(`${API_BASE}/chat/why`, {
    member_id: memberId,
    question,
    decision_id: decisionId ?? null
  })
  return data as WhyResponse
}
