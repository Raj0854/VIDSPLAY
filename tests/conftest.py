import io
import pytest
from app import create_app, db
from models import AdminUser, Category, Video, NavigationItem, Page, PageSection, SiteSetting


@pytest.fixture
def app():
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed test admin user
        admin = AdminUser(
            username="testadmin",
            email="testadmin@vidsplay.com",
            role="admin",
            is_active_account=True,
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # Seed test category
        cat = Category(name="Action", slug="action", icon="bi-film", display_order=0, is_active=True)
        db.session.add(cat)

        db.session.commit()

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Client with authenticated admin session."""
    c = app.test_client()
    c.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123"
    })
    return c
