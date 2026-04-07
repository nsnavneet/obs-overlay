from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests

from app.services.overlay_service import (
    normalize,
    get_overlay_payload,
    send_overlay_fields_to_obs,
    send_preview_fields_to_obs,
    show_advertisement_scene,
    clear_overlay_text,
)

router = APIRouter(prefix="/overlay", tags=["Overlay"])


# =========================
# REQUEST MODELS
# =========================

class OverlayRequest(BaseModel):
    sessionId: str
    detailId: str
    conferenceName: Optional[str] = ""


class EndRequest(BaseModel):
    """
    Angular sends sessionId + detailId on /end too.
    We accept them but don't need them — just switch to ad scene.
    """
    sessionId: Optional[str] = ""
    detailId: Optional[str] = ""


# =========================
# ROUTES
# =========================

@router.get("/health")
def health():
    """Health check — Angular ObsOverlayService calls this."""
    return {
        "success": True,
        "message": "OBS overlay API running"
    }


@router.post("/start")
def overlay_start(body: OverlayRequest):
    """
    Called when a talk is STARTED from the Angular control panel.
    1. Fetches session + talk details from backend
    2. Builds overlay text (current talk + next talk)
    3. Pushes text to OBS text sources
    4. Switches OBS to ConferenceOverlayScene
    """
    try:
        session_id = normalize(body.sessionId)
        detail_id  = normalize(body.detailId)

        if not session_id or not detail_id:
            raise HTTPException(
                status_code=400,
                detail="sessionId and detailId are required"
            )

        payload = get_overlay_payload(
            session_id=session_id,
            detail_id=detail_id,
            conference_name=body.conferenceName or ""
        )

        # Push text + switch scene
        send_overlay_fields_to_obs(
            speaker_name=payload["speakerName"],
            talk_topic=payload["talkTopic"],
            conference_name=payload["conferenceName"]
        )

        return {
            "success": True,
            "message": "Overlay sent to OBS and switched to overlay scene",
            "data": {
                "sessionId":    session_id,
                "detailId":     detail_id,
                "overlayText":  payload["overlayText"],
                "nextTalkText": payload["nextTalkText"],
            }
        }


    except HTTPException:
        raise
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Backend API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
def overlay_preview(body: OverlayRequest):
    """
    Called when operator clicks Preview in the Angular panel.
    Pushes text to OBS text sources but does NOT switch scenes —
    operator sees the text in OBS Studio preview before going live.
    """
    try:
        session_id = normalize(body.sessionId)
        detail_id  = normalize(body.detailId)

        if not session_id or not detail_id:
            raise HTTPException(
                status_code=400,
                detail="sessionId and detailId are required"
            )

        payload = get_overlay_payload(
            session_id=session_id,
            detail_id=detail_id,
            conference_name=body.conferenceName or ""
        )
        # Push text only — no scene switch
        send_preview_fields_to_obs(
            speaker_name=payload["speakerName"],
            talk_topic=payload["talkTopic"],
            conference_name=payload["conferenceName"]
        )

        return {
    "success": True,
    "message": "Preview text sent to OBS (scene not switched)",
    "data": {
        "speakerName": payload["speakerName"],
        "talkTopic": payload["talkTopic"],
        "conferenceName": payload["conferenceName"],
    }
}

    except HTTPException:
        raise
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Backend API error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end")
def overlay_end(body: EndRequest):
    """
    Called when a talk is ENDED from the Angular control panel.
    Switches OBS to the AdvertisementScene automatically.
    sessionId / detailId are accepted but not needed for scene switch.
    """
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
    """
    Blanks out all OBS text sources without switching scenes.
    Useful for clearing stale text between sessions.
    """
    try:
        clear_overlay_text()
        return {
            "success": True,
            "message": "Overlay text cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))