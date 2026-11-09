"""Exercise routing, serialization, startup, pagination and middleware over ASGI."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

import api
from migrate import upgrade
from models import Race, DriverResult
from security import RateLimiter


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    upgrade(engine)
    Session = sessionmaker(bind=engine)
    def get_db():
        with Session() as db:
            yield db
    api.app.dependency_overrides[api.get_db] = get_db
    monkeypatch.setattr(api, "engine", engine)
    monkeypatch.setattr(api, "limiter", RateLimiter())
    with Session() as db:
        db.add_all([
            Race(race_id=1, name="GP1", date="2026-01-01", round=1, air_temp=float("inf")),
            Race(race_id=2, name="GP2", date="2026-01-08", round=2),
        ])
        db.commit()
        db.add(DriverResult(race_id=1, full_name="Driver", position=1, points=12.5))
        db.commit()
    try:
        with TestClient(api.app) as test_client:
            yield test_client
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()


def test_http_serialization_pagination_and_query_validation(client):
    response = client.get("/races?limit=1&offset=0")
    assert response.status_code == 200
    assert response.json()[0]["air_temp"] is None
    assert client.get("/races?limit=1&offset=1").json()[0]["race_id"] == 2
    assert client.get("/races?limit=501").status_code == 422
    assert client.get("/races?offset=-1").status_code == 422
    assert client.get("/races?offset=1000001").status_code == 422
    assert client.get("/races/9999999999999999999999/results").status_code == 422
    assert client.get("/races/1/laps?limit=10001").status_code == 422
    assert client.get("/championship?season=2026").json()[0]["points"] == 12.5
    assert client.get("/races/999/results").status_code == 404
    assert client.get("/health").json() == {"status": "ok"}


def test_cors_headers_and_rate_limit(client, monkeypatch):
    response = client.get("/races", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "public, max-age=60"
    assert "access-control-allow-origin" not in client.get("/races", headers={"Origin": "https://untrusted.example"}).headers
    monkeypatch.setattr(api, "limiter", RateLimiter(1))
    assert client.get("/races").status_code == 200
    response = client.get("/races", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 429 and response.headers["retry-after"] == "60"
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert client.get("/health").status_code == 200


def test_rate_limit_recovers_and_bounds_memory():
    now = [0]
    limiter = RateLimiter(1, max_clients=2, clock=lambda: now[0])
    assert limiter.allow("a") and not limiter.allow("a")
    now[0] = 60
    assert limiter.allow("a")
    assert limiter.allow("b") and limiter.allow("c")
    assert len(limiter.clients) == 2
