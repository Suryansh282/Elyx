from pydantic import BaseModel, Field
from typing import List, Optional

class FrictionPoint(BaseModel):
    id: int
    text: str
    class Config: from_attributes = True

class DecisionReason(BaseModel):
    text: str
    evidence_ids: List[int] = Field(default_factory=list)

class Decision(BaseModel):
    id: int
    title: str
    date: str
    description: str
    reasons: List[DecisionReason]
    class Config: from_attributes = True

class Episode(BaseModel):
    id: int
    title: str
    start_date: str
    end_date: str
    goal: str
    triggered_by: str
    outcome: str
    persona_before: str
    persona_after: str
    response_time_minutes: int
    time_to_resolution_minutes: int
    friction_points: List[FrictionPoint]
    decisions: List[Decision]
    class Config: from_attributes = True

class ChatMessage(BaseModel):
    id: int
    date: str
    sender: str
    text: str
    class Config: from_attributes = True

class StaffActivity(BaseModel):
    date: str
    role: str
    hours: float
    class Config: from_attributes = True

class MemberJourney(BaseModel):
    member_id: int
    member_name: str
    episodes: List[Episode]
    chats: List[ChatMessage]

class InternalMetrics(BaseModel):
    member_id: int
    doctor_hours_total: float
    coach_hours_total: float
    doctor_consults: int
    coach_sessions: int
    per_day_hours: List[StaffActivity]

class WhyRequest(BaseModel):
    member_id: int
    question: str
    decision_id: Optional[int] = None

class WhyResponse(BaseModel):
    answer: str
    matched_decision_id: Optional[int] = None
    evidence_chat: List[ChatMessage]
