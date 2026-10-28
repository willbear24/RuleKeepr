from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.database as database
import backend.app.main as main
import backend.app.routers.auth as auth_router
from backend.app.database import Base, get_db
from backend.app.limiter import limiter
from backend.app.main import app
from backend.app.models.game import Game

TestSession = sessionmaker(autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession.configure(bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(auth_router, "send_email", lambda *_args, **_kwargs: None)

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    rate_limiting_enabled = limiter.enabled
    limiter.enabled = False
    try:
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        limiter.enabled = rate_limiting_enabled
        TestSession.configure(bind=None)
        engine.dispose()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    email = f"test-{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "test-password-123",
        },
    )

    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def sample_game():
    """Create and return a sample catalog game for tests that need existing data."""
    db = TestSession()
    game = Game(
        title="Monopoly",
        min_player=2,
        max_player=6,
        play_time_minutes="60-180",
        rules_filename="monopoly.txt",
    )
    try:
        db.add(game)
        db.commit()
        db.refresh(game)
        return {
            "id": game.id,
            "title": game.title,
            "min_player": game.min_player,
            "max_player": game.max_player,
            "play_time_minutes": game.play_time_minutes,
        }
    finally:
        db.close()
