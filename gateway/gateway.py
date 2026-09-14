"""gateway — container A.

It listens on a port (from $PORT, default 9100), which is published to your
laptop as 8090. So you open http://localhost:8090 in a browser and it serves a
web page (index.html). When you send text from that page, the gateway forwards
it to the other container — "processor" — and passes processor's reply back.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
import json
import os

PROCESSOR_HOST = os.environ.get("PROCESSOR_HOST", "processor")
PROCESSOR_PORT = int(os.environ.get("PROCESSOR_PORT", "9200"))


class Gateway(BaseHTTPRequestHandler):
    def do_GET(self):
        # the browser asked for the page → send index.html back
        with open("index.html", "rb") as f:
            page = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        # the page sent us some text → read it
        size = int(self.headers["Content-Length"])
        text_from_browser = self.rfile.read(size)

        # open a connection to the processor container BY NAME, on its port
        conn = http.client.HTTPConnection(PROCESSOR_HOST, PROCESSOR_PORT)
        conn.request("POST", "/", body=text_from_browser,
                     headers={"Content-Type": "application/json"})

        # the OS gave our outgoing connection a source port — read the real one
        out_port = conn.sock.getsockname()[1]

        reply = json.loads(conn.getresponse().read())
        conn.close()
        reply["gateway_out_port"] = out_port   # the port we sent from

        # hand the (enriched) reply back to the browser
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode())


port = int(os.environ.get("PORT", "9100"))
server = HTTPServer(("", port), Gateway)
print(f"gateway listening on port {server.server_address[1]}  →  open http://localhost:8090")
server.serve_forever()
