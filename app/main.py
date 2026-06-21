from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()  # picks up a local .env file if present; no-op in production where real env vars are set

from app.core.database import engine, Base
from app.routers import auth, sessions, attendance, liveness, analytics
from app.services.scheduler_service import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist, start background scheduler
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    # Shutdown: nothing to clean up for this demo


app = FastAPI(
    title="Smart Attendance System API",
    description="Face-recognition-based attendance system with liveness detection and anomaly flagging.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow the React dev server (and deployed frontend) to call this API.
# Set CORS_ORIGINS as a comma-separated list in production, e.g.
# CORS_ORIGINS=https://your-app.vercel.app
_cors_env = os.getenv("CORS_ORIGINS")
allow_origins = [o.strip() for o in _cors_env.split(",")] if _cors_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(attendance.router)
app.include_router(liveness.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Smart Attendance System API is running. See /docs for the API explorer."}


@app.get("/health")
def health():
    return {"status": "healthy"}
