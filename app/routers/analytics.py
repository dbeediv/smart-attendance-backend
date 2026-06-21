from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.models.models import User, AttendanceRecord, ClassSession
from app.models.schemas import AttendanceSummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=List[AttendanceSummary])
def attendance_summary(db: Session = Depends(get_db)):
    """
    Per-student attendance summary across all sessions.
    Powers the main analytics table on the faculty/admin dashboard.
    """
    total_sessions = db.query(func.count(ClassSession.id)).scalar() or 0
    students = db.query(User).filter(User.role == "student").all()

    summaries = []
    for student in students:
        records = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.user_id == student.id, AttendanceRecord.is_anomaly == False)  # noqa: E712
            .all()
        )
        present_count = sum(1 for r in records if r.status == "present")
        late_count = sum(1 for r in records if r.status == "late")
        attended = present_count + late_count
        absent_count = max(total_sessions - attended, 0)
        percentage = round((attended / total_sessions) * 100, 1) if total_sessions > 0 else 0.0

        summaries.append(AttendanceSummary(
            user_id=student.id,
            user_name=student.name,
            total_sessions=total_sessions,
            present_count=present_count,
            late_count=late_count,
            absent_count=absent_count,
            attendance_percentage=percentage,
        ))

    return summaries


@router.get("/anomalies")
def list_anomalies(db: Session = Depends(get_db)):
    """Returns all attendance records flagged as anomalies, for the admin to review."""
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.is_anomaly == True)  # noqa: E712
        .order_by(AttendanceRecord.timestamp.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "user_name": r.user.name,
            "session_name": r.session.name,
            "timestamp": r.timestamp,
            "reason": r.anomaly_reason,
        }
        for r in records
    ]


@router.get("/daily-trend")
def daily_trend(db: Session = Depends(get_db)):
    """
    Attendance count grouped by day - powers the trend line chart on the dashboard.
    Uses SQLite's date() function; swap for PostgreSQL's DATE_TRUNC equivalent if you migrate DBs.
    """
    results = (
        db.query(
            func.date(AttendanceRecord.timestamp).label("day"),
            func.count(AttendanceRecord.id).label("count"),
        )
        .group_by(func.date(AttendanceRecord.timestamp))
        .order_by(func.date(AttendanceRecord.timestamp))
        .all()
    )
    return [{"date": str(r.day), "count": r.count} for r in results]
