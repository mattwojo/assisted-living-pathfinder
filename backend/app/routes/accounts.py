"""Account sign-in and the labels used by the forms."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from agents.vocab import AMENITIES, CARE_LEVELS
from backend.app.db import LOCK, connect
from backend.app.security import (
    bearer,
    create_session,
    hash_password,
    now_iso,
    require_user,
    verify_password,
)

router = APIRouter()


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1] or " " in cleaned:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    return cleaned


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=8, max_length=200)
    role: str = "family"


class LoginIn(BaseModel):
    email: str
    password: str


@router.get("/meta")
def meta() -> dict:
    return {
        "care_levels": [{"id": key, "label": label} for key, label in CARE_LEVELS.items()],
        "amenities": AMENITIES,
        "demo_accounts": [
            {"role": "Family member", "email": "family@example.com", "password": "pathfinder"},
            {"role": "Community representative", "email": "rep@example.com", "password": "pathfinder"},
            {"role": "Reviewer", "email": "admin@example.com", "password": "pathfinder"},
        ],
        "sample_data_note": "The communities shipped with this app are fictional sample listings.",
    }


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn) -> dict:
    if body.role not in {"family", "representative"}:
        raise HTTPException(status_code=400, detail="Choose a family or representative account.")
    email = _email(body.email)
    with LOCK:
        connection = connect()
        try:
            exists = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                raise HTTPException(status_code=409, detail="An account with that email already exists.")
            cursor = connection.execute(
                """
                INSERT INTO users (email, name, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email, body.name.strip(), hash_password(body.password), body.role, now_iso()),
            )
            connection.commit()
            user_id = cursor.lastrowid
        finally:
            connection.close()
    token = create_session(user_id)
    return {
        "token": token,
        "user": {"id": user_id, "email": email, "name": body.name.strip(), "role": body.role},
    }


@router.post("/auth/login")
def login(body: LoginIn) -> dict:
    email = _email(body.email)
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, email, name, role, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        connection.close()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password does not match.")
    token = create_session(row["id"])
    return {
        "token": token,
        "user": {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]},
    }


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    user: dict = Depends(require_user),
) -> dict:
    del user
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    with LOCK:
        connection = connect()
        try:
            connection.execute("DELETE FROM sessions WHERE token = ?", (credentials.credentials,))
            connection.commit()
        finally:
            connection.close()
    return {"ok": True}


@router.get("/auth/me")
def me(user: dict = Depends(require_user)) -> dict:
    return {"user": user}
