# RaabtaX

A real-time mobile chat app built with Python + Flet (Flutter), PostgreSQL, and Redis.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | [Flet](https://flet.dev) 0.85+ (Python/Flutter) |
| Database | PostgreSQL via `asyncpg` |
| Pub/Sub | Redis (live message delivery) |
| Auth | bcrypt passwords + TOTP (Google Authenticator) |
| Runtime | Python 3.14+ with full async/await |

## Screens

| Route | Screen |
|-------|--------|
| `/login` | Login with email + password |
| `/register` | Register with name, email, phone, password |
| `/verify` | 6-digit TOTP verification (Google Authenticator) |
| `/hub` | Channel-based chat hub with drawer navigation |
| `/dms` | Direct messages list |
| `/dm` | 1-on-1 DM chat |

## Prerequisites

- **Python 3.14+**
- **PostgreSQL** running locally (or any reachable instance)
- **Redis** (optional for auth — required for live pub/sub in the chat hub)
- **Google Authenticator** (iOS/Android) for 2FA during registration

## Setup

### 1. Clone

```bash
git clone https://github.com/Mustafahubs/RaabtaX.git
cd RaabtaX
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -e .
```

Or with `uv`:

```bash
uv sync
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
RAABTAX_PG_DSN=postgresql://postgres:yourpassword@localhost:5432/raabtax
RAABTAX_REDIS_URL=redis://localhost:6379
```

> The app creates all tables automatically on first run — no migration tool needed.

### 4. Run

```bash
python main.py
```

Flet opens the app as a native window on desktop and can also be served as a web or Android app.

## Project Structure

```
RaabtaX/
├── main.py              # Entry point — configures page and boots router
├── router.py            # SPA-style route controller
├── database.py          # Async data layer (PostgreSQL + Redis)
├── theme.py             # Design tokens (Colors, Spacing, FontSize, etc.)
├── views/
│   ├── login_view.py
│   ├── register_view.py
│   ├── verify_view.py
│   ├── chat_hub_view.py
│   ├── dms_view.py
│   └── dm_chat_view.py
├── UI_Screens/          # HTML mockups and PNGs (design reference only)
├── pyproject.toml
└── .env                 # Local secrets — never committed
```

## Architecture Notes

- **Routing**: `AppRouter` in `router.py` does full view-stack replacement on every navigation — no stale widget state survives a route change.
- **Session**: `page.session.store` holds `user_id` and `session_token` in-memory per connection. Redis backs the token for cross-connection persistence.
- **OTP input**: The verify screen uses a hidden `ft.TextField` as the single source of truth, with six read-only visual containers. One invisible overlay absorbs all taps and opens the numeric keyboard.
- **Redis is optional for auth**: `create_session()` returns a token even if Redis is unreachable. The auth flow continues via `page.session.store`. Live pub/sub in the chat hub requires Redis.
