from pathlib import Path

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    return app.test_client()


def _login(client):
    return client.post(
        "/admin/login",
        data={"username": "admin", "password": "change-me"},
        follow_redirects=False,
    )


def test_admin_login_success(client):
    response = _login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")


def test_create_post_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    response = client.post("/api/posts", json={"title": "unauthorized"})
    assert response.status_code == 401


def test_create_post_success(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    _login(client)
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
    _login(client)
    (tmp_path / "same-slug.md").write_text("---\n---\n", encoding="utf-8")
    response = client.post("/api/posts", json={"title": "same slug"})
    assert response.status_code == 409


def test_update_post_success(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    _login(client)
    original = tmp_path / "my-post.md"
    original.write_text("---\ntitle: old\npublished: 2025-01-01\ntags: []\ndraft: false\n---\n", encoding="utf-8")

    response = client.put(
        "/api/posts/my-post",
        json={
            "slug": "my-post-updated",
            "title": "Updated Title",
            "description": "updated",
            "tags": "tag1,tag2",
            "category": "Test",
            "body": "updated body",
        },
    )
    assert response.status_code == 200
    assert not original.exists()
    updated = tmp_path / "my-post-updated.md"
    assert updated.exists()


def test_delete_post_success(client, tmp_path, monkeypatch):
    monkeypatch.setenv("POSTS_DIR", str(tmp_path))
    _login(client)
    target = tmp_path / "to-delete.md"
    target.write_text("---\n---\n", encoding="utf-8")

    response = client.delete("/api/posts/to-delete")
    assert response.status_code == 200
    assert not target.exists()
