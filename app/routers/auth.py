from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.models.schemas import UserCreate, UserLogin, UserOut, Token, FaceRegisterRequest
from app.services import auth_service, face_service
from app.services.auth_service import get_current_user_id

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=auth_service.hash_password(payload.password),
        role=payload.role,
        student_id=payload.student_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth_service.create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token, user=_to_user_out(user))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = auth_service.create_access_token({"sub": str(user.id), "role": user.role})
    return Token(access_token=token, user=_to_user_out(user))


@router.post("/register-face", response_model=UserOut)
def register_face(
    payload: FaceRegisterRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Registers a face embedding for the authenticated user.
    Reads user identity from the Bearer token — no manual user_id needed.
    """
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    try:
        embedding = face_service.extract_embedding(payload.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user.face_embedding = face_service.serialize_embedding(embedding)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@router.get("/me", response_model=UserOut)
def me(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns the currently authenticated user's profile."""
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _to_user_out(user)


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        student_id=user.student_id,
        has_face_registered=user.face_embedding is not None,
    )
