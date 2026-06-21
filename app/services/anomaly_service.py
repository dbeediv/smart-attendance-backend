"""
Anomaly detection - lightweight rule-based checks run on every check-in.

This is intentionally simple (rule-based, not ML) because:
1. It's explainable - you can describe exactly why something got flagged,
   which matters in an attendance system (no "black box" accusations).
2. It's a legitimate, defensible design choice to mention in interviews:
   not every problem needs ML; sometimes rules are the right tool.
"""
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.models import AttendanceRecord

DUPLICATE_WINDOW_MINUTES = 5


def check_for_anomalies(db: Session, user_id: int, session_id: int, timestamp) -> tuple[bool, str | None]:
    """
    Returns (is_anomaly, reason).
    Checks for:
    - Duplicate check-in: same user checking into the same session twice within a short window.
    - Already marked present: user already has a non-duplicate record for this session.
    """
    existing = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.session_id == session_id,
        )
        .order_by(AttendanceRecord.timestamp.desc())
        .first()
    )

    if existing is None:
        return False, None

    existing_timestamp = existing.timestamp
    if existing_timestamp.tzinfo is None:
        existing_timestamp = existing_timestamp.replace(tzinfo=timestamp.tzinfo)

    time_diff = timestamp - existing_timestamp
    if time_diff < timedelta(minutes=DUPLICATE_WINDOW_MINUTES):
        return True, f"Duplicate check-in within {DUPLICATE_WINDOW_MINUTES} minutes of a previous record."

    return True, "User already has an attendance record for this session."
