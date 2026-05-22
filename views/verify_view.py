import asyncio

import flet as ft
import pyotp

import database
from theme import Colors, Radius, Spacing, FontSize, FontWeight

_BOX_COUNT = 6


class VerifyView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._countdown = 45

        self._boxes = [self._make_otp_box(i) for i in range(_BOX_COUNT)]

        self._timer_val = ft.Text(
            "0:45",
            size=FontSize.LABEL_LG,
            weight=FontWeight.BOLD,
            color=Colors.PRIMARY,
        )
        self._resend_pill = self._build_timer_pill()

    # ------------------------------------------------------------------ #
    #  OTP box factory                                                     #
    # ------------------------------------------------------------------ #

    def _make_otp_box(self, index: int) -> ft.TextField:
        async def _on_change(e: ft.ControlEvent) -> None:
            await self._on_digit(e, index)

        return ft.TextField(
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=1,
            fill_color=Colors.SURFACE_CONTAINER,
            border=ft.InputBorder.OUTLINE,
            border_color=Colors.OUTLINE_VARIANT,
            focused_border_color=Colors.PRIMARY,
            border_radius=Radius.DEFAULT,
            border_width=1,
            focused_border_width=2,
            color=Colors.ON_SURFACE,
            text_size=FontSize.TITLE_LG,   # smaller than 4-box version to fit 6
            cursor_color=Colors.PRIMARY,
            width=44,
            height=56,
            content_padding=ft.Padding.symmetric(horizontal=0, vertical=12),
            on_change=_on_change,
        )

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #

    def _build_back_button(self) -> ft.Container:
        return ft.Container(
            content=ft.Icon(ft.Icons.ARROW_BACK, color=Colors.ON_SURFACE, size=22),
            width=40,
            height=40,
            border_radius=Radius.FULL,
            ink=True,
            on_click=self._on_back,
        )

    def _build_header(self) -> ft.Column:
        totp_secret = self._page.session.store.get("pending_totp_secret") or ""
        return ft.Column(
            controls=[
                ft.Text(
                    "Verify Your Account",
                    size=FontSize.HEADLINE_MOBILE,
                    weight=FontWeight.BOLD,
                    color=Colors.ON_SURFACE,
                ),
                ft.Container(height=8),
                ft.Text(
                    "Open Google Authenticator and enter the 6-digit code for this account.",
                    size=FontSize.BODY_MD,
                    color=Colors.ON_SURFACE_VARIANT,
                    max_lines=3,
                ),
                ft.Container(height=16),
                self._build_secret_card(totp_secret),
            ],
            spacing=0,
        )

    def _build_secret_card(self, secret: str) -> ft.Container:
        """Shows the TOTP secret the user must add to Google Authenticator."""
        if not secret:
            return ft.Container(height=0)

        # Format as groups of 4: ABCD EFGH IJKL...
        grouped = " ".join(secret[i:i+4] for i in range(0, len(secret), 4))
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCK, color=Colors.PRIMARY, size=14),
                            ft.Text(
                                "Add this key to Google Authenticator",
                                size=FontSize.LABEL_LG,
                                color=Colors.ON_SURFACE_VARIANT,
                                weight=FontWeight.MEDIUM,
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        grouped,
                        size=FontSize.BODY_MD,
                        weight=FontWeight.BOLD,
                        color=Colors.PRIMARY,
                        selectable=True,
                    ),
                ],
                spacing=0,
            ),
            padding=ft.Padding.all(14),
            bgcolor=Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
        )

    def _build_otp_row(self) -> ft.Row:
        return ft.Row(
            controls=self._boxes,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=0,
        )

    def _build_timer_pill(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.SCHEDULE, color=Colors.ON_SURFACE_VARIANT, size=14),
                    ft.Text(
                        "Resend code in ",
                        size=FontSize.LABEL_LG,
                        color=Colors.ON_SURFACE_VARIANT,
                    ),
                    self._timer_val,
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            border_radius=Radius.FULL,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
        )

    def _build_hint_text(self) -> ft.Text:
        return ft.Text(
            "Facing issues? Check your network or try again in a few minutes.",
            size=FontSize.LABEL_LG,
            color=Colors.ON_SURFACE_VARIANT,
            italic=True,
            opacity=0.45,
            text_align=ft.TextAlign.CENTER,
        )

    def _build_verify_button(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(
                        "Verify & Enter",
                        size=FontSize.TITLE_LG,
                        weight=FontWeight.SEMIBOLD,
                        color=Colors.ON_PRIMARY,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=Colors.ON_PRIMARY, size=22),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            height=56,
            bgcolor=Colors.PRIMARY,
            border_radius=Radius.FULL,
            on_click=self._on_verify,
            ink=True,
        )

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    async def _on_digit(self, e: ft.ControlEvent, index: int) -> None:
        val = e.control.value
        # Clear any previous error styling on edit
        if e.control.error:
            e.control.error = None
            e.control.update()
        if val == "" and index > 0:
            await self._boxes[index - 1].focus()
        elif val != "" and index < _BOX_COUNT - 1:
            await self._boxes[index + 1].focus()

    async def _on_back(self, e: ft.ControlEvent) -> None:
        self._page.navigate("/login")

    async def _on_verify(self, e: ft.ControlEvent) -> None:
        code = "".join(b.value or "" for b in self._boxes)

        if len(code) < _BOX_COUNT:
            for box in self._boxes:
                if not box.value:
                    box.error = " "
                    box.update()
            return

        pending_id = self._page.session.store.get("pending_user_id")
        if not pending_id:
            self._page.navigate("/register")
            return

        try:
            user = await database.get_user_by_id(int(pending_id))
        except Exception:
            self._page.show_dialog(
                ft.SnackBar(ft.Text("Connection error. Please try again."))
            )
            return

        if user is None:
            self._page.navigate("/register")
            return

        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(code, valid_window=1):
            for box in self._boxes:
                box.error = " "
                box.update()
            self._page.show_dialog(
                ft.SnackBar(ft.Text("Invalid code — check your Authenticator app."))
            )
            return

        try:
            await database.mark_verified(int(pending_id))
            token = await database.create_session(int(pending_id))
        except Exception:
            self._page.show_dialog(
                ft.SnackBar(ft.Text("Verification failed. Please try again."))
            )
            return

        self._page.session.store.set("user_id", pending_id)
        self._page.session.store.set("session_token", token)
        self._page.session.store.remove("pending_user_id")
        self._page.session.store.remove("pending_totp_secret")

        self._page.navigate("/hub")

    async def _on_resend(self, e: ft.ControlEvent) -> None:
        pass  # TODO: re-request TOTP secret via email/SMS link

    async def _start_countdown(self) -> None:
        while self._countdown > 0:
            await asyncio.sleep(1)
            self._countdown -= 1
            m, s = divmod(self._countdown, 60)
            self._timer_val.value = f"{m}:{s:02d}"
            self._timer_val.update()

        self._resend_pill.content = ft.Text(
            "Resend OTP Now",
            size=FontSize.LABEL_LG,
            weight=FontWeight.BOLD,
            color=Colors.TERTIARY,
        )
        self._resend_pill.on_click = self._on_resend
        self._resend_pill.ink = True
        self._resend_pill.update()

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def build(self) -> ft.View:
        self._page.run_task(self._start_countdown)
        return ft.View(
            route="/verify",
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.symmetric(horizontal=Spacing.H_MARGIN),
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(height=48),
                        self._build_back_button(),
                        ft.Container(height=28),
                        self._build_header(),
                        ft.Container(height=36),
                        self._build_otp_row(),
                        ft.Container(height=24),
                        ft.Row(
                            controls=[self._resend_pill],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Container(height=16),
                        ft.Row(
                            controls=[self._build_hint_text()],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Container(height=64),
                        self._build_verify_button(),
                        ft.Container(height=32),
                    ],
                    spacing=0,
                )
            ],
        )


async def verify_view(page: ft.Page) -> ft.View:
    return VerifyView(page).build()
