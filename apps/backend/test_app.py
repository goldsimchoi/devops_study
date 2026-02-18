from pathlib import Path

import pytest
from app import app


@pytest.fixture
def client():
    return app.test_client()


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Backend API server"


def test_create_post_success(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    response = client.post(
        "/api/posts",
        json={
            "title": "My First Post",
            "description": "quick note",
            "tags": ["DevOps", "Docker"],
            "category": "Diary",
            "body": "# Hello",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["slug"] == "my-first-post"

    created = Path(data["path"])
    assert created.exists()
    text = created.read_text(encoding="utf-8")
    assert "title: My First Post" in text
    assert "tags: [DevOps, Docker]" in text
    assert "# Hello" in text


def test_create_post_duplicate_returns_409(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    (tmp_path / "same-slug.md").write_text("---\n---\n", encoding="utf-8")
    response = client.post("/api/posts", json={"title": "same slug"})
    assert response.status_code == 409
