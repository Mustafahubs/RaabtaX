"""
Async data layer — PostgreSQL (asyncpg) + Redis.

Connection pools are module-level infrastructure globals.
Per-user state is NEVER stored here; it belongs in page.session.store.

Defaults target a local dev stack:
  PG:    postgresql://postgres:postgres@localhost:5433/raabtax
  Redis: redis://localhost:6379

Override via environment variables:
  RAABTAX_PG_DSN    — full asyncpg DSN
  RAABTAX_REDIS_URL — redis:// URL
"""
import json
import os
import secrets
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import asyncpg
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

# ── Pool references ──────────────────────────────────────────────────────── #

_pg: asyncpg.Pool | None = None
_rd: aioredis.Redis | None = None

PG_DSN    = os.environ.get("RAABTAX_PG_DSN",    "postgresql://postgres:postgres@localhost:5433/raabtax")
REDIS_URL = os.environ.get("RAABTAX_REDIS_URL", "redis://localhost:6379")

SESSION_TTL  = 86_400   # 24 h
PRESENCE_TTL = 300      # 5 min
OTP_TTL      = 900      # 15 min


# ── Lifecycle ────────────────────────────────────────────────────────────── #

async def _init_conn(conn: asyncpg.Connection) -> None:
    """Register JSONB codec so asyncpg encodes/decodes JSONB as Python dicts."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_db() -> None:
    """Create pools and apply schema. Idempotent — safe to call on every page open."""
    global _pg, _rd
    if _pg is not None:
        return

    _pg = await asyncpg.create_pool(
        dsn=PG_DSN, min_size=2, max_size=10, init=_init_conn
    )
    _rd = aioredis.from_url(REDIS_URL, decode_responses=True)
    await _apply_schema()


async def close_db() -> None:
    global _pg, _rd
    if _pg:
        await _pg.close()
        _pg = None
    if _rd:
        await _rd.aclose()
        _rd = None


async def _apply_schema() -> None:
    async with _pg.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL      PRIMARY KEY,
                full_name     TEXT        NOT NULL,
                email         TEXT        NOT NULL UNIQUE,
                phone         TEXT        NOT NULL UNIQUE,
                password_hash TEXT        NOT NULL,
                totp_secret   TEXT,
                is_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS channels (
                id                SERIAL      PRIMARY KEY,
                name              TEXT        NOT NULL UNIQUE,
                type              TEXT        NOT NULL DEFAULT 'public',
                server_context_id INT,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS messages (
                id                   SERIAL      PRIMARY KEY,
                channel_id           INT         NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
                sender_id            INT         NOT NULL REFERENCES users(id),
                text_content         TEXT,
                media_url            TEXT,
                link_preview_payload JSONB,
                timestamp            TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_messages_channel_ts
                ON messages (channel_id, timestamp ASC);
        """)

        # Migration: drop NOT NULL on totp_secret for existing tables
        try:
            await conn.execute(
                "ALTER TABLE users ALTER COLUMN totp_secret DROP NOT NULL"
            )
        except Exception:
            pass  # already nullable or column doesn't exist


# ── User operations ──────────────────────────────────────────────────────── #

async def create_user(
    full_name: str,
    email: str,
    phone: str,
    password_hash: str,
    totp_secret: str | None = None,
) -> int:
    async with _pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (full_name, email, phone, password_hash, totp_secret)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            full_name, email, phone, password_hash, totp_secret,
        )
        return row["id"]


async def get_user_by_id(user_id: int) -> asyncpg.Record | None:
    async with _pg.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def get_user_by_email(email: str) -> asyncpg.Record | None:
    async with _pg.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)


async def mark_verified(user_id: int) -> None:
    async with _pg.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_verified = TRUE WHERE id = $1", user_id
        )


# ── Email OTP operations (Redis) ─────────────────────────────────────────── #

async def store_email_otp(user_id: int, code: str) -> None:
    try:
        await _rd.setex(f"email_otp:{user_id}", OTP_TTL, code)
    except Exception:
        pass


async def get_email_otp(user_id: int) -> str | None:
    try:
        return await _rd.get(f"email_otp:{user_id}")
    except Exception:
        return None


async def delete_email_otp(user_id: int) -> None:
    try:
        await _rd.delete(f"email_otp:{user_id}")
    except Exception:
        pass


def send_verification_email(email: str, code: str) -> None:
    """
    Print the verification code to the terminal (always) and attempt delivery
    via a local SMTP debug server (python -m smtpd -n -c DebuggingServer localhost:1025).
    """
    print(
        f"\n{'=' * 52}\n"
        f"  RaabtaX — Email Verification\n"
        f"  To:      {email}\n"
        f"  Code:    {code}\n"
        f"  Expires: 15 minutes\n"
        f"{'=' * 52}\n"
    )
    try:
        msg = MIMEText(
            f"Your RaabtaX verification code is:\n\n"
            f"    {code}\n\n"
            f"This code expires in 15 minutes.\n"
            f"If you did not create a RaabtaX account, ignore this message."
        )
        msg["Subject"] = "RaabtaX — Your verification code"
        msg["From"] = "noreply@raabtax.local"
        msg["To"] = email
        with smtplib.SMTP("localhost", 1025, timeout=2) as smtp:
            smtp.send_message(msg)
    except Exception:
        pass  # local SMTP debug server not running — terminal output is the fallback


# ── Channel operations ───────────────────────────────────────────────────── #

async def get_channels(server_id: int | None = None) -> list[dict]:
    async with _pg.acquire() as conn:
        if server_id is not None:
            rows = await conn.fetch(
                "SELECT * FROM channels WHERE server_context_id = $1 ORDER BY id",
                server_id,
            )
        else:
            rows = await conn.fetch("SELECT * FROM channels ORDER BY id")
        return [dict(r) for r in rows]


async def seed_default_channels() -> None:
    """Insert starter channels if the table is empty."""
    async with _pg.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM channels")
        if count == 0:
            await conn.executemany(
                "INSERT INTO channels (name, type) VALUES ($1, $2)",
                [("general", "public"), ("coding-help", "public")],
            )


# ── Message operations ───────────────────────────────────────────────────── #

async def get_messages(channel_id: int, limit: int = 50) -> list[dict]:
    """Return up to `limit` messages for a channel, chronological order."""
    async with _pg.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT  m.id,
                    m.channel_id,
                    m.sender_id,
                    m.text_content,
                    m.media_url,
                    m.link_preview_payload,
                    m.timestamp,
                    u.full_name AS sender_full_name
            FROM    messages m
            JOIN    users    u ON u.id = m.sender_id
            WHERE   m.channel_id = $1
            ORDER BY m.timestamp ASC
            LIMIT   $2
            """,
            channel_id, limit,
        )
        return [dict(r) for r in rows]


async def insert_message(
    channel_id: int,
    sender_id: int,
    text_content: str,
    media_url: str | None = None,
    link_preview_payload: dict | None = None,
) -> dict:
    """Insert a message and return the full row including sender_full_name."""
    async with _pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages
                (channel_id, sender_id, text_content, media_url, link_preview_payload)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, channel_id, sender_id, text_content,
                      media_url, link_preview_payload, timestamp
            """,
            channel_id, sender_id, text_content, media_url, link_preview_payload,
        )
        user = await conn.fetchrow(
            "SELECT full_name FROM users WHERE id = $1", sender_id
        )
        return {**dict(row), "sender_full_name": user["full_name"]}


async def publish_message(channel_id: int, msg: dict) -> None:
    """Publish a message dict to the Redis pub/sub channel for live delivery."""
    payload = dict(msg)
    if isinstance(payload.get("timestamp"), datetime):
        payload["timestamp"] = payload["timestamp"].isoformat()
    await _rd.publish(f"ch:{channel_id}", json.dumps(payload))


def get_pubsub() -> aioredis.client.PubSub:
    """Return a new pub/sub object bound to the shared Redis connection."""
    return _rd.pubsub()


# ── Session operations (Redis) ───────────────────────────────────────────── #

async def create_session(user_id: int) -> str:
    """
    Generate a session token and persist it in Redis.
    If Redis is unreachable the token is still returned — the caller stores
    user_id in page.session.store directly, so the session remains valid for
    the current connection even without Redis backing.
    """
    token = secrets.token_urlsafe(32)
    try:
        await _rd.setex(f"session:{token}", SESSION_TTL, str(user_id))
    except Exception:
        pass  # Redis optional — auth flow continues via page.session.store
    return token


async def resolve_session(token: str) -> int | None:
    try:
        val = await _rd.get(f"session:{token}")
        return int(val) if val else None
    except Exception:
        return None


async def delete_session(token: str) -> None:
    try:
        await _rd.delete(f"session:{token}")
    except Exception:
        pass


# ── Presence operations (Redis) ──────────────────────────────────────────── #

async def set_presence(user_id: int) -> None:
    """Mark a user as active. TTL is PRESENCE_TTL seconds (5 min)."""
    try:
        await _rd.setex(f"presence:{user_id}", PRESENCE_TTL, "1")
    except Exception:
        pass


async def get_presence(user_id: int) -> bool:
    """Return True if the user has an active presence key."""
    try:
        return bool(await _rd.exists(f"presence:{user_id}"))
    except Exception:
        return False
