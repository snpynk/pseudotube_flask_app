import json
from urllib.parse import urlencode
import os
import secrets

from google.cloud import secretmanager

import requests
from flask import Flask, render_template, request, session, url_for, redirect
from flask_login import current_user, login_user, logout_user, LoginManager, UserMixin

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)

login = LoginManager(app)


class User(UserMixin):
    def __init__(self, email, provider):
        self.id = email
        self.email = email
        self.provider = provider


@login.user_loader
def user_loader(id):
    if id:
        return User(email=id, provider="google")

    return None


@app.route("/")
def route_index():
    return render_template("index.html", user=current_user)


@app.route("/search", methods=["GET", "POST"])
def route_search():
    return "Hey"


@app.route("/upload", methods=["POST"])
def route_upload():
    dom_video_input_name = "video_file"

    if not (request and request.files and dom_video_input_name in request.files.keys()):
        return "No file part in the request", 400

    file = request.files[dom_video_input_name]

    if file.filename == "":
        return "File name is empty", 400

    if not file:
        return "No file selected", 400

    # Bucket logic

    return "Video uploaded successfully", 200


@app.route("/video/<video_id>", methods=["GET"])
def route_video(video_id):
    return f"Video ID: {video_id}"


@app.route("/logout")
def route_logout():
    if current_user.is_authenticated:
        logout_user()
        return "Logged out successfully", 200

    return "You are not logged in", 400


@app.route("/authorize/<provider>")
def route_oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("route_index"))

    if provider not in OAUTH_PROVIDERS:
        return "Invalid OAuth2 provider", 400

    provider_data = OAUTH_PROVIDERS.get(provider)

    if not provider_data:
        return "Provider data not found", 400

    session["oauth2_state"] = secrets.token_urlsafe(16)

    qs = urlencode(
        {
            "client_id": provider_data["client_id"],
            "redirect_uri": url_for(
                "route_oauth2_callback", provider=provider, _external=True
            ),
            "response_type": "code",
            "scope": " ".join(provider_data["scopes"]),
            "state": session.get("oauth2_state"),
        }
    )

    return redirect(provider_data["auth_uri"] + "?" + qs)


@app.route("/auth_callback/<provider>")
def route_oauth2_callback(provider):
    if provider not in OAUTH_PROVIDERS:
        return "Invalid OAuth2 provider", 400

    provider_data = OAUTH_PROVIDERS.get(provider)

    if "error" in request.args:
        return f"Error during OAuth2 authorization: {request.args['error']}", 400

    if "code" not in request.args or "state" not in request.args:
        return "Missing code or state in the callback", 400

    if request.args["state"] != session.get("oauth2_state"):
        return "State mismatch", 400

    if not provider_data:
        return "Provider data not found", 400

    response_token = requests.post(
        provider_data["token_uri"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": url_for(
                "route_oauth2_callback", provider=provider, _external=True
            ),
        },
        headers={"Accept": "application/json"},
    )

    if response_token.status_code != 200:
        return f"Error fetching OAuth2 token: {response_token.text}", 400

    oauth2_token = response_token.json().get("access_token")
    if not oauth2_token:
        return "No access token received", 400

    response_userinfo = requests.get(
        provider_data["userinfo"]["url"],
        headers={
            "Authorization": "Bearer " + oauth2_token,
            "Accept": "application/json",
        },
    )

    if response_userinfo.status_code != 200:
        return f"Error fetching user info: {response_userinfo.text}", 400

    email = provider_data["userinfo"]["email"](response_userinfo.json())

    user = User(email=email, provider=provider)

    login_user(user)

    return redirect(url_for("route_index"))


def setup_oauth_providers():
    global OAUTH_PROVIDERS

    google_oauth_cred_filename = "client_secrets.apps.googleusercontent.com.json"

    if not os.path.exists(google_oauth_cred_filename):
        oauth2_providers = get_oath2_providers()
        google_provider_data = json.loads(oauth2_providers)["web"]

    else:
        with open(google_oauth_cred_filename, "r") as f:
            google_provider_data = json.load(f)["web"]

    if not google_provider_data:
        raise ValueError("Google OAuth2 credentials not found in the file.")

    google_provider_data["scopes"] = ["https://www.googleapis.com/auth/userinfo.email"]
    google_provider_data["userinfo"] = {
        "url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "email": lambda data: data.get("email"),
    }

    OAUTH_PROVIDERS = {
        "google": google_provider_data,
    }


def get_oath2_providers():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/pseudotube/secrets/oauth2_providers/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


if __name__ == "__main__":
    setup_oauth_providers()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
