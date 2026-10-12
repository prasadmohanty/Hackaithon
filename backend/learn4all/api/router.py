"""A tiny, dependency-free router with path parameters and self-documentation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from ..models import DomainError

PARAM_RE = re.compile(r"\{(\w+)\}")


class MethodNotAllowed(DomainError):
    status = 405
    code = "method_not_allowed"


class RouteNotFound(DomainError):
    status = 404
    code = "route_not_found"


@dataclass
class Request:
    method: str
    path: str
    params: Dict[str, int] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    body: object = None

    def q_int(self, name: str) -> Optional[int]:
        value = self.query.get(name)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except ValueError:
            raise DomainError(f"Query parameter '{name}' must be an integer")

    def q_str(self, name: str) -> Optional[str]:
        value = self.query.get(name)
        return value.strip() if value not in (None, "") else None

    def q_bool(self, name: str, default: bool = False) -> bool:
        value = self.query.get(name)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")


@dataclass
class Route:
    method: str
    template: str
    handler: Callable
    summary: str
    tag: str
    status: int = 200
    query: List[Tuple[str, str]] = field(default_factory=list)
    body: Optional[dict] = None
    regex: re.Pattern = None

    def __post_init__(self):
        pattern = PARAM_RE.sub(lambda m: f"(?P<{m.group(1)}>\\d+)", self.template.rstrip("/"))
        self.regex = re.compile(f"^{pattern}/?$")


class Router:
    def __init__(self):
        self.routes: List[Route] = []

    def add(self, method: str, template: str, handler: Callable, summary: str, tag: str,
            status: int = 200, query=None, body=None) -> None:
        self.routes.append(Route(method.upper(), template, handler, summary, tag, status,
                                 list(query or []), body))

    def match(self, method: str, path: str) -> Tuple[Route, Dict[str, int]]:
        allowed = []
        for route in self.routes:
            m = route.regex.match(path)
            if m:
                if route.method == method:
                    return route, {k: int(v) for k, v in m.groupdict().items()}
                allowed.append(route.method)
        if allowed:
            raise MethodNotAllowed(f"{method} not allowed on {path}. Allowed: {', '.join(sorted(set(allowed)))}")
        raise RouteNotFound(f"No endpoint matches {method} {path}. See GET /api/docs")

    # --- self documentation --------------------------------------------------------
    def describe(self) -> List[dict]:
        return [{"method": r.method, "path": r.template, "summary": r.summary, "tag": r.tag,
                 "success_status": r.status,
                 "query": [{"name": n, "description": d} for n, d in r.query],
                 "body": r.body} for r in self.routes]

    def openapi(self, title: str, version: str, server_url: str) -> dict:
        paths: Dict[str, dict] = {}
        for r in self.routes:
            parameters = [{"name": p, "in": "path", "required": True, "schema": {"type": "integer"}}
                          for p in PARAM_RE.findall(r.template)]
            parameters += [{"name": n, "in": "query", "required": False, "description": d,
                            "schema": {"type": "string"}} for n, d in r.query]
            op = {"summary": r.summary, "tags": [r.tag], "parameters": parameters,
                  "responses": {str(r.status): {"description": "Success",
                                                "content": {"application/json": {}}},
                                "4XX": {"description": "Error envelope: {error: {code, message, details}}"}}}
            if r.body:
                op["requestBody"] = {"required": True, "content": {"application/json": {
                    "schema": {"type": "object", "example": r.body}}}}
            paths.setdefault(r.template, {})[r.method.lower()] = op
        return {"openapi": "3.0.3",
                "info": {"title": title, "version": version,
                         "description": "Learn4All REST API. All bodies are JSON (UTF-8)."},
                "servers": [{"url": server_url}], "paths": paths}
