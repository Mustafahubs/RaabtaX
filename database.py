"""
Async data layer — PostgreSQL (asyncpg) + Redis.

Connection pools are module-level infrastructure globals.
Per-user state is NEVER stored here; it belongs in page.session.store.

Defaults target a local dev stack:
  PG:    postgresql://postgres:postgres@localhost:5433/raabtax
  Redis: redis://localhost:6379

Override via environment variables:
  RAABTAX_PG_DSN       — full asyncpg DSN
  RAABTAX_REDIS_URL    — redis:// URL
  RAABTAX_SMTP_USER    — outbound Gmail address
  RAABTAX_SMTP_PASSWORD — Gmail app password
"""
import asyncio
import json
import os
import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
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

SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.environ.get("RAABTAX_SMTP_USER",     "noreply.raabtax@gmail.com")
SMTP_PASSWORD = os.environ.get("RAABTAX_SMTP_PASSWORD", "")

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


def _build_verification_html(code: str) -> str:
    spaced = "  ".join(code)  # visual breathing room between digits
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>RaabtaX — Verify Your Account</title>
</head>
<body style="margin:0;padding:0;background-color:#0d1117;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background-color:#0d1117;padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:520px;background-color:#161b22;border-radius:16px;
                      border:1px solid #21262d;overflow:hidden;">

          <!-- ── Header ── -->
          <tr>
            <td style="background-color:#1c2333;padding:32px 40px 28px;
                       text-align:center;border-bottom:1px solid #21262d;">
              <div style="display:inline-block;background-color:rgba(31,111,235,0.12);
                          border:1px solid rgba(31,111,235,0.28);border-radius:12px;
                          padding:10px 18px;margin-bottom:14px;">
                <span style="font-size:20px;color:#58a6ff;font-weight:700;
                             letter-spacing:2px;">RX</span>
              </div>
              <h1 style="margin:0;font-size:22px;font-weight:700;
                         color:#e6edf3;letter-spacing:-0.3px;">RaabtaX</h1>
              <p style="margin:5px 0 0;font-size:11px;color:#6e7681;
                        letter-spacing:1.8px;text-transform:uppercase;">Secure Messaging</p>
            </td>
          </tr>

          <!-- ── Body ── -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <h2 style="margin:0 0 10px;font-size:18px;font-weight:600;
                         color:#e6edf3;">Verify your account</h2>
              <p style="margin:0 0 32px;font-size:14px;line-height:1.75;color:#8b949e;">
                Welcome to RaabtaX. Use the one-time code below to complete your
                registration. This code is valid for
                <strong style="color:#c9d1d9;">15&nbsp;minutes</strong>.
              </p>

              <!-- ── OTP box ── -->
              <div style="background-color:#0d1117;border:1px solid #30363d;
                          border-radius:12px;padding:30px 20px 26px;
                          text-align:center;margin-bottom:32px;">
                <p style="margin:0 0 10px;font-size:10px;font-weight:600;
                           color:#6e7681;letter-spacing:2px;
                           text-transform:uppercase;">Verification Code</p>
                <span style="font-family:'Courier New',Courier,monospace;
                             font-size:44px;font-weight:700;color:#58a6ff;
                             letter-spacing:14px;display:inline-block;
                             padding-left:14px;">{spaced}</span>
              </div>

              <!-- ── Disclaimer ── -->
              <div style="background-color:#161b22;border:1px solid #21262d;
                          border-left:3px solid #d29922;border-radius:6px;
                          padding:14px 18px;">
                <p style="margin:0;font-size:12px;line-height:1.65;color:#8b949e;">
                  If you did not create a RaabtaX account, you can safely ignore
                  this email. Never share this code with anyone — our team will
                  never ask for it.
                </p>
              </div>
            </td>
          </tr>

          <!-- ── Footer ── -->
          <tr>
            <td style="padding:18px 40px 26px;border-top:1px solid #21262d;
                       text-align:center;">
              <p style="margin:0;font-size:11px;color:#484f58;">
                © 2026 RaabtaX &nbsp;·&nbsp; Secure Messaging Platform
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def send_verification_email(to_email: str, code: str) -> None:
    """
    Dispatch an HTML verification email via Gmail SMTP on a thread pool so
    the blocking network handshake never stalls Flet's async event loop.

    Falls back to a terminal print if delivery fails (SMTP misconfigured,
    network unavailable, etc.) so development stays unblocked.
    """
    def _send() -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "RaabtaX — Your verification code"
        msg["From"]    = f"RaabtaX <{SMTP_USER}>"
        msg["To"]      = to_email

        plain = (
            f"Your RaabtaX verification code is: {code}\n\n"
            f"This code expires in 15 minutes.\n"
            f"If you did not initiate this, ignore this email."
        )
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(_build_verification_html(code), "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)

    try:
        await asyncio.to_thread(_send)
    except Exception as exc:
        print(
            f"\n{'=' * 52}\n"
            f"  [RaabtaX] Email delivery failed: {exc}\n"
            f"  To:   {to_email}\n"
            f"  Code: {code}\n"
            f"{'=' * 52}\n"
        )


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
