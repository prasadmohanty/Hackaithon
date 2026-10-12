"""HTTP layer built on the standard library's http.server.

Translates HTTP requests into Router lookups, adds CORS headers so a
frontend served from a different origin can call the API, and maps domain
errors to JSON error responses.
"""

from __future__ import annotations

import json
import logging
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .. import __version__
from ..config import CORS_ALLOWED_ORIGINS
from ..models import DomainError
from ..services import Learn4AllService
from .router import Request, Router
from .routes import build_router

log = logging.getLogger("learn4all.api")
MAX_BODY_BYTES = 2 * 1024 * 1024


class ApiRequestHandler(BaseHTTPRequestHandler):
    server_version = f"Learn4All/{__version__}"
    router: Router = None
    allowed_origins = CORS_ALLOWED_ORIGINS

    # --- HTTP verbs -------------------------------------------------------------------
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    # --- core -------------------------------------------------------------------------------
    def _dispatch(self, method: str) -> None:
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"
        try:
            if path in ("/", "/api") and method == "GET":
                return self._send(200, self._index())
            if path == "/api/openapi.json" and method == "GET":
                host = self.headers.get("Host") or f"{self.server.server_address[0]}:{self.server.server_address[1]}"
                return self._send(200, self.router.openapi("Learn4All API", __version__, f"http://{host}"))
            route, params = self.router.match(method, path)
            request = Request(method, path, params,
                              {k: v[0] for k, v in parse_qs(url.query).items()}, self._read_body())
            self._send(route.status, route.handler(request))
        except DomainError as exc:
            self._send(exc.status, {"error": exc.to_dict()})
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            log.error("Unhandled error on %s %s\n%s", method, self.path, traceback.format_exc())
            self._send(500, {"error": {"code": "internal_error", "message": str(exc), "details": []}})

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return None
        if length > MAX_BODY_BYTES:
            raise DomainError("Request body too large (max 2 MB)")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise DomainError("Request body must be valid UTF-8 JSON")

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        allowed = [o.strip() for o in self.allowed_origins.split(",")]
        if "*" in allowed:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

    def _send(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _index(self) -> dict:
        return {"name": "Learn4All API", "version": __version__,
                "description": "Inclusive Learning Progress & Resource Planner (SDG 4 & SDG 10)",
                "links": {"docs": "/api/docs", "openapi": "/api/openapi.json", "health": "/api/health",
                          "meta": "/api/meta", "students": "/api/students",
                          "class_report": "/api/reports/class"}}

    def log_message(self, fmt, *args):
        log.info("%s - %s", self.address_string(), fmt % args)


def create_server(service: Learn4AllService, host: str, port: int) -> ThreadingHTTPServer:
    """Build a threaded HTTP server bound to the given service."""
    handler = type("BoundApiRequestHandler", (ApiRequestHandler,), {"router": build_router(service)})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
