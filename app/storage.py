from datetime import timedelta
from json import loads
from typing import Literal, Optional
from uuid import uuid4

from flask import jsonify
from google.auth.credentials import Credentials
from google.cloud import storage
from google.oauth2 import service_account


class StorageManager:
    ALLOWED_VIDEO_MIME_TYPES = [
        "video/mp4",
        "video/webm",
        "video/ogg",
        "video/x-matroska",  # mkv
        "video/quicktime",  # mov
    ]

    def __init__(
        self,
        bucket_name: str,
        credentials_json: str,
        storage_type: Literal["gs"] = "gs",
    ):
        self.bucket_name = bucket_name
        self.credentials: Optional[Credentials] = None
        self.credentials_json = credentials_json
        self.client: Optional[storage.Client] = None
        self.bucket: Optional[storage.Bucket] = None

        if storage_type == "gs":
            self._setup_google_storage()

    def _setup_google_storage(self) -> None:
        try:
            self.credentials = service_account.Credentials.from_service_account_info(
                loads(self.credentials_json)
            )
            self.client = storage.Client(credentials=self.credentials)
            self.bucket = self.client.bucket(self.bucket_name)

        except Exception as e:
            raise ValueError(f"Failed to initialize Google Cloud Storage client: {e}")

    # def upload_video(self, file_path: str, file_name: str) -> str:
    #     if not self.bucket:
    #         raise ValueError("Google Cloud Storage bucket is not initialized.")
    #
    #     try:
    #         blob = self.bucket.blob(file_name)
    #         blob.upload_from_filename(file_path)
    #
    #         return f"https://storage.googleapis.com/{self.bucket_name}/{file_name}"
    #     except Exception as e:
    #         raise RuntimeError(f"Failed to upload video: {e}")
    #
    def upload_thumbnail(self, file_bytes: bytes, file_name: str) -> str:
        if not self.bucket:
            raise ValueError("Google Cloud Storage bucket is not initialized.")

        try:
            blob = self.bucket.blob(file_name)
            # make sure CORS is not a problem
            blob.upload_from_string(file_bytes, content_type="image/jpeg")

            return f"https://storage.googleapis.com/{self.bucket_name}/{file_name}"
        except Exception as e:
            raise RuntimeError(f"Failed to upload thumbnail: {e}")

    def generate_upload_url(
        self,
        file_name: str,
        expires_in_minutes: int = 5,
    ) -> str:
        if not self.bucket:
            raise ValueError("Google Cloud Storage bucket is not initialized.")

        try:
            blob = self.bucket.blob(file_name)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expires_in_minutes),
                # content_type="video/mp4",
                method="PUT",
            )

            return url
        except Exception as e:
            raise RuntimeError(f"Failed to generate signed upload URL: {e}")

    def path_exists(self, path: str) -> bool:
        if not self.bucket:
            raise ValueError("Google Cloud Storage bucket is not initialized.")

        try:
            blob = self.bucket.blob(path)
            return blob.exists()
        except Exception as e:
            raise RuntimeError(f"Failed to check if path exists: {e}")

    def get_public_url(self, path: str) -> str:
        if not self.bucket:
            raise RuntimeError("Google Cloud Storage bucket is not initialized.")

        try:
            blob = self.bucket.blob(path)
            if not blob.exists():
                raise ValueError(f"Path {path} does not exist in the bucket.")

            return f"https://storage.googleapis.com/{self.bucket_name}/{path}"
        except Exception as e:
            raise RuntimeError(f"Failed to get public URL: {e}")
