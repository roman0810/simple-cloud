import hashlib
import hmac
import secrets

import psycopg
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.db import get_conn

router = APIRouter()

SESSION_DAYS = 7


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


#в БД хранится не сам пароль, а его хэш

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)  # случайная "соль": у одинаковых паролей разные хэши
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return salt.hex() + "$" + digest.hex()


def check_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 600_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


#Кто сейчас залогинен: браузер присылает cookie "session", ищем её в таблице sessions

def get_current_user(session: str | None = Cookie(default=None)) -> dict:
    if session is None:
        raise HTTPException(status_code=401, detail="not logged in")

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.username
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = %s
              AND sessions.created_at > now() - make_interval(days => %s)
            """,
            (session, SESSION_DAYS),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return {"id": row[0], "username": row[1]}


@router.post("/register", status_code=201)
def register(data: Credentials):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (data.username, hash_password(data.password)),
            )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="username already taken")
    return {"username": data.username}


@router.post("/login")
def login(data: Credentials, response: Response):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = %s", (data.username,)
        ).fetchone()

        if row is None or not check_password(data.password, row[1]):
            raise HTTPException(status_code=401, detail="wrong username or password")

        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (%s, %s)", (token, row[0]))

    response.set_cookie(
        "session", token, httponly=True, samesite="lax", max_age=SESSION_DAYS * 24 * 3600
    )
    return {"username": data.username}


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None)):
    if session is not None:
        with get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = %s", (session,))
    response.delete_cookie("session")
    return {"status": "ok"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"username": user["username"]}
