# Resume app backend

Flask + MySQL (via `mysql-connector-python`). The resume content lives in
normalized MySQL tables instead of the hardcoded dict that used to be served
straight from `resume_data.py`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then edit your MySQL credentials
python seed.py              # creates the database, applies schema.sql, loads resume_data.py
python app.py               # http://localhost:5000
```

`resume_data.py` is still the source of the initial content — `seed.py` reads it
and inserts it. After that, edit the resume through the API (or MySQL) and
`resume_data.py` is no longer read by the running app.

## Files

| File | Purpose |
| --- | --- |
| `db.py` | Connection pool, `read_cursor()` / `transaction()` context managers, env config |
| `schema.sql` | Normalized table definitions |
| `resume_store.py` | Read + CRUD layer; returns dicts shaped like the old `RESUME` |
| `seed.py` | Creates the database, applies the schema, loads `resume_data.py` |
| `app.py` | Flask routes (public reads, admin writes) |
| `template/index.html` | Existing template, unchanged — `app.py` points Flask at the `template/` folder |

## Schema

`profile` (single row) · `contact` · `experience` + `experience_points` ·
`projects` · `education` · `skills`, with `experience_skills` and
`project_skills` join tables. Skills are shared between experience entries and
projects, so a skill only exists once in `skills`.

## API

Public (read-only):

| Method | Path | Returns |
| --- | --- | --- |
| `GET` | `/` | Rendered resume page |
| `GET` | `/api/resume` | The whole resume as nested JSON |
| `GET` | `/api/skills` | All skill names |
| `GET` | `/api/health` | DB connectivity check |
| `GET` | `/api/experience`, `/api/projects`, `/api/education`, `/api/contact` | One collection each |
| `GET` | `/api/<collection>/<id>` | A single item |

Admin (writes). Send `X-Admin-Token: <ADMIN_TOKEN>` (or `Authorization: Bearer <token>`):

| Method | Path | Body |
| --- | --- | --- |
| `PUT` | `/api/profile` | `{"name", "title", "location", "summary"}` |
| `POST` | `/api/experience` | `{"role", "org", "period", "points": [...], "skills": [...]}` |
| `PUT`/`DELETE` | `/api/experience/<id>` | Same shape as `POST` |
| `POST` | `/api/projects` | `{"name", "blurb", "skills": [...]}` |
| `PUT`/`DELETE` | `/api/projects/<id>` | Same shape as `POST` |
| `POST` | `/api/education` | `{"title", "org", "period"}` |
| `PUT`/`DELETE` | `/api/education/<id>` | Same shape as `POST` |
| `POST` | `/api/contact` | `{"label", "value", "href"}` |
| `PUT`/`DELETE` | `/api/contact/<id>` | Same shape as `POST` |
| `PUT` | `/api/resume` | Full resume document — replaces everything |

Write responses return the full refreshed resume (HTTP 201 for creates), so the
client always has the current state including new row ids.

If `ADMIN_TOKEN` is unset, write endpoints are left open and a warning is
printed at startup. **Always set `ADMIN_TOKEN` in production.**

## Example

```bash
curl -X POST http://localhost:5000/api/experience \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: change-me' \
  -d '{"role":"Developer","org":"Acme","period":"2020 – 2021",
       "points":["Built the thing."],"skills":["Python","MySQL"]}'
```
