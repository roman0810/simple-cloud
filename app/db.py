import os

import psycopg

# Адрес БД берём из переменной окружения. В docker-compose хост называется "db" (имя сервиса),
# а при запуске без Docker по умолчанию подключаемся к localhost.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cloudbox:cloudbox@localhost:5432/cloudbox")


def get_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL)


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет. Вызывается при старте приложения."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
