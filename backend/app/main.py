import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import seed_default_data
from .routes import profile, jobs, tailor, applications, agent, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB and seeds
    seed_default_data()
    yield

app = FastAPI(
    title="CareerPilot AI - Autonomous Career Agent API",
    description="Intelligent personalized job search, ATS matching, resume tailoring, and application management.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(tailor.router)
app.include_router(applications.router)
app.include_router(agent.router)
app.include_router(analytics.router)

# Locate Frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
FRONTEND_PUBLIC = FRONTEND_DIR / "public"

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "CareerPilot AI Engine", "version": "1.0.0"}

# Mount frontend public static files if directory exists
if FRONTEND_PUBLIC.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_PUBLIC)), name="static")

@app.get("/")
def serve_index():
    index_file = FRONTEND_PUBLIC / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "CareerPilot AI API is active. Visit /docs for OpenAPI swagger documentation."}
