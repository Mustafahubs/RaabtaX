import asyncio
import json
import random
import time
from datetime import datetime

import flet as ft

import database
from theme import Colors, Radius, Spacing, FontSize, FontWeight

# ── Deterministic per-sender styling ────────────────────────────────────── #

_AVATAR_COLORS = [
    Colors.PRIMARY_CONTAINER,
    "#1a3a2a",
    "#2d1b3a",
    "#3a1a1a",
    "#1a2a3a",
    "#2a2a1a",
]
_AUTHOR_COLORS = [
    Colors.PRIMARY,
    Colors.TERTIARY,
    "#80cbc4",
    "#ffb74d",
    "#f48fb1",
    "#ce93d8",
]

# ── Placeholder DM data — user_id drives Redis presence lookup ───────────── #

_DMS = [
    {"name": "Sarah Mitchell", "initials": "SM",
     "color": Colors.PRIMARY_CONTAINER, "user_id": 2},
    {"name": "James Holden",   "initials": "JH",
     "color": Colors.SURFACE_CONTAINER_HIGH, "user_id": 3},
]

# Consecutive messages within this window (seconds) from the same sender are grouped
_GROUP_WINDOW   = 300
# Typing signal debounce — publish at most once per this many seconds
_TYPING_DEBOUNCE = 2.0
# Prune a typing user after this many seconds of silence
_TYPING_EXPIRY  = 3.5


def _fmt_time(ts) -> str:
    if ts is None:
        return ""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    h = ts.hour % 12 or 12
    return f"{h}:{ts.minute:02d} {'AM' if ts.hour < 12 else 'PM'}"


def _parse_ts(ts) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _initials(full_name: str) -> str:
    parts = full_name.split()
    return (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()


class ChatHubView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        # ── Active channel state ─────────────────────────────────────── #
        self._active_channel: str = "general"
        self._active_channel_id: int | None = None

        # ── Background task handles ──────────────────────────────────── #
        self._listener_task: asyncio.Future | None = None   # message pub/sub
        self._typing_task:   asyncio.Future | None = None   # typing pub/sub
        self._prune_task:    asyncio.Future | None = None   # typing expiry sweep

        # ── Typing state ─────────────────────────────────────────────── #
        # {user_id: (full_name, last_seen_monotonic)}
        self._typing_users: dict[int, tuple[str, float]] = {}
        self._last_typing_sent: float = 0.0  # monotonic clock, not wall time

        # ── Mutable widgets updated in-place ─────────────────────────── #
        self._channel_title = ft.Text(
            "# general",
            size=FontSize.TITLE_LG,
            weight=FontWeight.SEMIBOLD,
            color=Colors.PRIMARY,
        )
        self._input_field = ft.TextField(
            hint_text="Message # general",
            hint_style=ft.TextStyle(color=Colors.ON_SURFACE_VARIANT, size=FontSize.BODY_MD),
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            text_size=FontSize.BODY_MD,
            color=Colors.ON_SURFACE,
            cursor_color=Colors.PRIMARY,
            expand=True,
            on_change=self._on_typing,
        )
        self._typing_label = ft.Text(
            "",
            size=FontSize.LABEL_LG,
            color=Colors.ON_SURFACE_VARIANT,
            italic=True,
        )

        # ── Profile header widgets — hydrated in _initialize() ───────── #
        self._profile_name_text = ft.Text(
            "...",
            size=FontSize.HEADLINE_MOBILE,
            weight=FontWeight.BOLD,
            color=Colors.PRIMARY,
        )
        self._profile_initials_text = ft.Text(
            "?",
            size=FontSize.LABEL_LG,
            weight=FontWeight.BOLD,
            color=Colors.ON_PRIMARY_CONTAINER,
        )

        # ── DM presence dot references — keyed by user_id ────────────── #
        # Populated in _dm_row(), updated in _initialize()
        self._dm_presence_dots: dict[int, ft.Container] = {}

        # ── Drawer channels column — populated by _initialize() ──────── #
        self._channels_col = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text(
                        "Loading channels...",
                        size=FontSize.LABEL_LG,
                        color=Colors.OUTLINE,
                        italic=True,
                    ),
                    padding=ft.Padding(left=16, right=16, top=16, bottom=4),
                )
            ],
            spacing=0,
        )

        self._message_list = self._build_message_list()
        self._drawer = self._build_drawer()
        self._view: ft.View | None = None  # set in build()

    # ------------------------------------------------------------------ #
    #  Shared helpers                                                      #
    # ------------------------------------------------------------------ #

    def _avatar(self, initials: str, bg: str, size: int = 40) -> ft.Container:
        return ft.Container(
            content=ft.Text(initials, size=FontSize.LABEL_LG,
                            weight=FontWeight.BOLD, color=Colors.ON_SURFACE),
            width=size, height=size,
            border_radius=size / 2,
            bgcolor=bg,
            alignment=ft.Alignment.CENTER,
        )

    def _icon_btn(self, icon, color=Colors.ON_SURFACE_VARIANT,
                  on_click=None, right_margin: int = 0) -> ft.Container:
        return ft.Container(
            content=ft.Icon(icon, color=color, size=22),
            padding=ft.Padding.all(8),
            border_radius=Radius.FULL,
            ink=True,
            on_click=on_click,
            margin=ft.Margin(right=right_margin, left=0, top=0, bottom=0),
        )

    # ------------------------------------------------------------------ #
    #  Message rendering                                                   #
    # ------------------------------------------------------------------ #

    def _bubble(self, text: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=FontSize.BODY_MD, color=Colors.ON_SURFACE),
            padding=ft.Padding.all(12),
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=ft.BorderRadius(
                top_left=0,
                top_right=Radius.DEFAULT,
                bottom_left=Radius.DEFAULT,
                bottom_right=Radius.DEFAULT,
            ),
        )

    def _link_preview_from_data(self, preview: dict) -> ft.Container:
        title = preview.get("title", "Link Preview")
        desc  = preview.get("description", "")
        url   = preview.get("url", "")

        header = ft.Container(
            height=72,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=ft.BorderRadius(top_left=12, top_right=12,
                                          bottom_left=0, bottom_right=0),
            content=ft.Row(
                controls=[ft.Icon(ft.Icons.LINK, color=Colors.PRIMARY, size=28)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        body = ft.Container(
            padding=ft.Padding.all(12),
            content=ft.Column(
                controls=[
                    ft.Text(title, size=FontSize.BODY_MD, weight=FontWeight.SEMIBOLD,
                            color=Colors.PRIMARY),
                    ft.Container(height=4),
                    ft.Text(desc, size=FontSize.LABEL_LG, color=Colors.ON_SURFACE_VARIANT,
                            max_lines=2),
                    ft.Container(height=6),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LINK, color=Colors.OUTLINE, size=12),
                            ft.Text(url, size=FontSize.LABEL_SM, color=Colors.OUTLINE),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
            ),
        )
        return ft.Container(
            content=ft.Column(controls=[header, body], spacing=0),
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            width=280,
        )

    def _full_message_row(self, data: dict) -> ft.Container:
        """
        Full row: circular avatar + author name + timestamp + bubble(s).
        Rendered for the first message of every new sender group.
        .data carries {sender_id, timestamp} for the O(1) grouping look-behind.
        """
        sender_id  = data.get("sender_id", 0)
        full_name  = data.get("sender_full_name", "Unknown")
        avatar_bg  = _AVATAR_COLORS[sender_id % len(_AVATAR_COLORS)]
        author_col = _AUTHOR_COLORS[sender_id % len(_AUTHOR_COLORS)]
        time_str   = _fmt_time(data.get("timestamp"))
        preview    = data.get("link_preview_payload")

        bubbles: list[ft.Control] = [self._bubble(data.get("text_content", ""))]
        if isinstance(preview, dict):
            bubbles += [ft.Container(height=6), self._link_preview_from_data(preview)]

        row = ft.Row(
            controls=[
                ft.Column(
                    controls=[self._avatar(_initials(full_name), avatar_bg)],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(width=12),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(full_name, size=FontSize.BODY_MD,
                                        weight=FontWeight.SEMIBOLD, color=author_col),
                                ft.Text(time_str, size=FontSize.LABEL_SM,
                                        color=Colors.OUTLINE_VARIANT),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.BASELINE,
                        ),
                        *bubbles,
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        return ft.Container(
            content=row,
            padding=ft.Padding(top=20, bottom=0, left=16, right=16),
            data={"sender_id": sender_id, "timestamp": _parse_ts(data.get("timestamp"))},
        )

    def _compact_message_row(self, data: dict) -> ft.Container:
        """
        Compact row: no avatar, no header — bubble(s) indented to align with the
        content column of the preceding full row.
        Avatar (40) + gap (12) = 52 px left spacer. Top-pad 4 px keeps the group
        visually tight without merging.
        """
        sender_id = data.get("sender_id", 0)
        preview   = data.get("link_preview_payload")

        bubbles: list[ft.Control] = [self._bubble(data.get("text_content", ""))]
        if isinstance(preview, dict):
            bubbles += [ft.Container(height=6), self._link_preview_from_data(preview)]

        row = ft.Row(
            controls=[
                ft.Container(width=52),  # mirrors avatar (40) + gap (12)
                ft.Column(controls=bubbles, spacing=4, expand=True),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        return ft.Container(
            content=row,
            padding=ft.Padding(top=4, bottom=0, left=16, right=16),
            data={"sender_id": sender_id, "timestamp": _parse_ts(data.get("timestamp"))},
        )

    def _append_message(self, data: dict) -> None:
        """
        Core append routine shared by _load_messages, _listen_channel, _on_send.

        Grouping (O(1)):
          Peek controls[-1].data — {sender_id, timestamp}.
          Same sender_id AND delta < _GROUP_WINDOW seconds → compact row.
          Otherwise → full row.
          Separators (ft.Row, no .data dict) naturally break grouping.

        Strips the 'no messages' placeholder on first real message.
        """
        controls = self._message_list.controls

        # Strip placeholder — a Container whose .data is not a sender dict
        if (controls
                and isinstance(controls[-1], ft.Container)
                and not isinstance(controls[-1].data, dict)):
            controls.clear()

        new_sid = data.get("sender_id", 0)
        new_ts  = _parse_ts(data.get("timestamp"))

        grouped = False
        if controls:
            last_data = getattr(controls[-1], "data", None)
            if isinstance(last_data, dict):
                last_sid = last_data.get("sender_id")
                last_ts  = last_data.get("timestamp")
                if last_sid == new_sid and last_ts and new_ts:
                    grouped = abs((new_ts - last_ts).total_seconds()) < _GROUP_WINDOW

        controls.append(
            self._compact_message_row(data) if grouped else self._full_message_row(data)
        )

    def _separator(self, label: str) -> ft.Row:
        line = lambda: ft.Container(height=1, bgcolor=Colors.OUTLINE_VARIANT,
                                    expand=True, opacity=0.25)
        return ft.Row(
            controls=[
                line(),
                ft.Text(label, size=FontSize.LABEL_SM, color=Colors.OUTLINE),
                line(),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            # no data key — grouping never fires after a separator
        )

    def _empty_placeholder(self, label: str) -> ft.Container:
        # No data key → .data is None → identified as placeholder by _append_message
        return ft.Container(
            content=ft.Text(label, size=FontSize.BODY_MD,
                            color=Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment.CENTER,
            expand=True,
        )

    def _build_message_list(self) -> ft.ListView:
        return ft.ListView(
            controls=[self._empty_placeholder("Loading messages...")],
            spacing=0,      # all gaps controlled per-row via Container.padding
            padding=ft.Padding(left=0, right=0, top=16, bottom=88),
            expand=True,
        )

    # ------------------------------------------------------------------ #
    #  Typing indicator                                                    #
    # ------------------------------------------------------------------ #

    def _update_typing_label(self) -> None:
        """Recompute the typing label text from _typing_users and push the update."""
        if not self._typing_users:
            text = ""
        elif len(self._typing_users) == 1:
            name = next(iter(self._typing_users.values()))[0]
            first = name.split()[0]
            text = f"{first} is typing..."
        else:
            text = "Multiple people are typing..."

        self._typing_label.value = text
        self._typing_label.update()

    async def _prune_typing_loop(self) -> None:
        """
        Sweep _typing_users every second. Remove any user whose last signal
        is older than _TYPING_EXPIRY seconds. This is what makes the indicator
        disappear naturally when someone stops typing without sending.
        """
        while True:
            try:
                await asyncio.sleep(1.0)
                now = time.monotonic()
                stale = [
                    uid for uid, (_, last_seen) in self._typing_users.items()
                    if now - last_seen > _TYPING_EXPIRY
                ]
                if stale:
                    for uid in stale:
                        self._typing_users.pop(uid, None)
                    self._update_typing_label()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Async initialization & live data pipeline                           #
    # ------------------------------------------------------------------ #

    async def _initialize(self) -> None:
        """
        Runs once after build() via page.run_task().

        1. Auth-guards /hub — bounces unauthenticated sessions to /login.
        2. Hydrates profile header from DB.
        3. Writes presence to Redis; starts presence heartbeat.
        4. Fetches channels; seeds defaults if empty.
        5. Loads the first channel's messages.
        6. Starts message + typing pub/sub listeners.
        7. Starts typing expiry prune loop.
        8. Hydrates DM presence dots via Redis get_presence().
        """
        # ── Auth guard ───────────────────────────────────────────────── #
        user_id_str = self._page.session.store.get("user_id")
        if not user_id_str:
            self._page.navigate("/login")
            return
        user_id = int(user_id_str)

        # ── Profile header ───────────────────────────────────────────── #
        try:
            user = await database.get_user_by_id(user_id)
            if user:
                name = user["full_name"]
                self._profile_name_text.value     = name
                self._profile_initials_text.value = _initials(name)
                self._profile_name_text.update()
                self._profile_initials_text.update()
        except Exception:
            pass

        # ── Presence ────────────────────────────────────────────────── #
        try:
            await database.set_presence(user_id)
        except Exception:
            pass

        # ── Channels ─────────────────────────────────────────────────── #
        try:
            channels = await database.get_channels()
            if not channels:
                await database.seed_default_channels()
                channels = await database.get_channels()
        except Exception:
            channels = []

        if channels:
            self._active_channel    = channels[0]["name"]
            self._active_channel_id = channels[0]["id"]
            self._channel_title.value   = f"# {self._active_channel}"
            self._input_field.hint_text = f"Message # {self._active_channel}"
            self._channel_title.update()
            self._input_field.update()

        self._channels_col.controls = [
            self._section_label("TEXT CHANNELS"),
            *[
                self._channel_row_db(ch["id"], ch["name"], active=(i == 0))
                for i, ch in enumerate(channels)
            ],
        ]
        self._channels_col.update()

        # ── Initial message load + listeners ─────────────────────────── #
        if self._active_channel_id is not None:
            await self._load_messages(self._active_channel_id)
            self._start_listeners(self._active_channel_id)

        # ── Typing prune loop (single global task, not per-channel) ──── #
        self._prune_task = self._page.run_task(self._prune_typing_loop)

        # ── Presence heartbeat ───────────────────────────────────────── #
        self._page.run_task(self._presence_loop, user_id)

        # ── Hydrate DM sidebar presence dots ─────────────────────────── #
        for dm in _DMS:
            uid = dm.get("user_id")
            if uid and uid in self._dm_presence_dots:
                try:
                    online = await database.get_presence(uid)
                except Exception:
                    online = False
                dot = self._dm_presence_dots[uid]
                dot.bgcolor = Colors.TERTIARY if online else Colors.OUTLINE_VARIANT
                dot.update()

    async def _load_messages(self, channel_id: int) -> None:
        """Replace the ListView with the last 50 DB messages, grouping applied."""
        try:
            rows = await database.get_messages(channel_id, limit=50)
        except Exception:
            rows = []

        self._message_list.controls.clear()

        if not rows:
            self._message_list.controls.append(
                self._empty_placeholder("No messages yet — be the first to say something.")
            )
        else:
            prev_date: str | None = None
            for row in rows:
                ts = row.get("timestamp")
                if ts:
                    date_label = (ts.strftime("%d %B %Y")
                                  if hasattr(ts, "strftime") else str(ts)[:10])
                    if date_label != prev_date:
                        self._message_list.controls.append(self._separator(date_label))
                        prev_date = date_label
                self._append_message(row)

        self._message_list.update()

    def _start_listeners(self, channel_id: int) -> None:
        """
        Cancel previous message + typing listeners and start fresh ones for
        channel_id. Clears typing state so stale indicators don't bleed across
        channel switches.
        """
        if self._listener_task is not None:
            self._listener_task.cancel()
        if self._typing_task is not None:
            self._typing_task.cancel()

        self._typing_users.clear()
        self._update_typing_label()

        self._listener_task = self._page.run_task(self._listen_channel, channel_id)
        self._typing_task   = self._page.run_task(self._listen_typing,  channel_id)

    async def _listen_channel(self, channel_id: int) -> None:
        """
        Persistent message pub/sub loop with exponential-backoff reconnection.

        CancelledError (intentional teardown) → break immediately.
        All other exceptions (network dropout, socket reset) → backoff retry.
        Stale-listener guard dissolves the task if the active channel changed
        during a backoff window.
        """
        delay = 2.0
        max_delay = 30.0

        while True:
            pubsub = database.get_pubsub()
            try:
                await pubsub.subscribe(f"ch:{channel_id}")
                delay = 2.0
                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue
                    try:
                        data = json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    self._append_message(data)
                    self._message_list.update()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            finally:
                await pubsub.aclose()

            if self._active_channel_id != channel_id:
                break

            jitter = random.uniform(0, delay * 0.2)
            await asyncio.sleep(delay + jitter)
            delay = min(delay * 2, max_delay)

    async def _listen_typing(self, channel_id: int) -> None:
        """
        Lightweight pub/sub loop for the ch:{channel_id}:typing Redis channel.

        Incoming payload: {"user_id": int, "full_name": str, "is_typing": true}

        Own signals are filtered out (we already know we're typing).
        Each valid signal upserts the user into _typing_users with the current
        monotonic timestamp, then calls _update_typing_label(). The prune loop
        does the expiry sweep independently.

        Same exponential-backoff + stale-listener pattern as _listen_channel.
        """
        delay = 2.0
        max_delay = 30.0
        my_uid_str = self._page.session.store.get("user_id")

        while True:
            pubsub = database.get_pubsub()
            try:
                await pubsub.subscribe(f"ch:{channel_id}:typing")
                delay = 2.0
                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue
                    try:
                        data = json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue

                    uid       = data.get("user_id")
                    full_name = data.get("full_name", "Someone")

                    if not uid or not data.get("is_typing"):
                        continue
                    # Don't show our own indicator back to ourselves
                    if my_uid_str and uid == int(my_uid_str):
                        continue

                    self._typing_users[uid] = (full_name, time.monotonic())
                    self._update_typing_label()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            finally:
                await pubsub.aclose()

            if self._active_channel_id != channel_id:
                break

            jitter = random.uniform(0, delay * 0.2)
            await asyncio.sleep(delay + jitter)
            delay = min(delay * 2, max_delay)

    async def _presence_loop(self, user_id: int) -> None:
        while True:
            try:
                await asyncio.sleep(240)
                await database.set_presence(user_id)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)

    # ------------------------------------------------------------------ #
    #  Input bar                                                           #
    # ------------------------------------------------------------------ #

    def _build_input_bar(self) -> ft.Container:
        pill = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.ATTACH_FILE,
                                        color=Colors.ON_SURFACE_VARIANT, size=20),
                        padding=ft.Padding.all(8),
                    ),
                    self._input_field,
                    ft.Container(
                        content=ft.Icon(ft.Icons.MOOD,
                                        color=Colors.ON_SURFACE_VARIANT, size=20),
                        padding=ft.Padding.all(8),
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            height=48,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.FULL,
        )

        send_btn = ft.Container(
            content=ft.Icon(ft.Icons.SEND, color=Colors.ON_PRIMARY, size=20),
            width=48, height=48,
            bgcolor=Colors.PRIMARY,
            border_radius=Radius.FULL,
            alignment=ft.Alignment.CENTER,
            on_click=self._on_send,
            ink=True,
        )

        return ft.Container(
            content=ft.Row(
                controls=[pill, send_btn],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=Colors.SURFACE_CONTAINER,
            border=ft.Border(top=ft.BorderSide(1, Colors.OUTLINE_VARIANT)),
        )

    # ------------------------------------------------------------------ #
    #  Navigation Drawer                                                   #
    # ------------------------------------------------------------------ #

    def _server_rail(self) -> ft.Container:
        s1 = ft.Container(
            content=ft.Text("S1", size=FontSize.LABEL_LG, weight=FontWeight.BOLD,
                            color=Colors.ON_PRIMARY),
            width=48, height=48, border_radius=12,
            bgcolor=Colors.PRIMARY, alignment=ft.Alignment.CENTER, ink=True,
        )
        s2 = ft.Container(
            content=ft.Text("S2", size=FontSize.LABEL_LG, weight=FontWeight.BOLD,
                            color=Colors.ON_SURFACE_VARIANT),
            width=48, height=48, border_radius=Radius.FULL,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH, alignment=ft.Alignment.CENTER, ink=True,
        )
        add_btn = ft.Container(
            content=ft.Icon(ft.Icons.ADD, color=Colors.PRIMARY, size=20),
            width=48, height=48, border_radius=Radius.FULL,
            border=ft.Border.all(2, Colors.OUTLINE_VARIANT),
            alignment=ft.Alignment.CENTER, ink=True,
        )
        return ft.Container(
            width=64,
            bgcolor="#060e20",
            padding=ft.Padding.symmetric(vertical=16),
            content=ft.Column(
                controls=[s1, s2, add_btn],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
        )

    def _channel_row_db(self, channel_id: int, name: str, active: bool) -> ft.Container:
        async def _tap(e: ft.ControlEvent) -> None:
            if self._active_channel_id == channel_id:
                await self._view.close_drawer()
                return

            self._active_channel    = name
            self._active_channel_id = channel_id
            self._channel_title.value   = f"# {name}"
            self._input_field.hint_text = f"Message # {name}"
            self._channel_title.update()
            self._input_field.update()

            await self._load_messages(channel_id)
            self._start_listeners(channel_id)
            await self._view.close_drawer()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TAG,
                            color=Colors.PRIMARY if active else Colors.ON_SURFACE_VARIANT,
                            size=18),
                    ft.Text(f"# {name}", size=FontSize.BODY_MD,
                            color=Colors.ON_SURFACE if active else Colors.ON_SURFACE_VARIANT,
                            weight=FontWeight.MEDIUM if active else None),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=Radius.FULL,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH if active else None,
            on_click=_tap,
            ink=not active,
        )

    def _dm_row(self, dm: dict) -> ft.Container:
        """
        Build a DM row with a mutable presence dot.
        The dot Container is stored in self._dm_presence_dots[user_id] so
        _initialize() can update its .bgcolor after the async presence check.
        Default colour is OUTLINE_VARIANT (offline) — updated live after init.
        """
        dot = ft.Container(
            width=10, height=10,
            bgcolor=Colors.OUTLINE_VARIANT,   # default offline; updated in _initialize
            border_radius=5,
            border=ft.Border.all(2, Colors.SURFACE_CONTAINER),
            right=0, bottom=0,
        )
        uid = dm.get("user_id")
        if uid:
            self._dm_presence_dots[uid] = dot

        avatar_stack = ft.Stack(
            controls=[
                self._avatar(dm["initials"], dm["color"], size=32),
                dot,
            ],
            width=32, height=32,
        )

        async def _tap(e: ft.ControlEvent) -> None:
            await self._view.close_drawer()
            self._page.navigate("/dm")

        return ft.Container(
            content=ft.Row(
                controls=[
                    avatar_stack,
                    ft.Text(dm["name"], size=FontSize.BODY_MD,
                            color=Colors.ON_SURFACE_VARIANT, expand=True),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=Radius.FULL,
            ink=True,
            on_click=_tap,
        )

    def _section_label(self, text: str, trailing: ft.Control | None = None) -> ft.Container:
        row_controls: list[ft.Control] = [
            ft.Text(text, size=FontSize.LABEL_LG, color=Colors.OUTLINE,
                    weight=FontWeight.MEDIUM, expand=True),
        ]
        if trailing:
            row_controls.append(trailing)
        return ft.Container(
            content=ft.Row(controls=row_controls,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(left=16, right=16, top=16, bottom=4),
        )

    def _build_drawer(self) -> ft.NavigationDrawer:
        profile_avatar = ft.Stack(
            controls=[
                ft.Container(
                    content=self._profile_initials_text,
                    width=48, height=48, border_radius=24,
                    bgcolor=Colors.PRIMARY_CONTAINER, alignment=ft.Alignment.CENTER,
                ),
                ft.Container(
                    width=12, height=12,
                    bgcolor=Colors.TERTIARY,
                    border_radius=6,
                    border=ft.Border.all(2, Colors.SURFACE_CONTAINER),
                    right=0, bottom=0,
                ),
            ],
            width=48, height=48,
        )
        profile_header = ft.Container(
            content=ft.Row(
                controls=[
                    profile_avatar,
                    ft.Column(
                        controls=[
                            self._profile_name_text,
                            ft.Text("Online", size=FontSize.BODY_MD,
                                    color=Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=16, right=16, top=24, bottom=8),
        )

        dm_block = ft.Column(
            controls=[
                self._section_label(
                    "DIRECT MESSAGES",
                    trailing=ft.Icon(ft.Icons.ADD, color=Colors.OUTLINE, size=16),
                ),
                *[self._dm_row(dm) for dm in _DMS],
            ],
            spacing=0,
        )

        settings_row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS, color=Colors.ON_SURFACE_VARIANT, size=20),
                    ft.Text("Settings", size=FontSize.BODY_MD,
                            color=Colors.ON_SURFACE_VARIANT),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=Radius.FULL,
            ink=True,
        )

        sign_out_row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.LOGOUT, color=Colors.ERROR, size=20),
                    ft.Text("Sign Out", size=FontSize.BODY_MD, color=Colors.ERROR),
                ],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            border_radius=Radius.FULL,
            ink=True,
            on_click=self._on_sign_out,
        )

        channels_panel = ft.Column(
            controls=[
                profile_header,
                self._channels_col,
                ft.Container(height=8),
                dm_block,
                ft.Container(height=8),
                ft.Divider(color=Colors.OUTLINE_VARIANT, height=1, thickness=1),
                settings_row,
                sign_out_row,
            ],
            spacing=0,
            expand=True,
        )

        drawer_body = ft.Container(
            height=900,
            padding=ft.Padding.all(0),
            content=ft.Row(
                controls=[self._server_rail(), channels_panel],
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

        return ft.NavigationDrawer(
            bgcolor=Colors.SURFACE_CONTAINER,
            tile_padding=ft.Padding.all(0),
            controls=[drawer_body],
        )

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    async def _on_burger_tap(self, e: ft.ControlEvent) -> None:
        await self._view.show_drawer()

    async def _on_typing(self, e: ft.ControlEvent) -> None:
        """
        Fires on every keystroke in the input field.
        Debounced to _TYPING_DEBOUNCE seconds using a monotonic clock so we
        never flood Redis with one pub/sub publish per character.
        """
        if not self._input_field.value or self._active_channel_id is None:
            return

        now = time.monotonic()
        if now - self._last_typing_sent < _TYPING_DEBOUNCE:
            return
        self._last_typing_sent = now

        user_id = self._page.session.store.get("user_id")
        if not user_id:
            return

        try:
            await database.publish_typing(
                self._active_channel_id,
                {
                    "user_id":   int(user_id),
                    "full_name": self._profile_name_text.value or "Unknown",
                    "is_typing": True,
                },
            )
        except Exception:
            pass

    async def _on_send(self, e: ft.ControlEvent) -> None:
        text = self._input_field.value.strip()
        if not text or self._active_channel_id is None:
            return

        user_id = self._page.session.store.get("user_id")
        if not user_id:
            self._page.navigate("/login")
            return

        # Clear immediately for snappy UX; restore on failure
        self._input_field.value = ""
        self._input_field.update()

        try:
            msg = await database.insert_message(
                channel_id=self._active_channel_id,
                sender_id=int(user_id),
                text_content=text,
            )
            self._append_message(msg)
            self._message_list.update()
            await database.publish_message(self._active_channel_id, msg)
        except Exception:
            self._input_field.value = text
            self._input_field.update()

    async def _on_sign_out(self, e: ft.ControlEvent) -> None:
        token = self._page.session.store.get("session_token")
        if token:
            await database.delete_session(token)

        self._page.session.store.remove("user_id")
        self._page.session.store.remove("session_token")

        for task in (self._listener_task, self._typing_task, self._prune_task):
            if task is not None:
                task.cancel()

        self._page.navigate("/login")

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def build(self) -> ft.View:
        appbar = ft.AppBar(
            leading=self._icon_btn(ft.Icons.MENU, color=Colors.PRIMARY,
                                   on_click=self._on_burger_tap),
            leading_width=48,
            title=self._channel_title,
            center_title=False,
            bgcolor=Colors.SURFACE_CONTAINER,
            toolbar_height=56,
            actions=[
                self._icon_btn(ft.Icons.SEARCH),
                self._icon_btn(ft.Icons.MORE_VERT, right_margin=8),
            ],
        )

        # Fixed-height typing bar sits between messages and input.
        # Always rendered (no layout jump) — empty text when nobody is typing.
        typing_bar = ft.Container(
            content=self._typing_label,
            padding=ft.Padding(left=20, right=16, top=4, bottom=0),
            height=22,
            bgcolor=Colors.SURFACE_CONTAINER,
        )

        self._view = ft.View(
            route="/hub",
            appbar=appbar,
            drawer=self._drawer,
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.all(0),
            controls=[
                ft.Column(
                    controls=[
                        self._message_list,
                        typing_bar,
                        self._build_input_bar(),
                    ],
                    spacing=0,
                    expand=True,
                )
            ],
        )

        self._page.run_task(self._initialize)
        return self._view


async def chat_hub_view(page: ft.Page) -> ft.View:
    return ChatHubView(page).build()
