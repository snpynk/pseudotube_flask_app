from flask_login import LoginManager

from flask_sqlalchemy import SQLAlchemy

from .oauth import OAuthProviderManager

from .gae import GAE

login_manager = LoginManager()

login_manager = LoginManager()

db = SQLAlchemy()

gae = GAE()

provider_manager = OAuthProviderManager(gae.OAUTH2_PROVIDERS)
