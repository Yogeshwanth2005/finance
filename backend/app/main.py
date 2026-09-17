from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import onboarding

app = FastAPI(title="Fin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
