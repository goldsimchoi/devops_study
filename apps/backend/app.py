import os
import re
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

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


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or f"post-{date.today().isoformat()}"


def _build_markdown(data: dict) -> str:
    title = data["title"].strip()
    description = data.get("description", "").strip()
    tags = data.get("tags", [])
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


@app.route("/api/health")
def health():
    return jsonify({"ok": True}), 200


@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    slug = _slugify(data.get("slug", title))
    posts_dir = _posts_dir()
    posts_dir.mkdir(parents=True, exist_ok=True)
    target = posts_dir / f"{slug}.md"

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
