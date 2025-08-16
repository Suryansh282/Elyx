from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base

class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    episodes = relationship("Episode", back_populates="member", cascade="all, delete-orphan")
    chats = relationship("ChatMessage", back_populates="member", cascade="all, delete-orphan")
    staff_activities = relationship("StaffActivity", back_populates="member", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    end_date: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    persona_before: Mapped[str] = mapped_column(Text, nullable=False)
    persona_after: Mapped[str] = mapped_column(Text, nullable=False)
    response_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    time_to_resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    member = relationship("Member", back_populates="episodes")
    friction_points = relationship("FrictionPoint", back_populates="episode", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="episode", cascade="all, delete-orphan")

class FrictionPoint(Base):
    __tablename__ = "frictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    episode = relationship("Episode", back_populates="friction_points")

class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)  # ISO date
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False)  # [{"text": str, "evidence_ids":[int,...]}]

    episode = relationship("Episode", back_populates="decisions")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    sender: Mapped[str] = mapped_column(String, nullable=False)  # member/elyx/doctor/coach
    text: Mapped[str] = mapped_column(Text, nullable=False)

    member = relationship("Member", back_populates="chats")

class StaffActivity(Base):
    __tablename__ = "staff_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # doctor/coach
    hours: Mapped[float] = mapped_column(Float, nullable=False)

    member = relationship("Member", back_populates="staff_activities")
