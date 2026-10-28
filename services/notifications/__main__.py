"""Run the notifications service."""

from services.platformhttp.server import serve
from services.notifications.handlers import build_app

if __name__ == "__main__":
    serve(build_app())
