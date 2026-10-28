"""Run the users service."""

from services.platformhttp.server import serve
from services.users.handlers import build_app

if __name__ == "__main__":
    serve(build_app())
