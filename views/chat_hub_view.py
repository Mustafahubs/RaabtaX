import asyncio
import json
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

# ── Placeholder DM data (not yet backed by a DM schema) ─────────────────── #

_DMS = [
    {"name": "Sarah Mitchell", "initials": "SM",
     "color": Colors.PRIMARY_CONTAINER, "online": True},
    {"name": "James Holden",   "initials": "JH",
     "color": Colors.SURFACE_CONTAINER_HIGH, "online": False},
]

# Consecutive messages within this many seconds from the same sender are grouped
_GROUP_WINDOW = 300


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
        self._listener_task: asyncio.Future | None = None

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
        Carries .data = {sender_id, timestamp} so the next call to
        _append_message can decide whether to group.
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
            # 20 px top gap opens a clear visual break between sender groups
            padding=ft.Padding(top=20, bottom=0, left=16, right=16),
            data={"sender_id": sender_id, "timestamp": _parse_ts(data.get("timestamp"))},
        )

    def _compact_message_row(self, data: dict) -> ft.Container:
        """
        Compact row: no avatar, no header — just the bubble(s) indented to
        align with the content column of the preceding full row.
        Avatar width (40) + gap (12) = 52 px left spacer.
        4 px top gap keeps the group tight without merging visually.
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
        Core append routine used by _load_messages, _listen_channel, and _on_send.

        Grouping algorithm (O(1)):
          1. Peek at controls[-1].data — a dict with sender_id + timestamp.
          2. If same sender_id AND delta < _GROUP_WINDOW seconds → compact row.
          3. Otherwise → full row.

        Also strips the 'no messages' placeholder on the first real message.
        Separators (ft.Row, data=None) intentionally break grouping because
        isinstance(None, dict) is False.
        """
        controls = self._message_list.controls

        # Remove placeholder — identified as a Container whose .data is not a sender dict
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
            # data intentionally absent — grouping never fires after a separator
        )

    def _empty_placeholder(self, label: str) -> ft.Container:
        # No data= key → .data is None → identified as placeholder by _append_message
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
            spacing=0,   # all spacing is controlled per-row via Container.padding
            padding=ft.Padding(left=0, right=0, top=16, bottom=88),
            expand=True,
        )

    # ------------------------------------------------------------------ #
    #  Async initialization & live data pipeline                           #
    # ------------------------------------------------------------------ #

    async def _initialize(self) -> None:
        """
        Runs once after build() via page.run_task().

        1. Auth-guards /hub — bounces unauthenticated requests to /login.
        2. Hydrates the profile header with the real user's name.
        3. Sets presence in Redis.
        4. Fetches channels; seeds defaults if empty.
        5. Loads the first channel's messages.
        6. Starts the Redis pub/sub listener.
        7. Starts the presence heartbeat.
        """
        # ── Auth guard ───────────────────────────────────────────────── #
        user_id_str = self._page.session.store.get("user_id")
        if not user_id_str:
            self._page.navigate("/login")
            return
        user_id = int(user_id_str)

        # ── Hydrate profile header ───────────────────────────────────── #
        try:
            user = await database.get_user_by_id(user_id)
            if user:
                name = user["full_name"]
                self._profile_name_text.value    = name
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

        # ── Initial message load ─────────────────────────────────────── #
        if self._active_channel_id is not None:
            await self._load_messages(self._active_channel_id)
            self._start_listener(self._active_channel_id)

        # ── Presence heartbeat ───────────────────────────────────────── #
        self._page.run_task(self._presence_loop, user_id)

    async def _load_messages(self, channel_id: int) -> None:
        """
        Replace the ListView contents with the last 50 messages from Postgres.
        Date separators are injected at day boundaries.
        Each message is routed through _append_message for grouping.
        """
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

    def _start_listener(self, channel_id: int) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
        self._listener_task = self._page.run_task(self._listen_channel, channel_id)

    async def _listen_channel(self, channel_id: int) -> None:
        """
        Persistent Redis pub/sub loop. Runs until cancelled on channel switch
        or sign-out. Each inbound message goes through _append_message —
        no full list rebuild occurs.
        """
        pubsub = database.get_pubsub()
        try:
            await pubsub.subscribe(f"ch:{channel_id}")
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
            pass
        except Exception:
            pass
        finally:
            await pubsub.aclose()

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
            self._start_listener(channel_id)
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
        dot_color = Colors.TERTIARY if dm["online"] else Colors.OUTLINE_VARIANT
        avatar_stack = ft.Stack(
            controls=[
                self._avatar(dm["initials"], dm["color"], size=32),
                ft.Container(
                    width=10, height=10,
                    bgcolor=dot_color,
                    border_radius=5,
                    border=ft.Border.all(2, Colors.SURFACE_CONTAINER),
                    right=0, bottom=0,
                ),
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
            # Append our own message locally — pub/sub does not echo back to sender
            self._append_message(msg)
            self._message_list.update()

            # Broadcast to every other connected client on this channel
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

        if self._listener_task is not None:
            self._listener_task.cancel()

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
