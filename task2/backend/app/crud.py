from sqlalchemy.orm import Session, joinedload
from . import models

def get_members(db: Session):
    return db.query(models.Member).all()

def get_member(db: Session, member_id: int):
    return db.query(models.Member).filter(models.Member.id == member_id).first()

def get_member_journey(db: Session, member_id: int):
    member = (
        db.query(models.Member)
        .options(
            joinedload(models.Member.episodes)
            .joinedload(models.Episode.friction_points),
            joinedload(models.Member.episodes)
            .joinedload(models.Episode.decisions),
            joinedload(models.Member.chats),
        )
        .filter(models.Member.id == member_id)
        .first()
    )
    return member

def get_decision(db: Session, decision_id: int):
    return db.query(models.Decision).filter(models.Decision.id == decision_id).first()

def get_internal_metrics(db: Session, member_id: int):
    activities = (
        db.query(models.StaffActivity)
        .filter(models.StaffActivity.member_id == member_id)
        .all()
    )
    doctor_hours = sum(a.hours for a in activities if a.role == "doctor")
    coach_hours = sum(a.hours for a in activities if a.role == "coach")

    # heuristics for counts
    member = get_member_journey(db, member_id)
    doctor_consults = 0
    coach_sessions = 0
    if member:
        for ep in member.episodes:
            for d in ep.decisions:
                title = d.title.lower()
                if "consult" in title or "lifestyle consultation" in title:
                    doctor_consults += 1
                if "workout" in title or "coaching" in title or "coach" in title:
                    coach_sessions += 1

    return {
        "doctor_hours_total": doctor_hours,
        "coach_hours_total": coach_hours,
        "doctor_consults": doctor_consults,
        "coach_sessions": coach_sessions,
        "per_day_hours": activities,
    }

def search_decision_by_text(db: Session, member_id: int, text: str):
    text = text.lower()
    member = get_member_journey(db, member_id)
    if not member:
        return []
    matches = []
    for ep in member.episodes:
        for d in ep.decisions:
            hay = (d.title + " " + d.description).lower()
            if any(tok in hay for tok in text.split()):
                matches.append(d)
    return matches
