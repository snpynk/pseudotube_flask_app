from flask_login import LoginManager

from flask_sqlalchemy import SQLAlchemy

from .oauth import OAuthProviderManager

from .gae import GAE

login_manager = LoginManager()

provider_manager = OAuthProviderManager()

db = SQLAlchemy()

gae = GAE()
