import secrets
from json import loads
from typing import TypedDict
from urllib.parse import urlencode

import requests
from flask import redirect, session, url_for


class Userinfo(TypedDict):
    name: str
    email: str
    locale: str
    picture: str


class OAuthProviderManager:
    def __init__(self, providers_json):
        self.providers = {}
        self.providers_json = providers_json

    def setup(self):
        google_provider_data = self.get_oath2_providers_secret()[0].get("web")

        if not google_provider_data:
            raise ValueError(
                "Google OAuth2 credentials not found in the secret manager."
            )

        if not google_provider_data:
            raise ValueError("Google OAuth2 credentials not found in the file.")

        google_provider_data["scopes"] = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

        google_provider_data["userinfo"] = {
            "url": "https://www.googleapis.com/oauth2/v3/userinfo",
        }

        self.providers["google"] = google_provider_data

    def is_provider(self, provider):
        return provider in self.providers

    def authorize(self, provider):
        if not self.is_provider(provider):
            raise ValueError(f"Invalid OAuth2 provider: {provider}")

        provider_data = self.providers.get(provider)

        if not provider_data:
            raise ValueError(f"Provider data not found for: {provider}")

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

    def oauth_callback(self, request, provider):
        provider_data = self.get_provider(provider)

        if "error" in request.args:
            raise ValueError(f"OAuth2 authorization error: {request.args['error']}")

        if "code" not in request.args or "state" not in request.args:
            raise ValueError("Missing 'code' or 'state' in the request arguments")

        if request.args["state"] != session.pop("oauth2_state", None):
            raise ValueError("Invalid OAuth2 state parameter")

        if not provider_data:
            raise ValueError("Provider data not found")

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
            raise ValueError(f"Error fetching OAuth2 token: {response_token.text}")

        oauth2_token = response_token.json().get("access_token")
        if not oauth2_token:
            raise ValueError("Access token not found in the response")

        response_userinfo = requests.get(
            provider_data["userinfo"]["url"],
            headers={
                "Authorization": "Bearer " + oauth2_token,
                "Accept": "application/json",
            },
        )

        if response_userinfo.status_code != 200:
            raise ValueError(f"Error fetching user info: {response_userinfo.text}")

        if not response_userinfo.json():
            raise ValueError("User info not found in the response")

        json_data: Userinfo = response_userinfo.json()

        return json_data

    def get_provider(self, name):
        if not self.is_valid_provider(name):
            raise ValueError("Invalid OAuth2 provider")

        return self.providers[name]

    def is_valid_provider(self, name):
        return name in self.providers

    def get_oath2_providers_secret(self) -> list[dict]:
        return loads(self.providers_json)
