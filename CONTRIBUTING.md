# Contributing to RaabtaX

Thanks for helping out. This doc covers everything you need to go from zero to a merged PR.

## Quick Start

### 1. Fork and clone

```bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR_USERNAME/RaabtaX.git
cd RaabtaX
git remote add upstream https://github.com/Mustafahubs/RaabtaX.git
```

### 2. Set up your environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e .
```

### 3. Configure local services

You need PostgreSQL and (optionally) Redis. Create a `.env` file:

```env
RAABTAX_PG_DSN=postgresql://postgres:yourpassword@localhost:5432/raabtax
RAABTAX_REDIS_URL=redis://localhost:6379
```

The database schema is applied automatically on first run — no migration steps.

### 4. Run the app

```bash
python main.py
```

---

## Workflow

### Branch naming

```
feature/short-description     # new functionality
fix/short-description         # bug fix
refactor/short-description    # code cleanup with no behavior change
```

Always branch off `main`:

```bash
git fetch upstream
git checkout -b feature/my-thing upstream/main
```

### Commit messages

- One line, imperative mood: `Add presence indicator to DM list`
- Reference the screen or module affected: `Fix OTP box border on backspace in verify_view`
- No need for issue numbers unless the repo uses them

### Pull Requests

1. Push your branch to your fork
2. Open a PR against `Mustafahubs/RaabtaX` main
3. Describe **what** changed and **why** — not just a list of files
4. Keep PRs focused: one feature or fix per PR
5. Respond to review comments within a day or two

---

## Code Style

These are the conventions already used in the codebase — follow them so reviews stay fast.

### General

- No comments unless the **why** is non-obvious (a hidden constraint, a workaround, a subtle invariant). Well-named identifiers explain the what.
- No backwards-compat shims, no feature flags, no dead code with `# removed` notes.
- No error handling for things that cannot happen — only validate at real boundaries (user input, DB calls, external APIs).

### Views

- Each screen is a class (e.g. `LoginView`) with a `build() -> ft.View` method plus a module-level async factory function (`async def login_view(page) -> ft.View`).
- Section builders are private methods (`_build_header`, `_build_footer`, etc.).
- Event handlers are async and named `_on_<event>` (`_on_change`, `_on_back`).
- All design tokens (colors, spacing, font sizes, radii) come from `theme.py` — never hardcode hex values or pixel numbers.

### Database

- All DB operations live in `database.py`. Views never import `asyncpg` or `redis` directly.
- Redis calls are wrapped in `try/except` — Redis is optional and must not crash auth.

### Routing

- Add new routes to `router.py` `_resolve()` match block only.
- `page.navigate("/route")` — never manipulate `page.views` directly outside `AppRouter`.

---

## Adding a New Screen

1. Create `views/my_screen_view.py` with a `MyScreenView` class and `async def my_screen_view(page)` factory.
2. Add a route case in `router.py`:
   ```python
   case "/myscreen":
       return await my_screen_view(self._page)
   ```
3. Navigate to it from other views with `self._page.navigate("/myscreen")`.
4. Use only tokens from `theme.py` for styling.

---

## Open Areas

These are unfinished pieces where contributions are most welcome:

| Area | File(s) | Notes |
|------|---------|-------|
| Real DM conversations | `database.py`, `dm_chat_view.py`, `dms_view.py` | Need a `direct_messages` table and live pub/sub |
| Logged-in user name in drawer | `chat_hub_view.py` | Currently shows hardcoded "Alex Chen" |
| Google OAuth | `login_view.py`, `register_view.py` | Stubs exist, logic is `pass` |
| Biometric login | `login_view.py` | Stub only |
| Push notifications | — | Not started |

---

## Questions

Open a GitHub issue or reach out to the maintainer directly. Welcome aboard.
