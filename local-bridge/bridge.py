#!/usr/bin/env python3
"""Localhost-only bridge: send a YouTube URL to the repository workflow."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

OWNER = os.environ.get("GITHUB_OWNER", "unisocsu")
REPO = os.environ.get("GITHUB_REPO", "yt-download")
WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "ytdlp-download.yml")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
PORT = int(os.environ.get("BRIDGE_PORT", "8765"))
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "chrome-extension://*")
        self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "null"))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/download":
            return self.send_json(404, {"error": "Not found"})
        origin = self.headers.get("Origin", "")
        if not origin.startswith("chrome-extension://"):
            return self.send_json(403, {"error": "Requests must come from the browser extension."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 16384:
                return self.send_json(400, {"error": "Invalid request size."})
            data = json.loads(self.rfile.read(length))
            url = str(data.get("url", "")).strip()
            fmt = data.get("format", "mp4")
            parsed = urlparse(url)
            if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
                return self.send_json(400, {"error": "Only HTTPS YouTube URLs are accepted."})
            if fmt not in ("mp4", "original"):
                return self.send_json(400, {"error": "Unsupported format."})
            if not TOKEN:
                return self.send_json(500, {"error": "Set GITHUB_TOKEN in the local environment first."})
            api = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
            body = json.dumps({"ref": "main", "inputs": {"url": url, "format": fmt}}).encode("utf-8")
            req = Request(api, data=body, method="POST", headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + TOKEN,
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "yt-download-local-bridge"
            })
            try:
                with urlopen(req, timeout=25) as response:
                    if response.status not in (200, 201, 204):
                        return self.send_json(502, {"error": f"GitHub API returned HTTP {response.status}."})
            except HTTPError as exc:
                return self.send_json(502, {"error": f"GitHub API returned HTTP {exc.code}. Check token permissions and workflow filename."})
            except URLError as exc:
                return self.send_json(502, {"error": f"Could not reach GitHub API: {exc.reason}"})
            return self.send_json(200, {"ok": True, "message": "Workflow dispatch accepted. Open Actions to see its run."})
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": "Invalid JSON request."})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    if not TOKEN:
        print("WARNING: GITHUB_TOKEN is not set; requests will fail until you set it.")
    print(f"Listening only on 127.0.0.1:{PORT}. Press Ctrl+C to stop.")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
