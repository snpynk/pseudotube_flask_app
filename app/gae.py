import os
from json import dumps

from google.cloud import secretmanager


class GAE:
    def __init__(self):
        self.PROJECT_NAME = os.getenv("PSEUDOTUBE_GCP_PROJECT", "pseudotube")
        self.GCP_BUCKET_NAME = os.getenv(
            "PSEUDOTUBE_GCP_BUCKET_NAME", "pseudotube-video-storage"
        )
        self.PSEUDOTUBE_GCP_CREDENTIALS = os.getenv("PSEUDOTUBE_GCP_CREDENTIALS", None)
        self.OAUTH2_PROVIDERS = os.getenv("PSEUDOTUBE_OAUTH2_PROVIDERS", None)

        if "IS_GAE" in os.environ:
            self.client = secretmanager.SecretManagerServiceClient()

            self.OAUTH2_PROVIDERS = dumps([self.get_secret_oauth2()])

            self.GCP_BUCKET_CREDENTIALS = dumps(self.get_secret_storage())

        else:
            google_oauth_cred_filename = "oauth2.creds.json"

            if os.path.exists(google_oauth_cred_filename):
                with open(google_oauth_cred_filename, "r") as f:
                    self.OAUTH2_PROVIDERS = f"[{f.read()}]"

            google_storage_cred_filename = "storage.creds.json"

            if os.path.exists(google_storage_cred_filename):
                with open(google_storage_cred_filename, "r") as f:
                    self.GCP_BUCKET_CREDENTIALS = f.read()

    def get_secret_oauth2(self):
        name = f"projects/{self.PROJECT_NAME}/secrets/oauth2_providers/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def get_secret_storage(self):
        name = f"projects/{self.PROJECT_NAME}/secrets/video_storage/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
