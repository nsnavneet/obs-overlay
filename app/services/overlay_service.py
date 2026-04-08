from typing import Optional, Dict, Any, List
import requests
from obsws_python import ReqClient
import threading
import time
from app.services.obs_settings import obs_settings
# =========================
# CONFIG
# =========================

BASE_URL = "https://nntr.in/api/api/Conference"

OVERLAY_SCENE_NAME = "ConferenceOverlayScene"
ADVERTISEMENT_SCENE_NAME = "AdvertisementScene"

# Separate OBS text sources
SPEAKER_TEXT_SOURCE_NAME = "SpeakerNameText"
TOPIC_TEXT_SOURCE_NAME = "TalkTopicText"
CONFERENCE_TEXT_SOURCE_NAME = "ConferenceNameText"
COUNTDOWN_TEXT_SOURCE_NAME = "CountdownText"   # optional / manual
BUZZER_SOURCE_NAME = "BuzzerSource"
TIME_UP_TEXT = "TIME'S UP"
# API endpoints
GET_ALL_SESSIONS_ENDPOINT = f"{BASE_URL}/GetSession"
GET_SESSION_BY_ID_ENDPOINT = f"{BASE_URL}/Get-Session"
timer_thread = None
timer_stop_event = threading.Event()
timer_lock = threading.Lock()
active_timer_key = None
def build_overlay_fields(
    session: Dict[str, Any],
    current_detail: Dict[str, Any],
    conference_name: str = ""
) -> Dict[str, str]:
    speaker = normalize(current_detail.get("nameOfSpeaker")) or "—"
    topic = normalize(current_detail.get("topic")) or "—"

    final_conference_name = (
        normalize(conference_name)
        or normalize(session.get("conferenceName"))
        or "—"
    )

    return {
        "speakerName": speaker,
        "talkTopic": topic,
        "conferenceName": final_conference_name,
    }
def send_overlay_fields_to_obs(
    speaker_name: str,
    talk_topic: str,
    conference_name: str
) -> None:
    # speaker name
    set_obs_text(SPEAKER_TEXT_SOURCE_NAME, speaker_name)

    # talk topic
    set_obs_text(TOPIC_TEXT_SOURCE_NAME, talk_topic)

    # conference name
    set_obs_text(CONFERENCE_TEXT_SOURCE_NAME, conference_name)

    # countdown ko फिलहाल blank ya manual chhod do
    try:
        set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, "")
    except Exception:
        pass

    # switch to live conference scene
    switch_scene(OVERLAY_SCENE_NAME)
def send_preview_fields_to_obs(
    speaker_name: str,
    talk_topic: str,
    conference_name: str
) -> None:
    set_obs_text(SPEAKER_TEXT_SOURCE_NAME, speaker_name)
    set_obs_text(TOPIC_TEXT_SOURCE_NAME, talk_topic)
    set_obs_text(CONFERENCE_TEXT_SOURCE_NAME, conference_name)

    try:
        set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, "")
    except Exception:
        pass
# =========================
# HELPERS
# =========================

def obs_client() -> ReqClient:
    """Create OBS WebSocket client using runtime settings entered by user."""
    return obs_settings.create_client()


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
    """Fetch all sessions from backend."""
    data = safe_get(GET_ALL_SESSIONS_ENDPOINT)
    return data.get("data") or []


def get_session_details(session_id: str) -> List[Dict[str, Any]]:
    """
    Fetch talk details for a given sessionId.
    Endpoint: GET /Get-Session/{sessionId}
    """
    data = safe_get(f"{GET_SESSION_BY_ID_ENDPOINT}/{session_id}")
    return data.get("data") or []


def find_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Find session metadata (name, hall, location, chairperson, etc.)
    by iterating GetSession list.
    """
    sessions = get_all_sessions()
    for session in sessions:
        if normalize(session.get("id")) == normalize(session_id):
            return session
    return None


def sort_details(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort talk details by startTime ascending, then createdDate as tiebreaker.
    This matches the Angular frontend sort logic.
    """
    def sort_key(detail: Dict[str, Any]):
        start_time = normalize(detail.get("startTime"))
        created_date = normalize(detail.get("createdDate"))
        return (start_time or "99:99:99", created_date or "9999-12-31T23:59:59")

    return sorted(details, key=sort_key)


def find_detail_by_id(
    details: List[Dict[str, Any]], detail_id: str
) -> Optional[Dict[str, Any]]:
    for detail in details:
        if normalize(detail.get("id")) == normalize(detail_id):
            return detail
    return None


def find_next_detail(
    details: List[Dict[str, Any]], current_detail_id: str
) -> Optional[Dict[str, Any]]:
    """Return the talk immediately after the current one (sorted order)."""
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
    """Build the main OBS overlay text for the current talk."""
    session_name = normalize(session.get("sessionName")) or "—"
    hall_name    = normalize(session.get("hallName"))    or "—"
    location     = normalize(session.get("location"))   or "—"
    chair        = normalize(session.get("chairPersonName")) or "—"

    topic    = normalize(current_detail.get("topic"))         or "—"
    speaker  = normalize(current_detail.get("nameOfSpeaker")) or "—"
    start_t  = hhmm(current_detail.get("startTime"))
    end_t    = hhmm(current_detail.get("endTime"))
    duration = duration_to_min(current_detail.get("time"))

    if next_detail:
        next_topic   = normalize(next_detail.get("topic"))         or "—"
        next_speaker = normalize(next_detail.get("nameOfSpeaker")) or "—"
        next_line    = f"Next: {next_topic} | {next_speaker}"
    else:
        next_line = "Next: No further talk in this session"

    return (
        f"{session_name}\n"
        f"Topic: {topic}\n"
        f"Speaker: {speaker}\n"
        f"Time: {start_t} - {end_t} | Duration: {duration}\n"
        f"Hall: {hall_name}\n"
        f"Location: {location}\n"
        f"Chair: {chair}\n"
        f"{next_line}"
    )


def build_next_talk_text(next_detail: Optional[Dict[str, Any]]) -> str:
    """Build the UP NEXT ticker text."""
    if not next_detail:
        return "No next talk"

    next_topic   = normalize(next_detail.get("topic"))         or "—"
    next_speaker = normalize(next_detail.get("nameOfSpeaker")) or "—"
    next_start   = hhmm(next_detail.get("startTime"))
    next_end     = hhmm(next_detail.get("endTime"))

    return f"UP NEXT: {next_topic} | {next_speaker} | {next_start} - {next_end}"


# =========================
# OBS ACTIONS
# =========================

def set_obs_text(source_name: str, text_value: str) -> None:
    """Update a text source in OBS."""
    client = obs_client()
    client.set_input_settings(
        name=source_name,
        settings={"text": text_value},
        overlay=True
    )


def switch_scene(scene_name: str) -> None:
    """Switch OBS to a named scene."""
    client = obs_client()
    client.set_current_program_scene(scene_name)


def send_overlay_to_obs(overlay_text: str, next_talk_text: Optional[str] = None) -> None:
    """
    Push overlay text to OBS text sources and switch to the overlay scene.
    Called on talk START.
    """
    # Set main overlay text
    set_obs_text(TEXT_SOURCE_NAME, overlay_text)

    # Set next talk ticker (best-effort — source may not exist in all scenes)
    if next_talk_text:
        try:
            set_obs_text(NEXT_TALK_TEXT_SOURCE_NAME, next_talk_text)
        except Exception:
            pass  # non-fatal

    # Switch to overlay scene
    switch_scene(OVERLAY_SCENE_NAME)


def send_preview_to_obs(overlay_text: str, next_talk_text: Optional[str] = None) -> None:
    """
    Push overlay text to OBS text sources WITHOUT switching scenes.
    Called on PREVIEW so operator can check text before going live.
    """
    set_obs_text(TEXT_SOURCE_NAME, overlay_text)

    if next_talk_text:
        try:
            set_obs_text(NEXT_TALK_TEXT_SOURCE_NAME, next_talk_text)
        except Exception:
            pass


def show_advertisement_scene() -> None:
    """
    Switch OBS to the advertisement scene.
    Called on talk END.
    """
    switch_scene(ADVERTISEMENT_SCENE_NAME)


def clear_overlay_text() -> None:
    stop_countdown_timer(clear_text=True)

    try:
        set_obs_text(SPEAKER_TEXT_SOURCE_NAME, "")
    except Exception:
        pass

    try:
        set_obs_text(TOPIC_TEXT_SOURCE_NAME, "")
    except Exception:
        pass

    try:
        set_obs_text(CONFERENCE_TEXT_SOURCE_NAME, "")
    except Exception:
        pass

    try:
        set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, "")
    except Exception:
        pass

    hide_buzzer_source()
# =========================
# MAIN BUSINESS LOGIC
# =========================

def get_overlay_payload(
    session_id: str,
    detail_id: str,
    conference_name: str = ""
) -> Dict[str, Any]:
    """
    Fetch session + talk data from backend and build overlay texts.
    Returns a dict with session, currentDetail, nextDetail, overlayText, nextTalkText.
    """
    # 1. Get session metadata (name, hall, location, chair)
    session = find_session_by_id(session_id)
    if not session:
        raise ValueError(f"Session not found for sessionId={session_id}")

    # 2. Get all talk details for this session
    details = get_session_details(session_id)
    if not details:
        raise ValueError(f"No session details found for sessionId={session_id}")

    # 3. Find the current talk
    current_detail = find_detail_by_id(details, detail_id)
    if not current_detail:
        raise ValueError(f"Session detail not found for detailId={detail_id}")

    # 4. Find the next talk (sorted by startTime)
    next_detail = find_next_detail(details, detail_id)

    # 5. Build OBS text strings
    overlay_fields = build_overlay_fields(
        session=session,
        current_detail=current_detail,
        conference_name=conference_name
    )

    return {
        "session": session,
        "currentDetail": current_detail,
        "nextDetail": next_detail,
        "speakerName": overlay_fields["speakerName"],
        "talkTopic": overlay_fields["talkTopic"],
        "conferenceName": overlay_fields["conferenceName"],
}

def duration_to_seconds(value: Optional[str]) -> int:
    """
    Convert HH:MM:SS into total seconds.
    Example: 00:10:00 -> 600
    """
    if not value:
        return 0

    try:
        parts = str(value).split(":")
        hours = int(parts[0]) if len(parts) > 0 else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


def format_countdown(seconds: int) -> str:
    if seconds < 0:
        seconds = 0

    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"

def set_scene_item_visibility(scene_name: str, source_name: str, visible: bool) -> None:
    client = obs_client()
    item = client.get_scene_item_id(scene_name=scene_name, source_name=source_name)
    client.set_scene_item_enabled(
        scene_name=scene_name,
        scene_item_id=item.scene_item_id,
        enabled=visible
    )


def show_buzzer_source() -> None:
    try:
        set_scene_item_visibility(OVERLAY_SCENE_NAME, BUZZER_SOURCE_NAME, True)
    except Exception:
        pass


def hide_buzzer_source() -> None:
    try:
        set_scene_item_visibility(OVERLAY_SCENE_NAME, BUZZER_SOURCE_NAME, False)
    except Exception:
        pass


def stop_countdown_timer(clear_text: bool = True) -> None:
    global timer_thread, active_timer_key

    with timer_lock:
        timer_stop_event.set()
        active_timer_key = None

    if clear_text:
        try:
            set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, "")
        except Exception:
            pass

    hide_buzzer_source()


def _countdown_worker(total_seconds: int, timer_key: str) -> None:
    """
    Internal worker thread:
    - updates CountdownText every second
    - when reaches zero, shows TIME'S UP and buzzer
    """
    try:
        hide_buzzer_source()

        remaining = total_seconds

        while remaining >= 0:
            if timer_stop_event.is_set():
                return

            with timer_lock:
                if active_timer_key != timer_key:
                    return

            if remaining == 0:
                set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, TIME_UP_TEXT)
                show_buzzer_source()

                # buzzer 5 sec ke liye visible rakho
                for _ in range(5):
                    if timer_stop_event.is_set():
                        hide_buzzer_source()
                        return
                    time.sleep(1)

                hide_buzzer_source()
                return

            set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, format_countdown(remaining))
            time.sleep(1)
            remaining -= 1

    except Exception as e:
        print(f"Countdown worker error: {e}")


def start_countdown_timer(duration_value: Optional[str], session_id: str, detail_id: str) -> None:
    """
    Starts a fresh countdown for current talk duration.
    Stops any old running timer first.
    """
    global timer_thread, active_timer_key

    total_seconds = duration_to_seconds(duration_value)

    # fallback: agar duration invalid ho
    if total_seconds <= 0:
        try:
            set_obs_text(COUNTDOWN_TEXT_SOURCE_NAME, "00:00")
        except Exception:
            pass
        return

    stop_countdown_timer(clear_text=False)
    timer_stop_event.clear()
    hide_buzzer_source()

    timer_key = f"{session_id}__{detail_id}"

    with timer_lock:
        active_timer_key = timer_key

    timer_thread = threading.Thread(
        target=_countdown_worker,
        args=(total_seconds, timer_key),
        daemon=True
    )
    timer_thread.start()