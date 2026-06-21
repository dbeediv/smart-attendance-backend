from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from app.core.database import get_db
from app.models.models import ClassSession
from app.models.schemas import ClassSessionCreate, ClassSessionOut
from app.services.auth_service import get_current_user_id, require_roles

router = APIRouter(prefix="/sessions", tags=["Class Sessions"])


@router.post("/", response_model=ClassSessionOut)
def create_session(
    payload: ClassSessionCreate,
    _auth=Depends(require_roles("faculty", "admin")),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = ClassSession(
        name=payload.name,
        faculty_id=current_user_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/active", response_model=List[ClassSessionOut])
def list_active_sessions(db: Session = Depends(get_db)):
    """Returns currently active sessions. Used by the student check-in page."""
    now = datetime.now(timezone.utc)
    sessions = db.query(ClassSession).filter(ClassSession.is_active == True).all()  # noqa: E712
    # Also filter to sessions whose time window is currently open
    result = []
    for s in sessions:
        start = s.start_time.replace(tzinfo=timezone.utc) if s.start_time.tzinfo is None else s.start_time
        end = s.end_time.replace(tzinfo=timezone.utc) if s.end_time.tzinfo is None else s.end_time
        if start <= now <= end:
            result.append(s)
    return result


@router.get("/", response_model=List[ClassSessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return db.query(ClassSession).order_by(ClassSession.start_time.desc()).all()


@router.get("/{session_id}", response_model=ClassSessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Class session not found.")
    return session
