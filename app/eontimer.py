from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import subprocess
import os

def start_eontimer():
    os.chdir("app/third_party/eontimer/EonTimer")

    server = HTTPServer(
        ("127.0.0.1", 8000),
        SimpleHTTPRequestHandler
    )

    threading.Thread(
        target=server.serve_forever,
        daemon=True
    ).start()

    subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--kiosk",
        "http://127.0.0.1:8000"
    ])

