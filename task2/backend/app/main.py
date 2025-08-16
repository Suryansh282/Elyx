import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import SessionLocal, Base, engine
from . import crud, schemas
from .llm import offline_why_answer
from typing import List

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Member Journey & Reasoning API", version="1.0.0")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/members")
def list_members(db: Session = Depends(get_db)):
    members = crud.get_members(db)
    return [{"id": m.id, "name": m.name} for m in members]

@app.get("/api/members/{member_id}/journey", response_model=schemas.MemberJourney)
def member_journey(member_id: int, db: Session = Depends(get_db)):
    member = crud.get_member_journey(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    episodes = [e for e in member.episodes]
    chats = [c for c in member.chats]
    return {
        "member_id": member.id,
        "member_name": member.name,
        "episodes": episodes,
        "chats": chats,
    }

@app.get("/api/decisions/{decision_id}", response_model=schemas.Decision)
def get_decision(decision_id: int, db: Session = Depends(get_db)):
    decision = crud.get_decision(db, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision

@app.get("/api/members/{member_id}/metrics", response_model=schemas.InternalMetrics)
def get_metrics(member_id: int, db: Session = Depends(get_db)):
    if not crud.get_member(db, member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    m = crud.get_internal_metrics(db, member_id)
    return {
        "member_id": member_id,
        "doctor_hours_total": m["doctor_hours_total"],
        "coach_hours_total": m["coach_hours_total"],
        "doctor_consults": m["doctor_consults"],
        "coach_sessions": m["coach_sessions"],
        "per_day_hours": m["per_day_hours"],
    }

@app.post("/api/chat/why", response_model=schemas.WhyResponse)
def ask_why(payload: schemas.WhyRequest, db: Session = Depends(get_db)):
    member = crud.get_member_journey(db, payload.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    decision = None
    if payload.decision_id:
        decision = crud.get_decision(db, payload.decision_id)
    if not decision:
        candidates = crud.search_decision_by_text(db, payload.member_id, payload.question)
        decision = candidates[0] if candidates else None

    if not decision:
        return {
            "answer": "I could not find a matching decision. Please mention the decision title or provide a decision ID.",
            "matched_decision_id": None,
            "evidence_chat": [],
        }

    # Build offline answer
    chats = [schemas.ChatMessage.model_validate(c) for c in member.chats]
    decision_dict = {
        "title": decision.title,
        "date": decision.date,
        "description": decision.description,
        "reasons": decision.reasons,
    }
    answer = offline_why_answer(decision_dict, chats)

    # Return the evidence chat blobs
    needed_ids = []
    for r in decision.reasons:
        needed_ids.extend(r.get("evidence_ids", []))
    idset = set(needed_ids)
    evidence = [c for c in member.chats if c.id in idset]

    return {
        "answer": answer,
        "matched_decision_id": decision.id,
        "evidence_chat": evidence,
    }
