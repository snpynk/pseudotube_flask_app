from json import loads
from typing import Optional, Literal

from google.oauth2 import service_account
from google.auth.credentials import Credentials
from cloudpathlib import GSClient


class StorageManager:
    def __init__(
        self,
        bucket_name: str,
        credentials_json: str,
        storage_type: Literal["gs"] = "gs",
    ):
        self.bucket_name = bucket_name

        self.client: Optional[GSClient] = None
        self.credentials: Optional[Credentials] = None
        self.credentials_json = credentials_json

        if storage_type == "gs":
            self._setup_google_storage()

    def _setup_google_storage(self) -> None:
        try:
            self.credentials = service_account.Credentials.from_service_account_info(
                loads(self.credentials_json)
            )
        except Exception as e:
            raise ValueError(f"Invalid Google Cloud credentials: {e}")

        self.client = GSClient(credentials=self.credentials)

    def upload_video(self, file_path: str, file_name: str) -> str:
        if not isinstance(self.client, GSClient):
            raise ValueError("Google Cloud Storage client is not initialized.")

        try:
            path = self.client.CloudPath(f"gs://{self.bucket_name}/{file_name}")
            path.upload_from(file_path)

            return str(
                "https://storage.googleapis.com/" + path.as_uri().replace("gs://", "")
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upload video: {e}")

    def upload_thumbnail(self, file_bytes: bytes, file_name: str) -> str:
        if not isinstance(self.client, GSClient):
            raise ValueError("Google Cloud Storage client is not initialized.")

        try:
            path = self.client.CloudPath(f"gs://{self.bucket_name}/{file_name}")
            path.write_bytes(file_bytes)
            return str(
                "https://storage.googleapis.com/" + path.as_uri().replace("gs://", "")
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upload thumbnail: {e}")
