from typing import Optional, Dict, Any, List
import requests
from obsws_python import ReqClient

# =========================
# CONFIG
# =========================

BASE_URL = "https://nntr.in/api/api/Conference"

OBS_HOST = "192.168.1.8"
OBS_PORT = 4455
OBS_PASSWORD = "29kPOoAi6qZGjFv6"

OVERLAY_SCENE_NAME = "ConferenceOverlayScene"
ADVERTISEMENT_SCENE_NAME = "AdvertisementScene"
TEXT_SOURCE_NAME = "ConferenceOverlayText"
NEXT_TALK_TEXT_SOURCE_NAME = "ConferenceNextTalkText"

GET_ALL_SESSIONS_ENDPOINT = f"{BASE_URL}/GetSession"
GET_SESSION_BY_ID_ENDPOINT = f"{BASE_URL}/Get-Session"


# =========================
# HELPERS
# =========================

def obs_client() -> ReqClient:
    return ReqClient(
        host=OBS_HOST,
        port=OBS_PORT,
        password=OBS_PASSWORD,
        timeout=5
    )


def safe_get(url: str, timeout: int = 15) -> Dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def normalize(value: Any) -> str:
    return str(value or "").strip()


def hhmm(value: Optional[str]) -> str:
    if not value:
        return "—"
    value = str(value).strip()
    return value[:5] if len(value) >= 5 else value


def duration_to_min(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        parts = str(value).split(":")
        hours = int(parts[0]) if len(parts) > 0 else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
        total = hours * 60 + minutes
        return f"{total} min"
    except Exception:
        return str(value)


# =========================
# BACKEND DATA
# =========================

def get_all_sessions() -> List[Dict[str, Any]]:
    data = safe_get(GET_ALL_SESSIONS_ENDPOINT)
    return data.get("data") or []


def get_session_details(session_id: str) -> List[Dict[str, Any]]:
    data = safe_get(f"{GET_SESSION_BY_ID_ENDPOINT}/{session_id}")
    return data.get("data") or []


def find_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    sessions = get_all_sessions()
    for session in sessions:
        if normalize(session.get("id")) == normalize(session_id):
            return session
    return None


def sort_details(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def sort_key(detail: Dict[str, Any]):
        start_time = normalize(detail.get("startTime"))
        created_date = normalize(detail.get("createdDate"))
        return (start_time or "99:99:99", created_date or "9999-12-31T23:59:59")

    return sorted(details, key=sort_key)


def find_detail_by_id(details: List[Dict[str, Any]], detail_id: str) -> Optional[Dict[str, Any]]:
    for detail in details:
        if normalize(detail.get("id")) == normalize(detail_id):
            return detail
    return None


def find_next_detail(details: List[Dict[str, Any]], current_detail_id: str) -> Optional[Dict[str, Any]]:
    ordered = sort_details(details)
    for index, detail in enumerate(ordered):
        if normalize(detail.get("id")) == normalize(current_detail_id):
            return ordered[index + 1] if index + 1 < len(ordered) else None
    return None


# =========================
# TEXT BUILDERS
# =========================

def build_overlay_text(
    session: Dict[str, Any],
    current_detail: Dict[str, Any],
    next_detail: Optional[Dict[str, Any]]
) -> str:
    session_name = normalize(session.get("sessionName")) or "—"
    hall_name = normalize(session.get("hallName")) or "—"
    location = normalize(session.get("location")) or "—"
    chair = normalize(session.get("chairPersonName")) or "—"

    topic = normalize(current_detail.get("topic")) or "—"
    speaker = normalize(current_detail.get("nameOfSpeaker")) or "—"
    start_time = hhmm(current_detail.get("startTime"))
    end_time = hhmm(current_detail.get("endTime"))
    duration = duration_to_min(current_detail.get("time"))

    if next_detail:
        next_topic = normalize(next_detail.get("topic")) or "—"
        next_speaker = normalize(next_detail.get("nameOfSpeaker")) or "—"
        next_line = f"Next: {next_topic} | {next_speaker}"
    else:
        next_line = "Next: No further talk in this session"

    return (
        f"{session_name}\n"
        f"Topic: {topic}\n"
        f"Speaker: {speaker}\n"
        f"Time: {start_time} - {end_time} | Duration: {duration}\n"
        f"Hall: {hall_name}\n"
        f"Location: {location}\n"
        f"Chair: {chair}\n"
        f"{next_line}"
    )


def build_next_talk_text(next_detail: Optional[Dict[str, Any]]) -> str:
    if not next_detail:
        return "No next talk"

    next_topic = normalize(next_detail.get("topic")) or "—"
    next_speaker = normalize(next_detail.get("nameOfSpeaker")) or "—"
    next_start = hhmm(next_detail.get("startTime"))
    next_end = hhmm(next_detail.get("endTime"))

    return f"UP NEXT: {next_topic} | {next_speaker} | {next_start} - {next_end}"


# =========================
# OBS ACTIONS
# =========================

def set_obs_text(source_name: str, text_value: str):
    client = obs_client()
    client.set_input_settings(
        name=source_name,
        settings={"text": text_value},
        overlay=True
    )


def switch_scene(scene_name: str):
    client = obs_client()
    client.set_current_program_scene(scene_name)


def send_overlay_to_obs(overlay_text: str, next_talk_text: Optional[str] = None):
    set_obs_text(TEXT_SOURCE_NAME, overlay_text)

    if next_talk_text:
        try:
            set_obs_text(NEXT_TALK_TEXT_SOURCE_NAME, next_talk_text)
        except Exception:
            pass

    switch_scene(OVERLAY_SCENE_NAME)


def show_advertisement_scene():
    switch_scene(ADVERTISEMENT_SCENE_NAME)


def clear_overlay_text():
    set_obs_text(TEXT_SOURCE_NAME, "")
    try:
        set_obs_text(NEXT_TALK_TEXT_SOURCE_NAME, "")
    except Exception:
        pass


# =========================
# MAIN BUSINESS LOGIC
# =========================

def get_overlay_payload(session_id: str, detail_id: str) -> Dict[str, Any]:
    session = find_session_by_id(session_id)
    if not session:
        raise ValueError(f"Session not found for sessionId={session_id}")

    details = get_session_details(session_id)
    if not details:
        raise ValueError(f"No session details found for sessionId={session_id}")

    current_detail = find_detail_by_id(details, detail_id)
    if not current_detail:
        raise ValueError(f"Session detail not found for detailId={detail_id}")

    next_detail = find_next_detail(details, detail_id)

    overlay_text = build_overlay_text(session, current_detail, next_detail)
    next_talk_text = build_next_talk_text(next_detail)

    return {
        "session": session,
        "currentDetail": current_detail,
        "nextDetail": next_detail,
        "overlayText": overlay_text,
        "nextTalkText": next_talk_text,
    }