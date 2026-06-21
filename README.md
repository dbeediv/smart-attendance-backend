# Smart Attendance System — Backend

FastAPI backend for a face-recognition-based attendance system with liveness
detection (anti-spoofing) and anomaly flagging.

## What's been tested and confirmed working

Every piece below was actually run end-to-end during development, not just written:

- ✅ User registration, login, JWT auth — tested with real requests
- ✅ Class session creation and listing
- ✅ QR-fallback check-in flow (present/late status logic)
- ✅ Duplicate check-in detection (anomaly flagging)
- ✅ Analytics summary (attendance %, correctly excludes anomalous duplicate records)
- ✅ Anomaly listing, daily trend aggregation
- ✅ All error paths: invalid session, missing image/QR, malformed QR token, duplicate email, wrong password
- ✅ **Liveness detection** (blink-based anti-spoofing) — tested with both a static photo
  (correctly rejected) and a simulated blink sequence (correctly accepted)
- ⚠️ **Face recognition (DeepFace/ArcFace) is written and integrated, but could not be
  live-tested in the sandbox this was built in** — see note below. The code path is
  correct and follows DeepFace's documented API; it just needs its model weights,
  which couldn't be downloaded in that specific environment.

## Important: first-run model download

The face recognition feature uses DeepFace's ArcFace model. On your machine, the
**first** time `extract_embedding()` runs, DeepFace will automatically download the
model weights (~50MB) from GitHub. This requires a normal, unrestricted internet
connection and may take 10-30 seconds depending on your connection. After that first
download, it's cached locally and every subsequent call is fast.

If you're behind a restrictive network/firewall and the download fails, you'll get a
clear `RuntimeError` (not a misleading "no face detected" error — this was a real bug
found and fixed during testing) telling you the weights couldn't be fetched.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** — FastAPI's auto-generated interactive API
explorer. You can test every endpoint directly from the browser without writing any
frontend code, including uploading a base64 image for face registration/check-in.

## First-time face recognition test

To confirm DeepFace works on your machine before wiring up the frontend:

```bash
python -c "
from app.services import face_service
import base64
with open('path/to/a/real/face/photo.jpg', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()
embedding = face_service.extract_embedding(img_b64)
print('Success! Embedding length:', len(embedding))
"
```

First run downloads the model. If it prints an embedding length (512 for ArcFace),
you're good to go.

## Database

Uses SQLite (`attendance.db`, auto-created on first run) for zero-setup local
development. The schema is in `app/models/models.py`. To switch to PostgreSQL later
(e.g. for deployment), only `app/core/database.py` needs to change — update
`SQLALCHEMY_DATABASE_URL` to your Postgres connection string. No other code changes
needed, since SQLAlchemy abstracts the dialect.

## Project structure

```
app/
  core/
    database.py       - DB connection setup
  models/
    models.py          - SQLAlchemy ORM models (User, ClassSession, AttendanceRecord)
    schemas.py          - Pydantic request/response schemas
  services/
    auth_service.py    - Password hashing, JWT tokens
    face_service.py    - DeepFace embedding extraction + cosine similarity matching
    liveness_service.py - Blink-based anti-spoofing
    anomaly_service.py - Duplicate/impossible check-in detection
    scheduler_service.py - Background job: auto-mark absentees after class ends
  routers/
    auth.py            - /auth/register, /auth/login, /auth/register-face
    sessions.py         - /sessions/
    attendance.py       - /attendance/check-in, /attendance/session/{id}, /attendance/user/{id}
    liveness.py          - /liveness/check
    analytics.py         - /analytics/summary, /analytics/anomalies, /analytics/daily-trend
  main.py               - App entrypoint, CORS, router registration, startup hooks
```

## Known limitations (be upfront about these in an interview)

- Liveness detection uses a simplified Haar-cascade blink check, not a production-grade
  3D/texture-based method. Good enough to demo the concept and stop a basic photo-spoof
  attempt; a real banking KYC app would use something more robust.
- Face matching is a linear O(n) scan over all registered users. Fine for a class of
  60-200 people; at real scale you'd swap to a vector index (FAISS, pgvector).
- JWT secret key is hardcoded for local dev — move to an environment variable before
  any real deployment.
- QR token format is intentionally simple for this demo; production would use a
  short-lived signed token to prevent screenshot/replay reuse.
