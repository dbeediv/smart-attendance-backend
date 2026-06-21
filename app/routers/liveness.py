from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from app.services import liveness_service, face_service

router = APIRouter(prefix="/liveness", tags=["Liveness Detection"])


class LivenessRequest(BaseModel):
    frames_base64: List[str]   # short sequence of frames (~10-15) captured over 2-3 seconds


class LivenessResponse(BaseModel):
    is_live: bool
    reason: str


@router.post("/check", response_model=LivenessResponse)
def check_liveness(payload: LivenessRequest):
    if len(payload.frames_base64) < 5:
        raise HTTPException(status_code=400, detail="Send at least 5 frames for a reliable liveness check.")

    frames = [face_service.decode_base64_image(f) for f in payload.frames_base64]
    result = liveness_service.check_liveness(frames)
    return LivenessResponse(**result)
