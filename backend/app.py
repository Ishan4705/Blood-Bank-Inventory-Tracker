from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask

from backend.routes import api


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix="/api")
    return app


app = create_app()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=debug_mode,
    )
