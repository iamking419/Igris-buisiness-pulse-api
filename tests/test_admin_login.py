import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import hash_password
from database import Base, get_db
from main import app
from models import AdminUser
from schemas import AdminLoginRequest


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    db.add(AdminUser(username="admin", password_hash=hash_password("correct-password")))
    db.commit()
    db.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_admin_login_request_requires_password_only():
    payload = AdminLoginRequest.model_validate({"password": "correct-password"})
    assert payload.model_dump() == {"password": "correct-password"}

    with pytest.raises(ValidationError):
        AdminLoginRequest.model_validate({"password": "correct-password", "username": "admin"})


def test_admin_login_endpoint_returns_invalid_credentials_for_bad_password(client):
    response = client.post("/api/v1/admin/login", json={"password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_admin_login_endpoint_accepts_password_only_and_returns_token(client):
    response = client.post("/api/v1/admin/login", json={"password": "correct-password"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]
