import flet as ft

from theme import Colors, Radius, Spacing, FontSize, FontWeight

_CAROUSEL = [
    {"name": "Alex",   "initials": "AR", "color": "#1a3a5c", "status": "online"},
    {"name": "Sarah",  "initials": "SC", "color": "#2d1b3a", "status": "dnd"},
    {"name": "Marcus", "initials": "MW", "color": "#1a2a3a", "status": "offline"},
    {"name": "Jamie",  "initials": "JL", "color": "#2a1a3a", "status": "online"},
    {"name": "Elena",  "initials": "EL", "color": "#1a3a2a", "status": "online"},
]

_CONVERSATIONS = [
    {
        "name": "Alex Rivers",   "initials": "AR", "color": "#1a3a5c",
        "status": "online",  "last_msg": "See you at 9 PM!",
        "time": "2m ago",    "unread": 3,
    },
    {
        "name": "Sarah Chen",    "initials": "SC", "color": "#2d1b3a",
        "status": "dnd",    "last_msg": "The files are ready.",
        "time": "15m ago",   "unread": 0,
    },
    {
        "name": "Marcus Wright", "initials": "MW", "color": "#1a2a3a",
        "status": "offline", "last_msg": "Thanks!",
        "time": "Yesterday", "unread": 0, "sent_by_me": True,
    },
    {
        "name": "Jamie L.",      "initials": "JL", "color": "#2a1a3a",
        "status": "online",  "last_msg": "Let's hop on the call later?",
        "time": "2h ago",    "unread": 0,
    },
]


class DirectMessagesHubView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._active_tab = 0
        self._tab_texts: list[ft.Text] = []
        self._tab_containers: list[ft.Container] = []

    # ── helpers ──────────────────────────────────────────────────────── #

    def _avatar(self, initials: str, color: str, size: int = 56) -> ft.Container:
        return ft.Container(
            content=ft.Text(initials, size=FontSize.LABEL_LG,
                            weight=FontWeight.BOLD, color=Colors.ON_SURFACE),
            width=size, height=size,
            border_radius=size / 2,
            bgcolor=color,
            alignment=ft.Alignment.CENTER,
        )

    def _status_dot(self, status: str, size: int = 12) -> ft.Container:
        if status == "dnd":
            return ft.Container(
                content=ft.Icon(ft.Icons.BEDTIME,
                                color=Colors.BACKGROUND, size=size - 4),
                width=size, height=size,
                bgcolor="#ffb74d",
                border_radius=size / 2,
                border=ft.Border.all(2, Colors.BACKGROUND),
                alignment=ft.Alignment.CENTER,
                right=0, bottom=0,
            )
        bgcolor = Colors.TERTIARY if status == "online" else Colors.OUTLINE_VARIANT
        return ft.Container(
            width=size, height=size,
            bgcolor=bgcolor,
            border_radius=size / 2,
            border=ft.Border.all(2, Colors.BACKGROUND),
            right=0, bottom=0,
        )

    def _avatar_with_dot(self, initials: str, color: str,
                         status: str, size: int = 56) -> ft.Stack:
        return ft.Stack(
            controls=[
                self._avatar(initials, color, size),
                self._status_dot(status, size=14),
            ],
            width=size, height=size,
        )

    # ── section builders ─────────────────────────────────────────────── #

    def _build_tab_bar(self) -> ft.Container:
        labels = ["All Chats", "Online (14)", "Requests (3)"]

        async def _tap(e: ft.ControlEvent, idx: int) -> None:
            self._active_tab = idx
            for i, (txt, con) in enumerate(zip(self._tab_texts, self._tab_containers)):
                active = (i == idx)
                txt.color = Colors.PRIMARY if active else Colors.ON_SURFACE_VARIANT
                con.border = (
                    ft.Border(bottom=ft.BorderSide(2, Colors.PRIMARY)) if active else None
                )
                txt.update()
                con.update()

        self._tab_texts = []
        self._tab_containers = []
        tabs: list[ft.Control] = []

        for i, label in enumerate(labels):
            active = (i == 0)
            txt = ft.Text(
                label,
                size=FontSize.LABEL_LG,
                weight=FontWeight.MEDIUM,
                color=Colors.PRIMARY if active else Colors.ON_SURFACE_VARIANT,
            )
            con = ft.Container(
                content=txt,
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                border=ft.Border(bottom=ft.BorderSide(2, Colors.PRIMARY)) if active else None,
                ink=True,
                on_click=lambda e, idx=i: _tap(e, idx),
            )
            self._tab_texts.append(txt)
            self._tab_containers.append(con)
            tabs.append(con)

        return ft.Container(
            content=ft.Row(controls=tabs, spacing=0),
            margin=ft.Margin(left=0, right=0, top=8, bottom=0),
        )

    def _build_carousel(self) -> ft.Container:
        items: list[ft.Control] = []
        for c in _CAROUSEL:
            items.append(
                ft.Column(
                    controls=[
                        ft.Stack(
                            controls=[
                                self._avatar(c["initials"], c["color"], size=64),
                                self._status_dot(c["status"], size=16),
                            ],
                            width=64, height=64,
                        ),
                        ft.Text(c["name"], size=FontSize.LABEL_LG,
                                color=Colors.ON_SURFACE_VARIANT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                )
            )
        return ft.Container(
            content=ft.Row(
                controls=items,
                spacing=24,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=24),
        )

    def _build_conversation_row(self, conv: dict) -> ft.Container:
        unread = conv.get("unread", 0)
        sent   = conv.get("sent_by_me", False)
        bold   = (unread > 0)

        if sent:
            msg_controls: list[ft.Control] = [
                ft.Icon(ft.Icons.DONE_ALL, color=Colors.PRIMARY, size=16),
                ft.Text(conv["last_msg"], size=FontSize.BODY_MD,
                        color=Colors.ON_SURFACE_VARIANT, expand=True,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ]
        else:
            msg_controls = [
                ft.Text(conv["last_msg"], size=FontSize.BODY_MD,
                        color=Colors.ON_SURFACE if bold else Colors.ON_SURFACE_VARIANT,
                        weight=FontWeight.SEMIBOLD if bold else None,
                        expand=True,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ]

        if unread > 0:
            msg_controls.append(
                ft.Container(
                    content=ft.Text(str(unread), size=10,
                                    weight=FontWeight.BOLD,
                                    color=Colors.ON_PRIMARY_CONTAINER),
                    width=20, height=20,
                    bgcolor=Colors.PRIMARY,
                    border_radius=10,
                    alignment=ft.Alignment.CENTER,
                )
            )

        time_color = Colors.TERTIARY if unread > 0 else Colors.ON_SURFACE_VARIANT

        async def _tap(e: ft.ControlEvent) -> None:
            self._page.navigate("/dm")

        return ft.Container(
            content=ft.Row(
                controls=[
                    self._avatar_with_dot(
                        conv["initials"], conv["color"], conv["status"], size=56
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(conv["name"],
                                            size=FontSize.TITLE_LG,
                                            weight=FontWeight.SEMIBOLD,
                                            color=Colors.ON_SURFACE,
                                            expand=True,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(conv["time"],
                                            size=FontSize.LABEL_SM,
                                            color=time_color),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Container(height=4),
                            ft.Row(
                                controls=msg_controls,
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            ink=True,
            on_click=_tap,
        )

    def _build_bottom_nav(self) -> ft.Container:
        def _item(icon: str, label: str, active: bool,
                  on_click=None) -> ft.Container:
            if active:
                return ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(icon, color=Colors.ON_PRIMARY_CONTAINER, size=22),
                            ft.Text(label, size=FontSize.LABEL_SM,
                                    color=Colors.ON_PRIMARY_CONTAINER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    bgcolor=Colors.PRIMARY_CONTAINER,
                    border_radius=12,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    width=72, height=44,
                    alignment=ft.Alignment.CENTER,
                    on_click=on_click,
                )
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(icon, color=Colors.ON_SURFACE_VARIANT, size=22),
                        ft.Text(label, size=FontSize.LABEL_SM,
                                color=Colors.ON_SURFACE_VARIANT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                width=72, height=44,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=on_click,
            )

        alerts_item = ft.Container(
            content=ft.Stack(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.NOTIFICATIONS,
                                    color=Colors.ON_SURFACE_VARIANT, size=22),
                            ft.Text("Alerts", size=FontSize.LABEL_SM,
                                    color=Colors.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    ),
                    ft.Container(
                        width=8, height=8,
                        bgcolor=Colors.ERROR,
                        border_radius=4,
                        right=8, top=0,
                    ),
                ],
                width=72, height=44,
            ),
            width=72, height=44,
            alignment=ft.Alignment.CENTER,
            ink=True,
        )

        async def _go_hub(e: ft.ControlEvent) -> None:
            self._page.navigate("/hub")

        return ft.Container(
            content=ft.Row(
                controls=[
                    _item(ft.Icons.CHAT, "Messages", active=True),
                    _item(ft.Icons.EXPLORE, "Servers", active=False,
                          on_click=_go_hub),
                    alerts_item,
                    _item(ft.Icons.PERSON_OUTLINE, "Profile", active=False),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=64,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border(top=ft.BorderSide(1, Colors.OUTLINE_VARIANT)),
            padding=ft.Padding.symmetric(horizontal=8),
        )

    # ── build ─────────────────────────────────────────────────────────── #

    def build(self) -> ft.View:
        def _icon_btn(icon: str, on_click=None) -> ft.Container:
            return ft.Container(
                content=ft.Icon(icon, color=Colors.PRIMARY, size=22),
                width=40, height=40,
                border_radius=Radius.FULL,
                ink=True,
                on_click=on_click,
            )

        appbar = ft.AppBar(
            leading=_icon_btn(ft.Icons.MENU),
            leading_width=48,
            title=ft.Text("Direct Messages",
                          size=FontSize.TITLE_LG,
                          weight=FontWeight.SEMIBOLD,
                          color=Colors.ON_SURFACE),
            center_title=True,
            bgcolor=Colors.SURFACE_CONTAINER,
            toolbar_height=56,
            actions=[_icon_btn(ft.Icons.PERSON_ADD)],
        )

        fab = ft.Container(
            content=ft.Icon(ft.Icons.CHAT, color=Colors.ON_PRIMARY, size=24),
            width=56, height=56,
            bgcolor=Colors.PRIMARY,
            border_radius=28,
            alignment=ft.Alignment.CENTER,
            ink=True,
            right=16,
            bottom=80,
            shadow=ft.BoxShadow(
                blur_radius=12,
                spread_radius=0,
                color="#44000000",
                offset=ft.Offset(0, 4),
            ),
        )

        body = ft.Column(
            controls=[
                self._build_carousel(),
                *[self._build_conversation_row(c) for c in _CONVERSATIONS],
                ft.Container(height=80),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.View(
            route="/dms",
            appbar=appbar,
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.all(0),
            controls=[
                ft.Column(
                    controls=[
                        self._build_tab_bar(),
                        ft.Stack(controls=[body, fab], expand=True),
                        self._build_bottom_nav(),
                    ],
                    spacing=0,
                    expand=True,
                )
            ],
        )


async def dms_view(page: ft.Page) -> ft.View:
    return DirectMessagesHubView(page).build()
