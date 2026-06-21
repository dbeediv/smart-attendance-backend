"""
Core data models.

Design notes (worth mentioning in an interview):
- We store face EMBEDDINGS (a list of floats), never raw face photos, in the
  attendance table. This is a privacy-conscious design choice - even if the
  DB leaks, you can't reconstruct someone's face from an embedding vector.
- Embeddings are stored as JSON-serialized text for SQLite simplicity. In a
  production system with heavy scale, you'd use a vector DB (Pinecone,
  pgvector) for fast nearest-neighbor search instead of a manual loop.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student")  # student | faculty | admin
    student_id = Column(String, unique=True, nullable=True, index=True)
    face_embedding = Column(Text, nullable=True)  # JSON-serialized embedding vector
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    attendance_records = relationship("AttendanceRecord", back_populates="user")


class ClassSession(Base):
    """A single class/period instance that attendance is taken against."""
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # e.g. "DBMS - Section A"
    faculty_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    attendance_records = relationship("AttendanceRecord", back_populates="session")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("class_sessions.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    method = Column(String, default="face")   # face | qr | manual
    confidence_score = Column(Float, nullable=True)  # similarity score from face match
    status = Column(String, default="present")  # present | late | absent
    is_anomaly = Column(Boolean, default=False)  # flagged by anomaly detection
    anomaly_reason = Column(String, nullable=True)

    user = relationship("User", back_populates="attendance_records")
    session = relationship("ClassSession", back_populates="attendance_records")
