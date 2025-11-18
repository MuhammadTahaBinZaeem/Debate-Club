"""Flask entrypoint bootstrapping REST and WebSocket interfaces."""
from __future__ import annotations

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from config import settings
from routes.api import api_bp
from routes.healthcheck import health_bp
from routes.websocket import register_socketio_events
from utils.logger import configure_logging

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    CORS(app, origins=settings.cors_origins, supports_credentials=True)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(health_bp)
    return app


app = create_app()
socketio = SocketIO(app, cors_allowed_origins=settings.cors_origins, async_mode="eventlet")
register_socketio_events(socketio)


if __name__ == "__main__":  # pragma: no cover - manual execution
    configure_logging()
    socketio.run(app, host=settings.app_host, port=settings.app_port)
