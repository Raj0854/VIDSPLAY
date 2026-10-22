import os
from pathlib import Path
import click
from flask import Flask, jsonify, render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

from config import config_by_name, BASE_DIR
from models import db, AdminUser, SiteSetting
from routes.api_auth import auth_bp
from routes.api_videos import videos_bp
from routes.api_categories import categories_bp
from routes.api_navigation import navigation_bp
from routes.api_pages import pages_bp
from routes.api_media import media_bp
from routes.api_dashboard import dashboard_bp
from routes.views import views_bp
from utils.schema_compat import upgrade_legacy_sqlite_schema

migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name=None):
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    config_class = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(config_class)

    # Ensure upload directory exists
    upload_path = Path(app.config["UPLOAD_FOLDER"])
    for sub in ["videos", "thumbnails", "banners", "general"]:
        (upload_path / sub).mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        with app.app_context():
            db.create_all()
            upgrade_legacy_sqlite_schema(db.engine)

    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "views.admin_login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(navigation_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(dashboard_bp)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    # CLI Command to create initial admin account
    @app.cli.command("create-admin")
    @click.option("--username", prompt="Admin username", default="admin", help="Admin username")
    @click.option("--email", prompt="Admin email", default="admin@vidsplay.com", help="Admin email")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
    def create_admin_cmd(username, email, password):
        """Create or update an administrative user account."""
        existing = AdminUser.query.filter((AdminUser.username == username) | (AdminUser.email == email)).first()
        if existing:
            click.echo(f"Updating password for existing user '{existing.username}'...")
            existing.set_password(password)
            existing.role = "admin"
            existing.is_active_account = True
        else:
            click.echo(f"Creating new admin user '{username}'...")
            new_user = AdminUser(
                username=username,
                email=email,
                role="admin",
                is_active_account=True,
            )
            new_user.set_password(password)
            db.session.add(new_user)

        db.session.commit()
        click.echo(click.style(f"Admin account '{username}' configured successfully!", fg="green"))

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=True)
