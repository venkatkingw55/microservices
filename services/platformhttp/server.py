"""Small JSON HTTP server used by every platform service.

The process listens on ``PORT`` (default 8080), answers the health paths the
Helm chart probes, logs JSON to stdout, and drains on SIGTERM.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import threading
import time
from collections import Counter
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY_BYTES = 1_048_576

Handler = Callable[["Request"], "Response"]


class Request:
    def __init__(self, method: str, path: str, headers: dict[str, str], body: dict):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.params: dict[str, str] = {}


class Response:
    def __init__(self, status: int, payload: object, content_type: str = "application/json"):
        self.status = status
        self.payload = payload
        self.content_type = content_type


def ok(payload: dict) -> Response:
    return Response(200, payload)


def created(payload: dict) -> Response:
    return Response(201, payload)


def error(status: int, message: str) -> Response:
    return Response(status, {"error": message})


class Route:
    def __init__(self, method: str, pattern: str, handler: Handler):
        names = re.findall(r"{([A-Za-z_][A-Za-z0-9_]*)}", pattern)
        expression = "^" + re.sub(r"{[A-Za-z_][A-Za-z0-9_]*}", "([^/]+)", pattern) + "$"
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self._names = names
        self._expression = re.compile(expression)

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if method != self.method:
            return None
        found = self._expression.match(path)
        if found is None:
            return None
        return dict(zip(self._names, found.groups(), strict=True))


class Application:
    def __init__(self, name: str, routes: list[Route]):
        self.name = name
        self.ready = True
        self._lock = threading.Lock()
        self._requests: Counter[tuple[str, int]] = Counter()
        self.routes = [
            Route("GET", "/health/startup", self._startup),
            Route("GET", "/health/ready", self._ready),
            Route("GET", "/health/live", self._live),
            Route("GET", "/metrics", self._metrics),
            *routes,
        ]

    def mark_not_ready(self) -> None:
        with self._lock:
            self.ready = False

    def dispatch(self, request: Request) -> tuple[Response, str]:
        for route in self.routes:
            params = route.match(request.method, request.path)
            if params is None:
                continue
            request.params = params
            try:
                response = route.handler(request)
            except Exception:
                logging.getLogger(self.name).exception("request failed")
                response = error(500, "internal error")
            self._record(route.pattern, response.status)
            return response, route.pattern
        response = error(404, "not found")
        self._record("unmatched", response.status)
        return response, "unmatched"

    def _record(self, route: str, status: int) -> None:
        with self._lock:
            self._requests[(route, status)] += 1

    def _startup(self, _request: Request) -> Response:
        return ok({"status": "ok", "service": self.name})

    def _ready(self, _request: Request) -> Response:
        with self._lock:
            accepting = self.ready
        if not accepting:
            return Response(503, {"status": "not ready", "service": self.name})
        return ok({"status": "ok", "service": self.name})

    def _live(self, _request: Request) -> Response:
        return ok({"status": "ok", "service": self.name})

    def _metrics(self, _request: Request) -> Response:
        lines = [
            "# HELP http_requests_total HTTP requests handled by this process.",
            "# TYPE http_requests_total counter",
        ]
        with self._lock:
            snapshot = list(self._requests.items())
        for (route, status), count in sorted(snapshot):
            lines.append(
                f'http_requests_total{{service="{self.name}",route="{route}",status="{status}"}} {count}'
            )
        return Response(200, "\n".join(lines) + "\n", content_type="text/plain; version=0.0.4")


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "service": self.service,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(service: str) -> None:
    level_name = os.environ.get("LOG_LEVEL", "info").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    if os.environ.get("LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(JsonFormatter(service))
    logger = logging.getLogger(service)
    logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False


def _handler_class(app: Application) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            self._handle()

        def do_POST(self) -> None:  # noqa: N802
            self._handle()

        def _handle(self) -> None:
            started = time.perf_counter()
            path = self.path.split("?", 1)[0]
            body, failure = self._read_body()
            if failure is not None:
                response, route = failure, "unmatched"
            else:
                headers = {key.lower(): value for key, value in self.headers.items()}
                response, route = app.dispatch(Request(self.command, path, headers, body))
            self._write(response)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger = logging.getLogger(app.name)
            message = "request method=%s path=%s status=%s duration_ms=%s"
            values = (self.command, path, response.status, elapsed_ms)
            if route.startswith("/health") or route == "/metrics":
                logger.debug(message, *values)
            else:
                logger.info(message, *values)

        def _read_body(self) -> tuple[dict, Response | None]:
            if self.command not in {"POST", "PUT", "PATCH"}:
                return {}, None
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                return {}, error(400, "invalid content length")
            if length < 0 or length > MAX_BODY_BYTES:
                return {}, error(413, "request body is too large")
            if length == 0:
                return {}, None
            raw = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "")
            if "application/json" not in content_type.lower():
                return {}, error(415, "content type must be application/json")
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}, error(400, "invalid json")
            if not isinstance(parsed, dict):
                return {}, error(400, "json body must be an object")
            return parsed, None

        def _write(self, response: Response) -> None:
            if response.content_type.startswith("application/json"):
                encoded = json.dumps(response.payload, separators=(",", ":")).encode("utf-8")
            else:
                encoded = str(response.payload).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def start_background(app: Application, host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    """Start the app on a background thread. Used by service tests."""
    server = ThreadingHTTPServer((host, port), _handler_class(app))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    bound_host, bound_port = server.server_address[:2]
    return server, f"http://{bound_host}:{bound_port}"


def stop_background(server: ThreadingHTTPServer) -> None:
    server.shutdown()
    server.server_close()


def serve(app: Application) -> None:
    """Listen until SIGINT or SIGTERM, then stop accepting and finish in-flight requests."""
    configure_logging(app.name)
    logger = logging.getLogger(app.name)
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _handler_class(app))
    server.daemon_threads = True

    def handle_stop(signum: int, _frame: object) -> None:
        logger.info("shutting down signal=%s", signum)
        app.mark_not_ready()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    logger.info("listening port=%s env=%s", port, os.environ.get("APP_ENV", "local"))
    try:
        server.serve_forever()
    finally:
        server.server_close()
        logger.info("stopped")
