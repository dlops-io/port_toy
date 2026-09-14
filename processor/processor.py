"""processor — container B.

It listens on a port (from $PORT, default 9200). This port is NOT published to
your laptop, so the only way to reach it is from inside the Docker network,
using its name: "processor". It gets a message, does a little work on it, and
sends a reply back.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os


class Processor(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        # 1. read the JSON message the gateway forwarded to us
        size = int(self.headers["Content-Length"])
        message = json.loads(self.rfile.read(size))
        text = message["text"]

        # 2. do the "work" — just upper-case it — plus note the ports involved
        reply = {
            "upper": text.upper(),                         # the reply: just the upper-case text
            "listen_port": self.server.server_address[1],  # the real port we're bound to
            "sender_port": self.client_address[1],         # the port the gateway came from
        }

        # 3. send the reply back
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode())


port = int(os.environ.get("PORT", "9200"))
server = HTTPServer(("", port), Processor)
print(f"processor listening on port {server.server_address[1]} (internal only)")
server.serve_forever()
