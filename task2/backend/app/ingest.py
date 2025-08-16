import json
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from . import models

def ingest(path: str):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db: Session = SessionLocal()
    try:
        member = models.Member(id=data["member"]["id"], name=data["member"]["name"])
        db.add(member)
        db.flush()

        for c in data["chats"]:
            db.add(models.ChatMessage(
                id=c["id"], member_id=member.id, date=c["date"], sender=c["sender"], text=c["text"]
            ))

        for ep in data["episodes"]:
            epi = models.Episode(
                id=ep["id"],
                member_id=member.id,
                title=ep["title"],
                start_date=str(ep["start_date"]),
                end_date=str(ep["end_date"]),
                goal=ep["goal"],
                triggered_by=ep["triggered_by"],
                outcome=ep["outcome"],
                persona_before=ep["persona_before"],
                persona_after=ep["persona_after"],
                response_time_minutes=ep["response_time_minutes"],
                time_to_resolution_minutes=ep["time_to_resolution_minutes"],
            )
            db.add(epi)
            db.flush()

            for fp in ep.get("friction_points", []):
                db.add(models.FrictionPoint(episode_id=epi.id, text=fp))

            for d in ep.get("decisions", []):
                db.add(models.Decision(
                    id=d["id"],
                    episode_id=epi.id,
                    title=d["title"],
                    date=d["date"],
                    description=d["description"],
                    reasons=d["reasons"]
                ))

        for s in data["staff_activities"]:
            db.add(models.StaffActivity(
                member_id=member.id, date=s["date"], role=s["role"], hours=float(s["hours"])
            ))
        db.commit()
        print("Ingest complete.")
    finally:
        db.close()

if __name__ == "__main__":
    ingest(path="app/seed/sample_data.json")
