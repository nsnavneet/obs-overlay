from typing import Optional, Dict, Any
from obsws_python import ReqClient


class OBSSettingsStore:
    def __init__(self):
        self.host: str = ""
        self.port: int = 4455
        self.password: str = ""
        self.is_connected: bool = False

    def set_settings(self, host: str, port: int, password: str):
        self.host = host.strip()
        self.port = int(port)
        self.password = password.strip()
        self.is_connected = True

    def clear(self):
        self.host = ""
        self.port = 4455
        self.password = ""
        self.is_connected = False

    def get_settings(self) -> Dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "password": self.password,
            "is_connected": self.is_connected,
        }

    def create_client(self) -> ReqClient:
        if not self.host or not self.password:
            raise ValueError("OBS not configured. Please enter OBS IP and password first.")
        return ReqClient(
            host=self.host,
            port=self.port,
            password=self.password,
            timeout=5
        )


obs_settings = OBSSettingsStore()