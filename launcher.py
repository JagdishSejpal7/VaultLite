"""Entry point of the desktop app (this is what the .exe runs).
Starts the Flask server on a private local port and shows it in a native window."""
import ctypes
import os
import socket
import sys
import threading
import time
import webbrowser

import product


def show_error(message):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(0, message, product.APP_NAME, 0x10)
    else:
        print(message, file=sys.stderr)


def acquire_single_instance():
    """Only one copy may run (a second launch would fight over the same database)."""
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", 47931))
    except OSError:
        show_error(f"{product.APP_NAME} is already running.")
        sys.exit(0)
    return lock


def main():
    _lock = acquire_single_instance()          # keep reference alive for the whole run
    from waitress.server import create_server
    import app as vault

    server = create_server(vault.app, host="127.0.0.1", port=0)   # port 0 = any free port
    port = server.effective_port
    vault.app.config["ALLOWED_HOSTS"] = {f"127.0.0.1:{port}", f"localhost:{port}"}
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"

    try:
        import webview                          # native window using Edge WebView2
        webview.create_window(product.APP_NAME, url, width=1200, height=780,
                              min_size=(900, 600), background_color="#0f1020")
        webview.start()                         # blocks until the window is closed
    except Exception:
        # WebView2 missing on an old PC -> fall back to the default browser.
        webbrowser.open(url)
        started = time.time()
        while True:                             # quit automatically when the tab is closed
            time.sleep(5)
            beat = vault.LAST_HEARTBEAT["t"]
            if beat is None and time.time() - started > 60:
                break
            if beat is not None and time.time() - beat > 150:
                break
    os._exit(0)


if __name__ == "__main__":
    main()
