"""Create the MySQL database, apply ``schema.sql`` and load ``resume_data.py``.

    python seed.py              # create + seed (wipes existing resume rows)
    python seed.py --schema-only

It is safe to re-run: the database and tables are created with IF NOT EXISTS,
and the resume tables are rebuilt from scratch each time.
"""

from __future__ import annotations

import argparse
import os
import re

import mysql.connector

from db import connection_config, database_name, server_connection, validate_database_name

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema.sql")


def read_statements(path: str) -> list[str]:
    """Read a .sql file and split it into individual statements.

    Comments are stripped first so that semicolons inside them do not split a
    statement in half. The schema contains only plain DDL, so splitting on
    semicolons is safe.
    """
    with open(path, "r", encoding="utf-8") as handle:
        sql = handle.read()
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def create_database(name: str) -> None:
    safe_name = validate_database_name(name)
    conn = server_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{safe_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def apply_schema(name: str) -> None:
    safe_name = validate_database_name(name)
    conn = mysql.connector.connect(**connection_config(include_database=False))
    try:
        cur = conn.cursor()
        cur.execute(f"USE `{safe_name}`")
        for statement in read_statements(SCHEMA_PATH):
            cur.execute(statement)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def seed_resume() -> None:
    # Imported here so the connection pool is only built once the schema exists.
    from resume_data import RESUME
    from resume_store import replace_resume

    replace_resume(RESUME)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true", help="create tables but do not insert data")
    args = parser.parse_args()

    name = database_name()
    print(f"Creating database `{name}` if needed...")
    create_database(name)

    print("Applying schema.sql...")
    apply_schema(name)

    if args.schema_only:
        print("Done (schema only).")
        return

    from resume_data import RESUME

    print(f"Seeding resume for {RESUME['name']}...")
    seed_resume()
    print("Done. Start the app with: python app.py")


if __name__ == "__main__":
    main()
