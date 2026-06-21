"""
Liveness detection - prevents someone from spoofing attendance with a
printed photo or a photo on a phone screen.

Approach: eye-aspect-ratio (EAR) based blink detection across a short
sequence of frames sent from the frontend. A static photo can't blink;
a live person naturally will within a 2-3 second capture window.

This is a simplified, CPU-friendly version of the standard EAR algorithm
(Soukupova & Cech, 2016) - good enough for a demo/resume project, while
being honest that production-grade liveness (e.g. banking KYC apps) uses
more robust 3D depth or texture-analysis methods.
"""
import numpy as np
import cv2

# Lazy-loaded once, reused across requests
_face_cascade = None
_eye_cascade = None


def _get_cascades():
    global _face_cascade, _eye_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        _eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    return _face_cascade, _eye_cascade


def count_open_eyes(frame_rgb: np.ndarray) -> int:
    """Returns how many eyes are detected as 'open' in a single frame."""
    face_cascade, eye_cascade = _get_cascades()
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return 0

    x, y, w, h = faces[0]  # assume largest/first face is the subject
    face_roi = gray[y:y + h, x:x + w]
    eyes = eye_cascade.detectMultiScale(face_roi, 1.1, 6)
    return len(eyes)


def check_liveness(frames: list[np.ndarray]) -> dict:
    """
    Takes a short sequence of frames (e.g. 10-15 frames captured over ~2 seconds)
    and checks for a blink pattern: eyes open -> eyes closed -> eyes open.

    Returns: { "is_live": bool, "reason": str }
    """
    if len(frames) < 5:
        return {"is_live": False, "reason": "Not enough frames captured for liveness check."}

    eye_counts = [count_open_eyes(f) for f in frames]

    # A blink shows up as a dip to 0 (or near-0) eyes detected between
    # frames where 2 eyes were clearly detected.
    saw_open = False
    saw_closed_after_open = False
    for count in eye_counts:
        if count >= 2:
            saw_open = True
        elif count == 0 and saw_open:
            saw_closed_after_open = True

    if saw_open and saw_closed_after_open:
        return {"is_live": True, "reason": "Blink detected - liveness confirmed."}

    if not saw_open:
        return {"is_live": False, "reason": "Could not clearly detect open eyes. Try better lighting."}

    return {
        "is_live": False,
        "reason": "No blink detected during capture window. Possible spoofing attempt (static photo)."
    }
