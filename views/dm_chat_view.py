import flet as ft

from theme import Colors, Radius, Spacing, FontSize, FontWeight


class DmChatView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._input_field = ft.TextField(
            hint_text="Message Hamza...",
            hint_style=ft.TextStyle(color=Colors.ON_SURFACE_VARIANT,
                                    size=FontSize.BODY_MD),
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            text_size=FontSize.BODY_MD,
            color=Colors.ON_SURFACE,
            cursor_color=Colors.PRIMARY,
            expand=True,
        )

    # ── message builders ─────────────────────────────────────────────── #

    def _outgoing_image_msg(self) -> ft.Container:
        """Right-aligned image placeholder with timestamp + read-receipt overlay."""
        overlay = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("10:42 AM", size=10, color="#ffffff",
                            weight=FontWeight.MEDIUM),
                    ft.Icon(ft.Icons.DONE_ALL, color=Colors.PRIMARY, size=14),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#66000000",
            border_radius=Radius.FULL,
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
            bottom=8, right=8,
        )

        img_placeholder = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.IMAGE, color=Colors.OUTLINE_VARIANT, size=48),
                    ft.Text("Workspace photo", size=FontSize.LABEL_LG,
                            color=Colors.OUTLINE_VARIANT,
                            text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=280, height=160,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=Radius.DEFAULT,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            alignment=ft.Alignment.CENTER,
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Stack(
                        controls=[img_placeholder, overlay],
                        width=280, height=160,
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _incoming_file_msg(self) -> ft.Container:
        """Left-aligned PDF attachment card."""
        file_card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.PICTURE_AS_PDF,
                                        color=Colors.ERROR, size=24),
                        width=40, height=40,
                        bgcolor=Colors.ERROR + "33",
                        border_radius=20,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Project_Requirements.pdf",
                                    size=FontSize.BODY_MD,
                                    weight=FontWeight.MEDIUM,
                                    color=Colors.ON_SURFACE,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text("4.2 MB", size=FontSize.LABEL_SM,
                                    color=Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.Icons.DOWNLOAD,
                                        color=Colors.ON_SURFACE_VARIANT, size=20),
                        padding=ft.Padding.all(8),
                        border_radius=Radius.FULL,
                        ink=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.all(10),
            bgcolor=Colors.SURFACE_CONTAINER,
            border_radius=Radius.DEFAULT,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
        )

        bubble = ft.Container(
            content=ft.Column(
                controls=[
                    file_card,
                    ft.Container(height=6),
                    ft.Row(
                        controls=[
                            ft.Text("10:45 AM", size=10,
                                    color=Colors.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=0,
            ),
            padding=ft.Padding.all(12),
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=ft.BorderRadius(
                top_left=0, top_right=Radius.DEFAULT,
                bottom_left=Radius.DEFAULT, bottom_right=Radius.DEFAULT,
            ),
            width=300,
        )

        return ft.Container(
            content=ft.Row(controls=[bubble], alignment=ft.MainAxisAlignment.START),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _incoming_link_msg(self) -> ft.Container:
        """Left-aligned text bubble followed by a link preview card."""
        text_bubble = ft.Container(
            content=ft.Text(
                "Check out the documentation for Flet, it looks promising: flet.dev/docs",
                size=FontSize.BODY_MD,
                color=Colors.ON_SURFACE,
            ),
            padding=ft.Padding.all(12),
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border_radius=ft.BorderRadius(
                top_left=0, top_right=Radius.DEFAULT,
                bottom_left=Radius.DEFAULT, bottom_right=Radius.DEFAULT,
            ),
            width=300,
        )

        link_preview = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.LANGUAGE,
                                                color=Colors.PRIMARY, size=14),
                                        ft.Text("FLET.DEV", size=11,
                                                color=Colors.PRIMARY,
                                                weight=FontWeight.BOLD),
                                    ],
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Container(height=4),
                                ft.Text("Flet Docs - Build Flutter apps in Python",
                                        size=FontSize.BODY_MD,
                                        weight=FontWeight.SEMIBOLD,
                                        color=Colors.ON_SURFACE),
                                ft.Container(height=4),
                                ft.Text(
                                    "Flet enables developers to easily build "
                                    "real-time web, mobile and desktop apps in Python.",
                                    size=FontSize.LABEL_LG,
                                    color=Colors.ON_SURFACE_VARIANT,
                                    max_lines=2,
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=ft.Padding.all(12),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.Icons.CODE, color=Colors.PRIMARY, size=32),
                        width=72,
                        bgcolor=Colors.SURFACE_CONTAINER,
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            border=ft.Border(
                left=ft.BorderSide(4, Colors.PRIMARY),
                top=ft.BorderSide(1, Colors.OUTLINE_VARIANT),
                right=ft.BorderSide(1, Colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, Colors.OUTLINE_VARIANT),
            ),
            border_radius=Radius.DEFAULT,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            bgcolor=Colors.SURFACE_CONTAINER,
            width=300,
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            text_bubble,
                            ft.Container(height=6),
                            link_preview,
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Text("10:48 AM", size=10,
                                            color=Colors.ON_SURFACE_VARIANT),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ],
                        spacing=0,
                    )
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    def _typing_indicator(self) -> ft.Container:
        dots = ft.Row(
            controls=[
                ft.Container(width=7, height=7, bgcolor=Colors.TERTIARY, border_radius=4),
                ft.Container(width=7, height=7, bgcolor=Colors.TERTIARY,
                             border_radius=4, opacity=0.55),
                ft.Container(width=7, height=7, bgcolor=Colors.TERTIARY,
                             border_radius=4, opacity=0.25),
            ],
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=dots,
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                        bgcolor=Colors.SURFACE_CONTAINER,
                        border_radius=Radius.FULL,
                        border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
                    ),
                    ft.Text("Hamza is typing",
                            size=FontSize.LABEL_SM,
                            color=Colors.TERTIARY,
                            italic=True,
                            opacity=0.75),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16),
        )

    # ── input area ───────────────────────────────────────────────────── #

    def _build_quick_strip(self) -> ft.Container:
        def _action(icon: str, label: str,
                    icon_color: str, bg: str, border: str) -> ft.Column:
            return ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(icon, color=icon_color, size=20),
                        width=40, height=40,
                        border_radius=20,
                        bgcolor=bg,
                        border=ft.Border.all(1, border),
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                    ),
                    ft.Text(label, size=9, weight=FontWeight.MEDIUM,
                            color=icon_color),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )

        return ft.Container(
            content=ft.Row(
                controls=[
                    _action(ft.Icons.PHOTO_CAMERA, "CAMERA",
                            Colors.PRIMARY, Colors.PRIMARY_CONTAINER + "22",
                            Colors.PRIMARY + "44"),
                    _action(ft.Icons.IMAGE, "GALLERY",
                            "#b9c7e0", "#3c4a5e33", "#3c4a5e66"),
                    _action(ft.Icons.MIC, "AUDIO",
                            Colors.TERTIARY, Colors.TERTIARY + "22",
                            Colors.TERTIARY + "44"),
                ],
                spacing=20,
            ),
            padding=ft.Padding(left=8, right=8, top=4, bottom=8),
        )

    def _build_input_bar(self) -> ft.Container:
        pill = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE,
                                        color=Colors.ON_SURFACE_VARIANT, size=22),
                        padding=ft.Padding.symmetric(horizontal=6),
                    ),
                    self._input_field,
                    ft.Container(
                        content=ft.Icon(ft.Icons.MOOD,
                                        color=Colors.ON_SURFACE_VARIANT, size=22),
                        padding=ft.Padding.symmetric(horizontal=6),
                    ),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            height=48,
            bgcolor=Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.FULL,
        )

        send_btn = ft.Container(
            content=ft.Icon(ft.Icons.SEND, color=Colors.ON_PRIMARY, size=20),
            width=48, height=48,
            bgcolor=Colors.PRIMARY,
            border_radius=Radius.FULL,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self._on_send,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    self._build_quick_strip(),
                    ft.Row(
                        controls=[pill, send_btn],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border=ft.Border(top=ft.BorderSide(1, Colors.OUTLINE_VARIANT)),
        )

    # ── event handlers ───────────────────────────────────────────────── #

    async def _on_back(self, e: ft.ControlEvent) -> None:
        self._page.navigate("/dms")

    async def _on_send(self, e: ft.ControlEvent) -> None:
        text = self._input_field.value.strip()
        if not text:
            return
        self._input_field.value = ""
        self._input_field.update()

    # ── build ─────────────────────────────────────────────────────────── #

    def build(self) -> ft.View:
        def _icon_btn(icon: str, on_click=None) -> ft.Container:
            return ft.Container(
                content=ft.Icon(icon, color=Colors.ON_SURFACE_VARIANT, size=22),
                width=40, height=40,
                border_radius=Radius.FULL,
                ink=True,
                on_click=on_click,
            )

        hamza_avatar = ft.Stack(
            controls=[
                ft.Container(
                    content=ft.Text("H", size=FontSize.LABEL_LG,
                                    weight=FontWeight.BOLD, color=Colors.ON_SURFACE),
                    width=40, height=40,
                    border_radius=20,
                    bgcolor=Colors.SURFACE_CONTAINER_HIGH,
                    border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(
                    width=10, height=10,
                    bgcolor=Colors.TERTIARY,
                    border_radius=5,
                    border=ft.Border.all(2, Colors.BACKGROUND),
                    right=0, bottom=0,
                ),
            ],
            width=40, height=40,
        )

        title_widget = ft.Row(
            controls=[
                hamza_avatar,
                ft.Column(
                    controls=[
                        ft.Text("Hamza", size=FontSize.TITLE_LG,
                                weight=FontWeight.SEMIBOLD,
                                color=Colors.ON_SURFACE,
                                height=22),
                        ft.Text("Active now", size=FontSize.LABEL_SM,
                                color=Colors.TERTIARY,
                                height=16),
                    ],
                    spacing=0,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        appbar = ft.AppBar(
            leading=_icon_btn(ft.Icons.ARROW_BACK, on_click=self._on_back),
            leading_width=48,
            title=title_widget,
            center_title=False,
            bgcolor=Colors.BACKGROUND,
            toolbar_height=56,
            actions=[
                _icon_btn(ft.Icons.CALL),
                _icon_btn(ft.Icons.VIDEOCAM),
                _icon_btn(ft.Icons.MORE_VERT),
            ],
        )

        message_list = ft.ListView(
            controls=[
                ft.Container(height=8),
                self._outgoing_image_msg(),
                self._incoming_file_msg(),
                self._incoming_link_msg(),
                self._typing_indicator(),
                ft.Container(height=8),
            ],
            spacing=20,
            padding=ft.Padding(left=0, right=0, top=8, bottom=12),
            expand=True,
        )

        return ft.View(
            route="/dm",
            appbar=appbar,
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.all(0),
            controls=[
                ft.Column(
                    controls=[
                        message_list,
                        self._build_input_bar(),
                    ],
                    spacing=0,
                    expand=True,
                )
            ],
        )


async def dm_chat_view(page: ft.Page) -> ft.View:
    return DmChatView(page).build()
