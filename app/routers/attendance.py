from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from app.core.database import get_db
from app.models.models import User, AttendanceRecord, ClassSession
from app.models.schemas import CheckInRequest, AttendanceOut, AttendanceWithUser
from app.services import face_service, anomaly_service
from app.services.auth_service import get_current_user_id

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/checkin", response_model=AttendanceOut)
def check_in(
    payload: CheckInRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Core check-in flow:
    1. Validate session exists and is active.
    2. Face image → extract embedding → find best match among registered users.
       (The matched user must be the authenticated user — prevents checking in as someone else.)
    3. QR token fallback → parse token, use authenticated user's ID directly.
    4. Anomaly check (duplicate, impossible location, etc).
    5. Write attendance record.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found.")

    if not session.is_active:
        raise HTTPException(status_code=400, detail="This session is no longer accepting check-ins.")

    confidence = None
    method = None

    if payload.image_base64:
        method = "face"
        try:
            captured_embedding = face_service.extract_embedding(payload.image_base64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        candidates = [
            (u.id, u.face_embedding)
            for u in db.query(User).filter(User.face_embedding.isnot(None)).all()
        ]
        matched_user_id, confidence = face_service.find_best_match(captured_embedding, candidates)

        if matched_user_id is None:
            raise HTTPException(
                status_code=401,
                detail=f"Face not recognized (confidence: {confidence:.2f}). Try again or use QR fallback.",
            )

        # Security: matched face must belong to the authenticated user
        if matched_user_id != current_user_id:
            raise HTTPException(
                status_code=403,
                detail="Face matched a different user. Please use your own registered face.",
            )

    elif payload.qr_token:
        method = "qr"
        # Token format: "user:<id>:<session_token>" - verify the user ID matches the auth token
        try:
            token_user_id = int(payload.qr_token.split(":")[1])
        except (IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid QR token format.")

        if token_user_id != current_user_id:
            raise HTTPException(status_code=403, detail="QR token does not belong to your account.")
    else:
        raise HTTPException(status_code=400, detail="Provide either image_base64 (face) or qr_token (QR fallback).")

    now = datetime.now(timezone.utc)
    is_anomaly, anomaly_reason = anomaly_service.check_for_anomalies(db, current_user_id, session.id, now)

    session_start = session.start_time
    if session_start.tzinfo is None:
        session_start = session_start.replace(tzinfo=timezone.utc)

    status_value = "late" if now > session_start else "present"

    record = AttendanceRecord(
        user_id=current_user_id,
        session_id=session.id,
        timestamp=now,
        method=method,
        confidence_score=confidence,
        status=status_value,
        is_anomaly=is_anomaly,
        anomaly_reason=anomaly_reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/session/{session_id}", response_model=List[AttendanceWithUser])
def get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    """Live attendance list for a session — used by faculty/admin dashboard."""
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .order_by(AttendanceRecord.timestamp.desc())
        .all()
    )
    return [
        AttendanceWithUser(
            id=r.id, user_id=r.user_id, session_id=r.session_id,
            timestamp=r.timestamp, method=r.method,
            confidence_score=r.confidence_score, status=r.status,
            is_anomaly=r.is_anomaly, anomaly_reason=r.anomaly_reason,
            user_name=r.user.name, student_id=r.user.student_id,
        )
        for r in records
    ]


@router.get("/me", response_model=List[AttendanceOut])
def my_attendance(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """A student's own attendance history."""
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.user_id == current_user_id)
        .order_by(AttendanceRecord.timestamp.desc())
        .all()
    )
