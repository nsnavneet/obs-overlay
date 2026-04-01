from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.overlay import router as overlay_router

app = FastAPI(title="OBS Overlay API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overlay_router)

@app.get("/")
def root():
    return {"success": True, "message": "FastAPI OBS Overlay API is running"}