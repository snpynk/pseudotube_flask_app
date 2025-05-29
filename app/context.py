from flask_login import LoginManager

from flask_sqlalchemy import SQLAlchemy

from .oauth import OAuthProviderManager

login_manager = LoginManager()

provider_manager = OAuthProviderManager()

db = SQLAlchemy()
