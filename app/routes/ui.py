from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from obsws_python import ReqClient
from app.services.obs_settings import obs_settings
import os
import sys

router = APIRouter(tags=["UI"])


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)


BASE_PATH = get_base_path()
TEMPLATES_DIR = os.path.join(BASE_PATH, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class OBSConnectRequest(BaseModel):
    host: str
    port: int = 4455
    password: str


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    try:
        settings = obs_settings.get_settings()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "settings": settings
            }
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return HTMLResponse(content=f"<h1>Error</h1><pre>{error_details}</pre>", status_code=500)


@router.post("/connect-obs")
def connect_obs(body: OBSConnectRequest):
    try:
        client = ReqClient(
            host=body.host.strip(),
            port=body.port,
            password=body.password.strip(),
            timeout=5
        )

        client.get_version()

        obs_settings.set_settings(
            host=body.host,
            port=body.port,
            password=body.password
        )

        return {
            "success": True,
            "message": "OBS connected successfully",
            "data": {
                "host": body.host,
                "port": body.port
            }
        }

    except Exception as e:
        obs_settings.clear()
        raise HTTPException(status_code=400, detail=f"OBS connection failed: {str(e)}")


@router.get("/obs-status")
def obs_status():
    return {
        "success": True,
        "data": obs_settings.get_settings()
    }