from flask_login import LoginManager

from flask_sqlalchemy import SQLAlchemy

from app.transcoder import TranscoderService

from .oauth import OAuthProviderManager

from .gae import GAE

from .storage import StorageManager

login_manager = LoginManager()

db = SQLAlchemy()

gae = GAE()

provider_manager = OAuthProviderManager(gae.OAUTH2_PROVIDERS)

storage_manager = StorageManager(gae.GCP_BUCKET_NAME, gae.GCP_BUCKET_CREDENTIALS)

transcoder_service = TranscoderService(
    gae.GCP_TRANSCODER_CREDENTIALS,
    gae.GCP_PROJECT_NAME,
    gae.GCP_LOCATION,
    gae.GCP_PUBSUB_UPLOAD_QUEUE_TOPIC,
)
