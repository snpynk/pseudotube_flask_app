import os
import secrets
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask import Flask, redirect, url_for

from . import routes

from .context import (
    db,
    login_manager,
    provider_manager,
)


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = secrets.token_urlsafe(16)

    load_dotenv()

    DB_USER = os.getenv("PSEUDOTUBE_DB_USER", "root")
    DB_PASS = os.getenv("PSEUDOTUBE_DB_PASS", "password")
    DB_INSTANCE = os.getenv("PSEUDOTUBE_DB_INSTANCE", "")
    DB_NAME = os.getenv("PSEUDOTUBE_DB_NAME", "")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}"
        f"@/{DB_NAME}?unix_socket={DB_INSTANCE}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager.init_app(app)

    provider_manager.setup()

    app.register_blueprint(routes.user.route_user_bp)
    app.register_blueprint(routes.main.main_bp)
    app.register_blueprint(routes.search.route_search_bp)
    app.register_blueprint(routes.upload.route_upload_bp)
    app.register_blueprint(routes.watch.route_watch_bp)
    app.register_blueprint(routes.video.route_video_bp)
    app.register_blueprint(routes.transcoder.route_transcoder_bp)

    @app.route("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.ico"))

    @app.route("/apple-touch-icon.png")
    def apple_touch_icon():
        return redirect(url_for("static", filename="apple-touch-icon.png"))

    @app.route("/android-chrome-192x192.png")
    def android_chrome_192x192():
        return redirect(url_for("static", filename="android-chrome-192x192.png"))

    @app.route("/android-chrome-512x512.png")
    def android_chrome_512x512():
        return redirect(url_for("static", filename="android-chrome-512x512.png"))

    @app.route("/site.webmanifest")
    def site_webmanifest():
        return redirect(url_for("static", filename="site.webmanifest"))

    with app.app_context():
        db.create_all()

    return app
