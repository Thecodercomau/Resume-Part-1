"""MySQL connection handling for the resume backend.

Configuration is read from the environment so the same code works in dev and
production:

    DB_HOST      default 127.0.0.1
    DB_PORT      default 3306
    DB_USER      default root
    DB_PASSWORD  default "" (empty)
    DB_NAME      default resume
    DB_POOL_SIZE default 5

Everything goes through ``mysql-connector-python``. Two helpers cover almost
all call sites:

    with read_cursor() as cur:      # SELECTs
        ...

    with transaction() as cur:      # INSERT/UPDATE/DELETE, commits on exit
        ...
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from mysql.connector import pooling

# Optional: load a local .env so DB_* settings can live outside the shell.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:  # python-dotenv is optional
    pass

_pool: pooling.MySQLConnectionPool | None = None


def connection_config(include_database: bool = True) -> dict[str, Any]:
    """Build a mysql-connector connection config from the environment.

    ``include_database=False`` is used by the setup script, which has to connect
    to the server *before* the application database exists.
    """
    config: dict[str, Any] = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "autocommit": False,
        "use_pure": True,
        "charset": "utf8mb4",
        "ssl_disabled": os.getenv("DB_SSL_DISABLED", "1") == "1",
    }
    if include_database:
        config["database"] = os.getenv("DB_NAME", "resume")
    return config


def database_name() -> str:
    return os.getenv("DB_NAME", "resume")


def validate_database_name(name: str) -> str:
    """Guard the one value we interpolate into DDL."""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Invalid DB_NAME {name!r}: use letters, digits and underscores only")
    return name


def get_pool() -> pooling.MySQLConnectionPool:
    """Lazily create the shared connection pool."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="resume_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **connection_config(),
        )
    return _pool


def server_connection():
    """A direct connection with no database selected (used by setup scripts)."""
    return mysql.connector.connect(**connection_config(include_database=False))


@contextmanager
def read_cursor(dictionary: bool = True) -> Iterator[mysql.connector.cursor.MySQLCursor]:
    """Yield a cursor for SELECTs, always returning the connection to the pool."""
    conn = get_pool().get_connection()
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield cur
    finally:
        cur.close()
        conn.close()


@contextmanager
def transaction(dictionary: bool = True) -> Iterator[mysql.connector.cursor.MySQLCursor]:
    """Yield a cursor inside a transaction, committing on success and rolling
    back if anything raises."""
    conn = get_pool().get_connection()
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def ping() -> None:
    """Raise if the database is unreachable."""
    with read_cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
