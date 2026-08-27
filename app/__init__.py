from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .services.text_formatting import render_inline_markup

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.jinja_env.filters["inline_markup"] = render_inline_markup

    return app


from . import models  # noqa: E402,F401
