import os
from json import dumps

from google.cloud import secretmanager


class GAE:
    def __init__(self):
        if "IS_GAE" in os.environ:
            self.client = secretmanager.SecretManagerServiceClient()

    def setup(self):
        if hasattr(self, "client"):
            os.environ["PSEUDOTUBE_OAUTH2_PROVIDERS"] = dumps(
                [self.get_oauth2_providers()]
            )

    def get_oauth2_providers(self):
        name = "projects/pseudotube/secrets/oauth2_providers/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
