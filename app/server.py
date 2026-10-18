"""Small stateless release probe. No customer data or AWS API access."""
import json
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/healthz":
            status, payload = 200, {"status": "ok"}
        elif path == "/readyz":
            ready = os.getenv("FAIL_READINESS", "false").lower() != "true"
            status, payload = (200 if ready else 503), {"ready": ready}
        elif path == "/":
            status, payload = 200, {"service": "release-probe", "revision": os.getenv("APP_REVISION", "local")}
        else:
            status, payload = 404, {"error": "not found"}
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Do not log query strings, headers or client IP addresses.
        print(json.dumps({"event": "http_request", "method": self.command}), flush=True)


def main():
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler)
    server.daemon_threads = True
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever()
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
