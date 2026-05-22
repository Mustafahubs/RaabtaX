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


def _fmt_time(ts) -> str:
    if ts is None:
        return ""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    h = ts.hour % 12 or 12
    return f"{h}:{ts.minute:02d} {'AM' if ts.hour < 12 else 'PM'}"


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

        # ── Mutable widgets updated in-place on switch ───────────────── #
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

    def _bubble(self, text: str, top_left_radius: int = 0) -> ft.Container:
        return ft.Container(
            content=ft.Text(text, size=FontSize.BODY_MD, color=Colors.ON_SURFACE),
            padding=ft.Padding.all(12),
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=ft.BorderRadius(
                top_left=top_left_radius,
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

    def _message_row_from_data(self, data: dict) -> ft.Control:
        sender_id   = data.get("sender_id", 0)
        full_name   = data.get("sender_full_name", "Unknown")
        avatar_bg   = _AVATAR_COLORS[sender_id % len(_AVATAR_COLORS)]
        author_col  = _AUTHOR_COLORS[sender_id % len(_AUTHOR_COLORS)]
        time_str    = _fmt_time(data.get("timestamp"))
        preview     = data.get("link_preview_payload")

        bubble_col: list[ft.Control] = [self._bubble(data.get("text_content", ""))]
        if isinstance(preview, dict):
            bubble_col += [ft.Container(height=6), self._link_preview_from_data(preview)]

        return ft.Row(
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
                        *bubble_col,
                    ],
                    spacing=4,
                ),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _separator(self, label: str) -> ft.Row:
        line = lambda: ft.Container(height=1, bgcolor=Colors.OUTLINE_VARIANT,
                                    expand=True, opacity=0.25)
        return ft.Row(
            controls=[line(), ft.Text(label, size=FontSize.LABEL_SM, color=Colors.OUTLINE), line()],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _empty_placeholder(self, label: str) -> ft.Container:
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
            spacing=20,
            padding=ft.Padding(left=16, right=16, top=16, bottom=88),
            expand=True,
        )

    # ------------------------------------------------------------------ #
    #  Async initialization & live data pipeline                           #
    # ------------------------------------------------------------------ #

    async def _initialize(self) -> None:
        """
        Runs once after build() via page.run_task().
        1. Set Redis presence key for the current user.
        2. Fetch channels from Postgres; seed defaults if empty.
        3. Populate the drawer channel list.
        4. Load the first channel's messages.
        5. Start the Redis pub/sub listener for live delivery.
        6. Start the presence refresh heartbeat.
        """
        # ── Presence ────────────────────────────────────────────────── #
        user_id = self._page.session.store.get("user_id")
        if user_id:
            try:
                await database.set_presence(int(user_id))
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
            self._channel_title.value     = f"# {self._active_channel}"
            self._input_field.hint_text   = f"Message # {self._active_channel}"
            self._channel_title.update()
            self._input_field.update()

        # ── Populate drawer channel column ───────────────────────────── #
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
        if user_id:
            self._page.run_task(self._presence_loop, int(user_id))

    async def _load_messages(self, channel_id: int) -> None:
        """Clear the ListView and populate it with the last 50 DB messages."""
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
            prev_sender: int | None = None
            for row in rows:
                # Date separator at day boundaries
                if prev_sender is None:
                    ts = row.get("timestamp")
                    if ts:
                        label = (ts.strftime("%-d %B %Y")
                                 if hasattr(ts, "strftime") else ts[:10])
                        self._message_list.controls.append(self._separator(label))

                self._message_list.controls.append(self._message_row_from_data(row))
                prev_sender = row.get("sender_id")

        self._message_list.update()

    def _start_listener(self, channel_id: int) -> None:
        """Cancel the previous Redis listener and start one for channel_id."""
        if self._listener_task is not None:
            self._listener_task.cancel()
        self._listener_task = self._page.run_task(self._listen_channel, channel_id)

    async def _listen_channel(self, channel_id: int) -> None:
        """
        Persistent Redis pub/sub loop for live message delivery.

        Runs until cancelled (on channel switch or view teardown).
        Each inbound message appends exactly one Control node to
        _message_list — no full list rebuild occurs.
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

                # Remove "no messages" placeholder on first live message
                if (
                    len(self._message_list.controls) == 1
                    and isinstance(self._message_list.controls[0], ft.Container)
                ):
                    self._message_list.controls.clear()

                self._message_list.controls.append(self._message_row_from_data(data))
                self._message_list.update()
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.aclose()

    async def _presence_loop(self, user_id: int) -> None:
        """Refresh the presence key every 4 minutes (TTL is 5 min)."""
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
        """Channel row wired to a DB channel_id; on-click triggers live data swap."""
        async def _tap(e: ft.ControlEvent) -> None:
            if self._active_channel_id == channel_id:
                await self._view.close_drawer()
                return

            # ── State update ──────────────────────────────────────────── #
            self._active_channel    = name
            self._active_channel_id = channel_id

            # ── In-place widget mutations (O(1), no list rebuild) ──────── #
            self._channel_title.value   = f"# {name}"
            self._input_field.hint_text = f"Message # {name}"
            self._channel_title.update()
            self._input_field.update()

            # ── Swap listener before closing drawer ───────────────────── #
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
        # ── Profile header ───────────────────────────────────────────── #
        profile_avatar = ft.Stack(
            controls=[
                ft.Container(
                    content=ft.Text("AC", size=FontSize.LABEL_LG,
                                    weight=FontWeight.BOLD,
                                    color=Colors.ON_PRIMARY_CONTAINER),
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
                            ft.Text("Alex Chen", size=FontSize.HEADLINE_MOBILE,
                                    weight=FontWeight.BOLD, color=Colors.PRIMARY),
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

        channels_panel = ft.Column(
            controls=[
                profile_header,
                self._channels_col,   # ← populated live by _initialize()
                ft.Container(height=8),
                dm_block,
                ft.Container(height=8),
                ft.Divider(color=Colors.OUTLINE_VARIANT, height=1, thickness=1),
                settings_row,
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
            return

        # Clear input immediately for snappy UX
        self._input_field.value = ""
        self._input_field.update()

        try:
            msg = await database.insert_message(
                channel_id=self._active_channel_id,
                sender_id=int(user_id),
                text_content=text,
            )
            # Remove placeholder if present
            if (
                len(self._message_list.controls) == 1
                and isinstance(self._message_list.controls[0], ft.Container)
            ):
                self._message_list.controls.clear()

            # Append our own message (pubsub won't echo back to sender)
            self._message_list.controls.append(self._message_row_from_data(msg))
            self._message_list.update()

            # Broadcast to all other connected clients via Redis
            await database.publish_message(self._active_channel_id, msg)
        except Exception:
            # Restore text if send failed
            self._input_field.value = text
            self._input_field.update()

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

        # Kick off async hydration after view is returned to the router
        self._page.run_task(self._initialize)

        return self._view


async def chat_hub_view(page: ft.Page) -> ft.View:
    return ChatHubView(page).build()
