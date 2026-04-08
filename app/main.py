from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.overlay import router as overlay_router
from app.routes.ui import router as ui_router
app = FastAPI(
    title="OBS Overlay API",
    version="1.0.0",
    description="Controls OBS text overlays and scene switching for conference talks."
)

# Allow Angular dev server + any local OBS operator machine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# HTML UI
app.include_router(ui_router)

# All overlay routes are at /overlay/*
app.include_router(overlay_router)


@app.get("/")
def root():
    return {
        "success": True,
        "message": "FastAPI OBS Overlay API is running",
        "routes": [
            "GET  /overlay/health",
            "POST /overlay/preview  — push text to OBS (no scene switch)",
            "POST /overlay/start    — push text + switch to ConferenceOverlayScene",
            "POST /overlay/end      — switch to AdvertisementScene",
            "POST /overlay/clear    — blank all overlay text sources",
        ]
    }