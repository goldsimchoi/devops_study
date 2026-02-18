import os
import re
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

DEFAULT_POSTS_DIR = (
    Path(__file__).resolve().parents[1]
    / "frontend"
    / "blog_bm0p"
    / "src"
    / "content"
    / "posts"
)


def _posts_dir() -> Path:
    return Path(os.getenv("POSTS_DIR", str(DEFAULT_POSTS_DIR)))


def _admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "admin")


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "change-me")


def _is_logged_in() -> bool:
    return session.get("is_admin") is True


def _login_required_api(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_logged_in():
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


def _login_required_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_logged_in():
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)

    return wrapper


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or f"post-{date.today().isoformat()}"


def _normalize_tags(raw_tags) -> list[str]:
    if isinstance(raw_tags, list):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if isinstance(raw_tags, str):
        return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    return []


def _post_file(slug: str) -> Path:
    return _posts_dir() / f"{_slugify(slug)}.md"


def _list_post_slugs() -> list[str]:
    posts_dir = _posts_dir()
    if not posts_dir.exists():
        return []
    return sorted([p.stem for p in posts_dir.glob("*.md")])


def _build_markdown(data: dict) -> str:
    title = data["title"].strip()
    description = data.get("description", "").strip()
    tags = _normalize_tags(data.get("tags", []))
    category = data.get("category", "").strip()
    draft = bool(data.get("draft", False))
    published = data.get("published", date.today().isoformat())
    body = data.get("body", "").rstrip()

    tags_str = ", ".join(tags)
    lines = [
        "---",
        f"title: {title}",
        f"published: {published}",
    ]
    if description:
        lines.append(f"description: {description}")
    lines.append(f"tags: [{tags_str}]")
    if category:
        lines.append(f"category: {category}")
    lines.append(f"draft: {'true' if draft else 'false'}")
    lines.extend(["---", "", body, ""])
    return "\n".join(lines)


@app.route("/")
def root():
    return jsonify({"message": "Backend API server", "health": "/api/health"}), 200


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == _admin_username() and password == _admin_password():
            session["is_admin"] = True
            return redirect(url_for("admin_page"))
        error = "Invalid credentials"

    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Admin Login</title>
      <style>
        body { font-family: Arial, sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }
        label { display: block; margin-top: 12px; font-weight: 600; }
        input { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; }
        button { margin-top: 16px; padding: 10px 14px; cursor: pointer; }
        .error { color: #b00020; margin-top: 12px; }
      </style>
    </head>
    <body>
      <h1>Admin Login</h1>
      <form method="post" action="/admin/login">
        <label for="username">Username</label>
        <input id="username" name="username" required />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" required />
        <button type="submit">Sign in</button>
      </form>
      {% if error %}<p class="error">{{ error }}</p>{% endif %}
    </body>
    </html>
    """
    return render_template_string(html, error=error)


@app.route("/admin/logout", methods=["POST"])
@_login_required_admin
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@_login_required_admin
def admin_page():
    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Blog Admin</title>
      <style>
        body { font-family: Arial, sans-serif; max-width: 860px; margin: 20px auto; padding: 0 16px; }
        textarea, input { width: 100%; box-sizing: border-box; margin: 6px 0 10px; padding: 8px; }
        textarea { min-height: 160px; }
        button { padding: 8px 12px; margin-right: 8px; cursor: pointer; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
      </style>
    </head>
    <body>
      <h1>Blog Admin</h1>
      <form method="post" action="/admin/logout"><button type="submit">Logout</button></form>
      <div class="grid">
        <div class="card">
          <h2>Create / Update</h2>
          <input id="slug" placeholder="slug (optional for create)" />
          <input id="title" placeholder="title (required)" />
          <input id="description" placeholder="description" />
          <input id="tags" placeholder="tags,comma,separated" />
          <input id="category" placeholder="category" />
          <input id="published" placeholder="published YYYY-MM-DD (optional)" />
          <label><input id="draft" type="checkbox" /> draft</label>
          <textarea id="body" placeholder="markdown body"></textarea>
          <button type="button" onclick="createPost()">Create</button>
          <button type="button" onclick="updatePost()">Update</button>
        </div>
        <div class="card">
          <h2>Delete</h2>
          <input id="deleteSlug" placeholder="slug to delete" />
          <button type="button" onclick="deletePost()">Delete</button>
          <h2>Existing Posts</h2>
          <ul>
            {% for slug in slugs %}
              <li>{{ slug }}</li>
            {% endfor %}
          </ul>
        </div>
      </div>
      <p id="result"></p>
      <script>
        function payload() {
          return {
            slug: document.getElementById('slug').value,
            title: document.getElementById('title').value,
            description: document.getElementById('description').value,
            tags: document.getElementById('tags').value,
            category: document.getElementById('category').value,
            published: document.getElementById('published').value,
            draft: document.getElementById('draft').checked,
            body: document.getElementById('body').value
          };
        }
        async function createPost() {
          const res = await fetch('/api/posts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload())
          });
          document.getElementById('result').innerText = JSON.stringify(await res.json());
        }
        async function updatePost() {
          const slug = document.getElementById('slug').value;
          if (!slug) { alert('slug required for update'); return; }
          const res = await fetch('/api/posts/' + encodeURIComponent(slug), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload())
          });
          document.getElementById('result').innerText = JSON.stringify(await res.json());
        }
        async function deletePost() {
          const slug = document.getElementById('deleteSlug').value;
          if (!slug) { alert('slug required for delete'); return; }
          const res = await fetch('/api/posts/' + encodeURIComponent(slug), { method: 'DELETE' });
          document.getElementById('result').innerText = JSON.stringify(await res.json());
        }
      </script>
    </body>
    </html>
    """
    return render_template_string(html, slugs=_list_post_slugs())


@app.route("/api/health")
def health():
    return jsonify({"ok": True}), 200


@app.route("/api/posts", methods=["POST"])
@_login_required_api
def create_post():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    slug = _slugify(data.get("slug", title))
    posts_dir = _posts_dir()
    posts_dir.mkdir(parents=True, exist_ok=True)
    target = _post_file(slug)

    if target.exists():
        return jsonify({"error": "post already exists", "slug": slug}), 409

    markdown = _build_markdown(data)
    target.write_text(markdown, encoding="utf-8")

    return (
        jsonify(
            {
                "message": "post created",
                "slug": slug,
                "path": str(target),
            }
        ),
        201,
    )


@app.route("/api/posts/<slug>", methods=["PUT"])
@_login_required_api
def update_post(slug: str):
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    current = _post_file(slug)
    if not current.exists():
        return jsonify({"error": "post not found", "slug": _slugify(slug)}), 404

    next_slug = _slugify(data.get("slug", slug))
    next_target = _post_file(next_slug)
    if next_target != current and next_target.exists():
        return jsonify({"error": "target slug already exists", "slug": next_slug}), 409

    markdown = _build_markdown(data)
    if next_target != current:
        current.unlink()
    next_target.write_text(markdown, encoding="utf-8")

    return jsonify({"message": "post updated", "slug": next_slug, "path": str(next_target)}), 200


@app.route("/api/posts/<slug>", methods=["DELETE"])
@_login_required_api
def delete_post(slug: str):
    target = _post_file(slug)
    if not target.exists():
        return jsonify({"error": "post not found", "slug": _slugify(slug)}), 404
    target.unlink()
    return jsonify({"message": "post deleted", "slug": _slugify(slug)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
