"""Read and write the resume held in MySQL.

Functions accept and return plain dicts shaped exactly like the original
``resume_data.RESUME`` constant, so the templates and the JSON API keep working
unchanged:

    {
      "name", "title", "location", "summary",
      "contact":    [{"label", "value", "href"}],
      "experience": [{"role", "org", "period", "points": [...], "skills": [...]}],
      "projects":   [{"name", "blurb", "skills": [...]}],
      "education":  [{"title", "org", "period"}],
    }

Write helpers return the created/updated id, or ``None`` when the row does not
exist. Callers re-read ``load_resume()`` to send a consistent snapshot back.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from db import read_cursor, transaction

# Columns written for each simple table, in order.
_EXPERIENCE_FIELDS = ("role", "org", "period")
_PROJECT_FIELDS = ("name", "blurb")
_EDUCATION_FIELDS = ("title", "org", "period")
_CONTACT_FIELDS = ("label", "value", "href")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    return "" if value is None else str(value).strip()


def _next_order(cur, table: str) -> int:
    cur.execute(f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM `{table}`")
    return cur.fetchone()["n"]


def _sync_skills(cur, names: Iterable[str]) -> list[int]:
    """Upsert skill names and return their ids, preserving input order."""
    ids: list[int] = []
    seen: set[str] = set()
    for raw in names or []:
        name = _text({"n": raw}, "n")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        # LAST_INSERT_ID(id) makes lastrowid the id of the *existing* row too.
        cur.execute(
            "INSERT INTO skills (name) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
            (name,),
        )
        ids.append(cur.lastrowid)
    return ids


def _set_links(cur, table: str, owner_column: str, owner_id: int, skill_ids: Sequence[int]) -> None:
    cur.execute(f"DELETE FROM `{table}` WHERE {owner_column} = %s", (owner_id,))
    if skill_ids:
        cur.executemany(
            f"INSERT IGNORE INTO `{table}` ({owner_column}, skill_id) VALUES (%s, %s)",
            [(owner_id, skill_id) for skill_id in skill_ids],
        )


def _group(cur, table: str, owner_column: str, ids: Sequence[int], column: str = "text") -> dict[int, list[str]]:
    """Collect ordered plain-text children (e.g. experience bullet points)."""
    if not ids:
        return {}
    cur.execute(
        f"SELECT {owner_column} AS owner_id, {column} AS val FROM `{table}` "
        f"WHERE {owner_column} IN ({_placeholders(len(ids))}) ORDER BY sort_order, id",
        list(ids),
    )
    grouped: dict[int, list[str]] = {}
    for row in cur.fetchall():
        grouped.setdefault(row["owner_id"], []).append(row["val"])
    return grouped


def _group_skills(cur, table: str, owner_column: str, ids: Sequence[int]) -> dict[int, list[str]]:
    if not ids:
        return {}
    cur.execute(
        f"SELECT t.{owner_column} AS owner_id, s.name AS val FROM `{table}` t "
        f"JOIN skills s ON s.id = t.skill_id "
        f"WHERE t.{owner_column} IN ({_placeholders(len(ids))}) ORDER BY t.id",
        list(ids),
    )
    grouped: dict[int, list[str]] = {}
    for row in cur.fetchall():
        grouped.setdefault(row["owner_id"], []).append(row["val"])
    return grouped


def _insert_simple(cur, table: str, fields: Sequence[str], data: dict[str, Any], order: int) -> int:
    columns = ", ".join(f"`{f}`" for f in fields) + ", sort_order"
    values = [_text(data, f) for f in fields] + [order]
    cur.execute(f"INSERT INTO `{table}` ({columns}) VALUES ({_placeholders(len(values))})", values)
    return cur.lastrowid


def _update_simple(cur, table: str, fields: Sequence[str], row_id: int, data: dict[str, Any]) -> int:
    assignments = ", ".join(f"`{f}` = %s" for f in fields)
    values = [_text(data, f) for f in fields] + [row_id]
    cur.execute(f"UPDATE `{table}` SET {assignments} WHERE id = %s", values)
    return cur.rowcount


def _delete_simple(cur, table: str, row_id: int) -> bool:
    cur.execute(f"DELETE FROM `{table}` WHERE id = %s", (row_id,))
    return cur.rowcount > 0


def _replace_points(cur, experience_id: int, points: Sequence[str]) -> None:
    cur.execute("DELETE FROM experience_points WHERE experience_id = %s", (experience_id,))
    rows = [(_text({"p": p}, "p"), experience_id, i) for i, p in enumerate(points) if _text({"p": p}, "p")]
    if rows:
        cur.executemany(
            "INSERT INTO experience_points (text, experience_id, sort_order) VALUES (%s, %s, %s)",
            rows,
        )


def _insert_experience(cur, data: dict[str, Any], order: int) -> int:
    experience_id = _insert_simple(cur, "experience", _EXPERIENCE_FIELDS, data, order)
    _replace_points(cur, experience_id, data.get("points", []))
    _set_links(cur, "experience_skills", "experience_id", experience_id,
               _sync_skills(cur, data.get("skills", [])))
    return experience_id


def _insert_project(cur, data: dict[str, Any], order: int) -> int:
    project_id = _insert_simple(cur, "projects", _PROJECT_FIELDS, data, order)
    _set_links(cur, "project_skills", "project_id", project_id,
               _sync_skills(cur, data.get("skills", [])))
    return project_id


# --------------------------------------------------------------------------- #
# reads
# --------------------------------------------------------------------------- #
def load_resume() -> dict[str, Any]:
    """Return the whole resume as a single nested dict."""
    with read_cursor() as cur:
        cur.execute("SELECT name, title, location, summary FROM profile ORDER BY id LIMIT 1")
        profile = cur.fetchone() or {"name": "", "title": "", "location": "", "summary": ""}

        cur.execute("SELECT id, label, value, href FROM contact ORDER BY sort_order, id")
        contact = cur.fetchall()

        cur.execute("SELECT id, role, org, period FROM experience ORDER BY sort_order, id")
        experience = cur.fetchall()
        experience_ids = [row["id"] for row in experience]
        points = _group(cur, "experience_points", "experience_id", experience_ids)
        experience_skills = _group_skills(cur, "experience_skills", "experience_id", experience_ids)

        cur.execute("SELECT id, name, blurb FROM projects ORDER BY sort_order, id")
        projects = cur.fetchall()
        project_skills = _group_skills(cur, "project_skills", "project_id", [row["id"] for row in projects])

        cur.execute("SELECT id, title, org, period FROM education ORDER BY sort_order, id")
        education = cur.fetchall()

    return {
        "name": profile["name"],
        "title": profile["title"],
        "location": profile["location"],
        "summary": profile["summary"],
        "contact": [
            {"id": row["id"], "label": row["label"], "value": row["value"], "href": row["href"]}
            for row in contact
        ],
        "experience": [
            {
                "id": row["id"],
                "role": row["role"],
                "org": row["org"],
                "period": row["period"],
                "points": points.get(row["id"], []),
                "skills": experience_skills.get(row["id"], []),
            }
            for row in experience
        ],
        "projects": [
            {
                "id": row["id"],
                "name": row["name"],
                "blurb": row["blurb"],
                "skills": project_skills.get(row["id"], []),
            }
            for row in projects
        ],
        "education": [
            {"id": row["id"], "title": row["title"], "org": row["org"], "period": row["period"]}
            for row in education
        ],
    }


def list_skills() -> list[str]:
    with read_cursor() as cur:
        cur.execute("SELECT name FROM skills ORDER BY name")
        return [row["name"] for row in cur.fetchall()]


# --------------------------------------------------------------------------- #
# profile
# --------------------------------------------------------------------------- #
def save_profile(data: dict[str, Any]) -> dict[str, Any]:
    """Update the single profile row, inserting one if the table is empty."""
    values = (_text(data, "name"), _text(data, "title"), _text(data, "location"), _text(data, "summary"))
    with transaction() as cur:
        cur.execute("SELECT id FROM profile ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE profile SET name = %s, title = %s, location = %s, summary = %s WHERE id = %s",
                (*values, row["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO profile (name, title, location, summary) VALUES (%s, %s, %s, %s)", values
            )
    return {"name": values[0], "title": values[1], "location": values[2], "summary": values[3]}


# --------------------------------------------------------------------------- #
# experience
# --------------------------------------------------------------------------- #
def create_experience(data: dict[str, Any]) -> int:
    with transaction() as cur:
        return _insert_experience(cur, data, _next_order(cur, "experience"))


def update_experience(experience_id: int, data: dict[str, Any]) -> int | None:
    with transaction() as cur:
        if not _update_simple(cur, "experience", _EXPERIENCE_FIELDS, experience_id, data):
            cur.execute("SELECT id FROM experience WHERE id = %s", (experience_id,))
            if not cur.fetchone():
                return None
        _replace_points(cur, experience_id, data.get("points", []))
        _set_links(cur, "experience_skills", "experience_id", experience_id,
                   _sync_skills(cur, data.get("skills", [])))
    return experience_id


def delete_experience(experience_id: int) -> bool:
    with transaction() as cur:
        return _delete_simple(cur, "experience", experience_id)


# --------------------------------------------------------------------------- #
# projects
# --------------------------------------------------------------------------- #
def create_project(data: dict[str, Any]) -> int:
    with transaction() as cur:
        return _insert_project(cur, data, _next_order(cur, "projects"))


def update_project(project_id: int, data: dict[str, Any]) -> int | None:
    with transaction() as cur:
        if not _update_simple(cur, "projects", _PROJECT_FIELDS, project_id, data):
            cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
            if not cur.fetchone():
                return None
        _set_links(cur, "project_skills", "project_id", project_id,
                   _sync_skills(cur, data.get("skills", [])))
    return project_id


def delete_project(project_id: int) -> bool:
    with transaction() as cur:
        return _delete_simple(cur, "projects", project_id)


# --------------------------------------------------------------------------- #
# education
# --------------------------------------------------------------------------- #
def create_education(data: dict[str, Any]) -> int:
    with transaction() as cur:
        return _insert_simple(cur, "education", _EDUCATION_FIELDS, data, _next_order(cur, "education"))


def update_education(education_id: int, data: dict[str, Any]) -> int | None:
    with transaction() as cur:
        if not _update_simple(cur, "education", _EDUCATION_FIELDS, education_id, data):
            cur.execute("SELECT id FROM education WHERE id = %s", (education_id,))
            if not cur.fetchone():
                return None
    return education_id


def delete_education(education_id: int) -> bool:
    with transaction() as cur:
        return _delete_simple(cur, "education", education_id)


# --------------------------------------------------------------------------- #
# contact
# --------------------------------------------------------------------------- #
def create_contact(data: dict[str, Any]) -> int:
    with transaction() as cur:
        return _insert_simple(cur, "contact", _CONTACT_FIELDS, data, _next_order(cur, "contact"))


def update_contact(contact_id: int, data: dict[str, Any]) -> int | None:
    with transaction() as cur:
        if not _update_simple(cur, "contact", _CONTACT_FIELDS, contact_id, data):
            cur.execute("SELECT id FROM contact WHERE id = %s", (contact_id,))
            if not cur.fetchone():
                return None
    return contact_id


def delete_contact(contact_id: int) -> bool:
    with transaction() as cur:
        return _delete_simple(cur, "contact", contact_id)


# --------------------------------------------------------------------------- #
# bulk replace (used by the seed script and PUT /api/resume)
# --------------------------------------------------------------------------- #
def replace_resume(data: dict[str, Any]) -> None:
    """Wipe every table and rebuild the resume from ``data`` in one transaction."""
    with transaction() as cur:
        # Children are removed by ON DELETE CASCADE.
        for table in ("experience", "projects", "education", "contact", "profile", "skills"):
            cur.execute(f"DELETE FROM `{table}`")

        save_profile_row = (
            _text(data, "name"), _text(data, "title"), _text(data, "location"), _text(data, "summary")
        )
        cur.execute(
            "INSERT INTO profile (name, title, location, summary) VALUES (%s, %s, %s, %s)",
            save_profile_row,
        )

        for order, item in enumerate(data.get("contact", [])):
            _insert_simple(cur, "contact", _CONTACT_FIELDS, item, order)

        for order, item in enumerate(data.get("experience", [])):
            _insert_experience(cur, item, order)

        for order, item in enumerate(data.get("projects", [])):
            _insert_project(cur, item, order)

        for order, item in enumerate(data.get("education", [])):
            _insert_simple(cur, "education", _EDUCATION_FIELDS, item, order)
