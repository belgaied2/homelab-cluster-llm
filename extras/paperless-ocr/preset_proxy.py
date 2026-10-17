"""Tiny reverse proxy in front of docling-serve.

paperless-gpt v0.31.0 sends `pipeline=vlm` but never a `vlm_pipeline_preset`, and docling-serve
v1.37.0 only applies its server default (`default_vlm_preset`) when a request asks for the preset
named "default". With no preset it falls back to the built-in local Granite model, which the CPU
image doesn't ship. This proxy appends `vlm_pipeline_preset=default` to multipart requests on
POST /v1/convert/file that use pipeline=vlm and name no preset. Everything else passes through.
Standard library only.
"""
import http.client
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = os.environ.get("UPSTREAM_HOST", "docling")
UPSTREAM_PORT = int(os.environ.get("UPSTREAM_PORT", "5001"))
PRESET = os.environ.get("VLM_PRESET", "default")
TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT", "900"))
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
       "proxy-authorization", "proxy-authenticate", "host", "content-length"}


def inject_preset(body: bytes, content_type: str) -> bytes:
    m = re.search(r'boundary="?([^";]+)"?', content_type or "")
    if not m:
        return body
    boundary = m.group(1).encode()
    if b'name="vlm_pipeline_preset"' in body:
        return body                      # caller chose a preset: respect it
    if not re.search(rb'name="pipeline"\r\n\r\nvlm\r\n', body):
        return body                      # standard pipeline: nothing to do
    closing = b"--" + boundary + b"--"
    idx = body.rfind(closing)
    if idx < 0:
        return body
    part = (b"--" + boundary + b'\r\nContent-Disposition: form-data; name="vlm_pipeline_preset"\r\n\r\n'
            + PRESET.encode() + b"\r\n")
    return body[:idx] + part + body[idx:]


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        injected = False
        if self.command == "POST" and self.path.split("?")[0] == "/v1/convert/file":
            new = inject_preset(body, self.headers.get("Content-Type", ""))
            injected, body = new is not body and new != body, new
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["Content-Length"] = str(len(body))
        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=TIMEOUT)
        try:
            conn.request(self.command, self.path, body=body or None, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
        except Exception as e:  # upstream down or timeout
            msg = f'{{"detail":"preset-proxy upstream error: {e}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        finally:
            conn.close()
        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        if injected:
            print(f"injected vlm_pipeline_preset={PRESET} -> {resp.status}", flush=True)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _forward

    def log_message(self, fmt, *args):
        if "/health" not in (args[0] if args else ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "5002"))), Proxy).serve_forever()
