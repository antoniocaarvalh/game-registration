import subprocess
import sys
import os
import time
import socket
import threading
import webview

APP_DIR  = os.path.dirname(os.path.abspath(__file__))
APP_FILE = os.path.join(APP_DIR, "app.py")
PORT     = 8501


def _streamlit_ready(timeout=30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _start_streamlit():
    subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", APP_FILE,
            "--server.headless", "true",
            "--server.port", str(PORT),
            "--browser.gatherUsageStats", "false",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
        ],
        cwd=APP_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    thread = threading.Thread(target=_start_streamlit, daemon=True)
    thread.start()

    if not _streamlit_ready():
        print("Erro: não foi possível iniciar o servidor Streamlit.")
        sys.exit(1)

    window = webview.create_window(
        title="🎮 Game Registration",
        url=f"http://127.0.0.1:{PORT}",
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True,
    )
    webview.start()
