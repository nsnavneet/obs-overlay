from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

from app.services.overlay_service import (
    normalize,
    get_overlay_payload,
    send_overlay_to_obs,
    show_advertisement_scene,
    clear_overlay_text,
)

router = APIRouter(prefix="/overlay", tags=["Overlay"])


class OverlayRequest(BaseModel):
    sessionId: str
    detailId: str


@router.get("/health")
def health():
    return {
        "success": True,
        "message": "OBS overlay API running"
    }


@router.post("/start")
def overlay_start(body: OverlayRequest):
    try:
        session_id = normalize(body.sessionId)
        detail_id = normalize(body.detailId)

        if not session_id or not detail_id:
            raise HTTPException(status_code=400, detail="sessionId and detailId are required")

        payload = get_overlay_payload(session_id, detail_id)

        send_overlay_to_obs(
            overlay_text=payload["overlayText"],
            next_talk_text=payload["nextTalkText"]
        )

        return {
            "success": True,
            "message": "Overlay sent to OBS and switched to overlay scene",
            "data": {
                "sessionId": session_id,
                "detailId": detail_id,
                "overlayText": payload["overlayText"],
                "nextTalkText": payload["nextTalkText"]
            }
        }

    except requests.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Backend API HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
def overlay_preview(body: OverlayRequest):
    try:
        session_id = normalize(body.sessionId)
        detail_id = normalize(body.detailId)

        if not session_id or not detail_id:
            raise HTTPException(status_code=400, detail="sessionId and detailId are required")

        payload = get_overlay_payload(session_id, detail_id)

        send_overlay_to_obs(
            overlay_text=payload["overlayText"],
            next_talk_text=payload["nextTalkText"]
        )

        return {
            "success": True,
            "message": "Preview sent to OBS",
            "data": {
                "overlayText": payload["overlayText"],
                "nextTalkText": payload["nextTalkText"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end")
def overlay_end():
    try:
        show_advertisement_scene()
        return {
            "success": True,
            "message": "OBS switched to advertisement scene"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
def overlay_clear():
    try:
        clear_overlay_text()
        return {
            "success": True,
            "message": "Overlay text cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))