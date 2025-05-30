from flask_login import LoginManager

from flask_sqlalchemy import SQLAlchemy

from .oauth import OAuthProviderManager

from .gae import GAE

from .storage import StorageManager

login_manager = LoginManager()

db = SQLAlchemy()

gae = GAE()

provider_manager = OAuthProviderManager(gae.OAUTH2_PROVIDERS)

storage_manager = StorageManager(gae.GCP_BUCKET_NAME, gae.GCP_BUCKET_CREDENTIALS)
