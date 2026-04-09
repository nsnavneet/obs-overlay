from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.overlay import router as overlay_router
from app.routes.ui import router as ui_router

app = FastAPI(
    title="OBS Overlay API",
    version="1.0.0",
    description="Controls OBS text overlays and scene switching for conference talks."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nntr.in",
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ui_router)
app.include_router(overlay_router)


@app.get("/")
def root():
    return {
        "success": True,
        "message": "FastAPI OBS Overlay API is running",
        "routes": [
            "GET  /overlay/health",
            "POST /overlay/preview",
            "POST /overlay/start",
            "POST /overlay/end",
            "POST /overlay/clear",
        ]
    }