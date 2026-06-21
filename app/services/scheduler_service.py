"""
Background jobs using APScheduler - runs inside the FastAPI process.

Job: every 5 minutes, check for class sessions that just ended and
auto-mark any registered student who didn't check in as "absent".
This is what makes the system feel "alive" rather than purely reactive.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.models.models import ClassSession, User, AttendanceRecord

scheduler = BackgroundScheduler()


def auto_mark_absentees():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        all_sessions = (
            db.query(ClassSession)
            .filter(ClassSession.is_active == True)  # noqa: E712
            .all()
        )
        # Normalize naive end_time values (SQLite round-trip strips tzinfo) before comparing
        ended_sessions = [
            s for s in all_sessions
            if (s.end_time if s.end_time.tzinfo else s.end_time.replace(tzinfo=timezone.utc)) <= now
        ]

        for session in ended_sessions:
            checked_in_ids = {
                r.user_id for r in
                db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session.id).all()
            }
            all_students = db.query(User).filter(User.role == "student").all()

            for student in all_students:
                if student.id not in checked_in_ids:
                    db.add(AttendanceRecord(
                        user_id=student.id,
                        session_id=session.id,
                        timestamp=now,
                        method="auto",
                        status="absent",
                    ))

            session.is_active = False  # mark processed so we don't repeat this

        db.commit()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(auto_mark_absentees, "interval", minutes=5, id="auto_mark_absentees")
    scheduler.start()
