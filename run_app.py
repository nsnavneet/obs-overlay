import threading
import time
import webbrowser
import uvicorn

from app.main import app


def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    try:
        threading.Thread(target=open_browser, daemon=True).start()
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
    except Exception as e:
        print("ERROR STARTING APP:", str(e))
        input("Press Enter to exit...")