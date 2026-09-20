from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import onboarding, dashboard, rag

app = FastAPI(title="Fin API")

# Allow origins from environment variables for production, fallback to localhost for dev
# In Render, set ALLOWED_ORIGINS to your Vercel URL (e.g., https://fin-app.vercel.app)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding.router)
app.include_router(dashboard.router)
app.include_router(rag.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
