"""Resume app backend.

The resume content lives in MySQL (see ``schema.sql``) and is served in the same
shape the templates always used. Public endpoints are read-only; anything that
writes requires the ``X-Admin-Token`` header (set ``ADMIN_TOKEN``).

Set up, in order:

    pip install -r requirements.txt
    python seed.py          # creates the database, applies schema, loads resume_data.py
    python app.py
"""

from __future__ import annotations

import os
import secrets
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, render_template, request

import resume_store as store
from db import ping

# Flask's default folder is "templates"; this project calls it "template".
app = Flask(__name__, template_folder="template")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _json_body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def _bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    return header[len(prefix):] if header.startswith(prefix) else ""


def require_admin(view):
    """Gate write endpoints behind ADMIN_TOKEN.

    If ADMIN_TOKEN is unset the endpoints stay open, which is convenient for
    local development — a warning is printed at startup.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not ADMIN_TOKEN:
            return view(*args, **kwargs)
        supplied = request.headers.get("X-Admin-Token") or _bearer_token()
        if not supplied or not secrets.compare_digest(supplied, ADMIN_TOKEN):
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapper


def _resume_response(status: int = 200):
    """Writes return the full refreshed resume so clients stay in sync."""
    return jsonify(store.load_resume()), status


def _item_response(collection: str, item_id: int, status: int = 200):
    data = store.load_resume()
    for item in data.get(collection, []):
        if item.get("id") == item_id:
            return jsonify(item), status
    return jsonify({"error": f"{collection[:-1]} {item_id} not found"}), 404


@app.errorhandler(mysql.connector.Error)
def handle_db_error(error: mysql.connector.Error):
    app.logger.error("database error: %s", error)
    return jsonify({"error": "database unavailable", "detail": str(error)}), 503


# --------------------------------------------------------------------------- #
# public reads
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    resume = store.load_resume()
    skills = sorted({s for item in resume["experience"] + resume["projects"] for s in item["skills"]})
    return render_template("index.html", r=resume, skills=skills)


@app.route("/api/resume")
def api_resume():
    return jsonify(store.load_resume())


@app.route("/api/skills")
def api_skills():
    return jsonify({"skills": store.list_skills()})


@app.route("/api/health")
def api_health():
    ping()
    return jsonify({"status": "ok", "database": os.getenv("DB_NAME", "resume")})


# --------------------------------------------------------------------------- #
# profile
# --------------------------------------------------------------------------- #
@app.route("/api/profile", methods=["PUT"])
@require_admin
def api_profile_update():
    store.save_profile(_json_body())
    return _resume_response()


# --------------------------------------------------------------------------- #
# experience
# --------------------------------------------------------------------------- #
@app.route("/api/experience", methods=["GET"])
def api_experience_list():
    return jsonify({"experience": store.load_resume()["experience"]})


@app.route("/api/experience", methods=["POST"])
@require_admin
def api_experience_create():
    if not _json_body():
        return jsonify({"error": "expected a JSON object"}), 400
    store.create_experience(_json_body())
    return _resume_response(201)


@app.route("/api/experience/<int:item_id>", methods=["GET"])
def api_experience_get(item_id: int):
    return _item_response("experience", item_id)


@app.route("/api/experience/<int:item_id>", methods=["PUT"])
@require_admin
def api_experience_update(item_id: int):
    if store.update_experience(item_id, _json_body()) is None:
        return jsonify({"error": f"experience {item_id} not found"}), 404
    return _resume_response()


@app.route("/api/experience/<int:item_id>", methods=["DELETE"])
@require_admin
def api_experience_delete(item_id: int):
    if not store.delete_experience(item_id):
        return jsonify({"error": f"experience {item_id} not found"}), 404
    return _resume_response()


# --------------------------------------------------------------------------- #
# projects
# --------------------------------------------------------------------------- #
@app.route("/api/projects", methods=["GET"])
def api_projects_list():
    return jsonify({"projects": store.load_resume()["projects"]})


@app.route("/api/projects", methods=["POST"])
@require_admin
def api_projects_create():
    if not _json_body():
        return jsonify({"error": "expected a JSON object"}), 400
    store.create_project(_json_body())
    return _resume_response(201)


@app.route("/api/projects/<int:item_id>", methods=["GET"])
def api_projects_get(item_id: int):
    return _item_response("projects", item_id)


@app.route("/api/projects/<int:item_id>", methods=["PUT"])
@require_admin
def api_projects_update(item_id: int):
    if store.update_project(item_id, _json_body()) is None:
        return jsonify({"error": f"project {item_id} not found"}), 404
    return _resume_response()


@app.route("/api/projects/<int:item_id>", methods=["DELETE"])
@require_admin
def api_projects_delete(item_id: int):
    if not store.delete_project(item_id):
        return jsonify({"error": f"project {item_id} not found"}), 404
    return _resume_response()


# --------------------------------------------------------------------------- #
# education
# --------------------------------------------------------------------------- #
@app.route("/api/education", methods=["GET"])
def api_education_list():
    return jsonify({"education": store.load_resume()["education"]})


@app.route("/api/education", methods=["POST"])
@require_admin
def api_education_create():
    if not _json_body():
        return jsonify({"error": "expected a JSON object"}), 400
    store.create_education(_json_body())
    return _resume_response(201)


@app.route("/api/education/<int:item_id>", methods=["GET"])
def api_education_get(item_id: int):
    return _item_response("education", item_id)


@app.route("/api/education/<int:item_id>", methods=["PUT"])
@require_admin
def api_education_update(item_id: int):
    if store.update_education(item_id, _json_body()) is None:
        return jsonify({"error": f"education {item_id} not found"}), 404
    return _resume_response()


@app.route("/api/education/<int:item_id>", methods=["DELETE"])
@require_admin
def api_education_delete(item_id: int):
    if not store.delete_education(item_id):
        return jsonify({"error": f"education {item_id} not found"}), 404
    return _resume_response()


# --------------------------------------------------------------------------- #
# contact
# --------------------------------------------------------------------------- #
@app.route("/api/contact", methods=["GET"])
def api_contact_list():
    return jsonify({"contact": store.load_resume()["contact"]})


@app.route("/api/contact", methods=["POST"])
@require_admin
def api_contact_create():
    if not _json_body():
        return jsonify({"error": "expected a JSON object"}), 400
    store.create_contact(_json_body())
    return _resume_response(201)


@app.route("/api/contact/<int:item_id>", methods=["GET"])
def api_contact_get(item_id: int):
    return _item_response("contact", item_id)


@app.route("/api/contact/<int:item_id>", methods=["PUT"])
@require_admin
def api_contact_update(item_id: int):
    if store.update_contact(item_id, _json_body()) is None:
        return jsonify({"error": f"contact {item_id} not found"}), 404
    return _resume_response()


@app.route("/api/contact/<int:item_id>", methods=["DELETE"])
@require_admin
def api_contact_delete(item_id: int):
    if not store.delete_contact(item_id):
        return jsonify({"error": f"contact {item_id} not found"}), 404
    return _resume_response()


# --------------------------------------------------------------------------- #
# bulk
# --------------------------------------------------------------------------- #
@app.route("/api/resume", methods=["PUT"])
@require_admin
def api_resume_replace():
    body = _json_body()
    if not body:
        return jsonify({"error": "expected a resume JSON object"}), 400
    store.replace_resume(body)
    return _resume_response()


if __name__ == "__main__":
    if not ADMIN_TOKEN:
        print("WARNING: ADMIN_TOKEN is not set - write endpoints are unprotected.")
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
