import asyncio

import flet as ft
import pyotp

import database
from theme import Colors, Radius, Spacing, FontSize, FontWeight

_BOX_COUNT = 6


class VerifyView:
    """
    Hidden-input OTP pattern:
      ONE invisible ft.TextField is the single source of truth.
      SIX ft.Container boxes are purely visual read-only displays.

    Tapping anywhere on the grid area hits the invisible TextField (opacity=0
    still absorbs pointer events in Flutter), opens the numeric keyboard, and
    on_change fans each digit to the corresponding visual box.

    Auto-submit fires when the hidden field reaches exactly 6 digits.
    Clipboard paste drops the whole code in at once via ft.Clipboard().get().

    No "Resend" button — TOTP codes regenerate automatically in Google
    Authenticator every 30 seconds. There is nothing to resend.
    """

    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._verifying = False

        # ── Single hidden source-of-truth input ──────────────────────── #
        self._hidden = ft.TextField(
            max_length=_BOX_COUNT,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_change,
            color=Colors.BACKGROUND,
            bgcolor=Colors.BACKGROUND,
            border=ft.InputBorder.NONE,
            cursor_color=Colors.BACKGROUND,
            content_padding=ft.Padding.all(0),
        )

        # ── Six read-only visual display boxes ───────────────────────── #
        self._boxes = [self._make_box() for _ in range(_BOX_COUNT)]

    # ── Visual box factory ───────────────────────────────────────────── #

    def _make_box(self) -> ft.Container:
        return ft.Container(
            content=ft.Text(
                "",
                size=FontSize.TITLE_LG,
                weight=FontWeight.BOLD,
                color=Colors.ON_SURFACE,
                text_align=ft.TextAlign.CENTER,
            ),
            width=44,
            height=56,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
            bgcolor=Colors.SURFACE_CONTAINER,
            alignment=ft.Alignment.CENTER,
        )

    # ── Box sync helpers ─────────────────────────────────────────────── #

    def _sync_boxes(self, raw: str) -> None:
        n = len(raw)
        for i, box in enumerate(self._boxes):
            box.content.value = raw[i] if i < n else ""

            if i < n:
                box.border = ft.Border.all(2, Colors.PRIMARY)
            elif i == n and n > 0:
                box.border = ft.Border.all(2, Colors.PRIMARY)
            else:
                box.border = ft.Border.all(1, Colors.OUTLINE_VARIANT)

            box.update()

    def _error_boxes(self) -> None:
        for box in self._boxes:
            box.border = ft.Border.all(2, Colors.ERROR)
            box.update()

    # ── Core event handlers ──────────────────────────────────────────── #

    async def _on_change(self, e: ft.ControlEvent) -> None:
        raw = "".join(c for c in (e.control.value or "") if c.isdigit())[:_BOX_COUNT]

        if raw != (e.control.value or ""):
            e.control.value = raw
            e.control.update()

        self._sync_boxes(raw)

        if len(raw) == _BOX_COUNT and not self._verifying:
            await self._submit(raw)

    async def _on_paste(self, e: ft.ControlEvent) -> None:
        try:
            text = await ft.Clipboard().get() or ""
        except Exception:
            text = ""

        digits = "".join(c for c in text if c.isdigit())[:_BOX_COUNT]
        if not digits:
            self._page.show_dialog(
                ft.SnackBar(ft.Text("No numeric code found in clipboard."))
            )
            return

        self._hidden.value = digits
        self._hidden.update()
        self._sync_boxes(digits)

        if len(digits) == _BOX_COUNT and not self._verifying:
            await self._submit(digits)

    async def _on_back(self, e: ft.ControlEvent) -> None:
        self._page.navigate("/login")

    # ── Verification logic ────────────────────────────────────────────── #

    async def _submit(self, raw: str) -> None:
        if self._verifying:
            return
        self._verifying = True

        pending_id = self._page.session.store.get("pending_user_id")
        if not pending_id:
            self._page.navigate("/register")
            return

        try:
            user = await database.get_user_by_id(int(pending_id))
        except Exception as exc:
            self._page.show_dialog(
                ft.SnackBar(ft.Text(f"DB error: {exc}"))
            )
            self._verifying = False
            return

        if user is None:
            self._page.navigate("/register")
            return

        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(raw, valid_window=1):
            self._error_boxes()
            self._page.show_dialog(
                ft.SnackBar(ft.Text("Invalid code — check your Authenticator app."))
            )
            await asyncio.sleep(0.6)
            self._hidden.value = ""
            self._hidden.update()
            self._sync_boxes("")
            self._verifying = False
            return

        try:
            await database.mark_verified(int(pending_id))
            token = await database.create_session(int(pending_id))
        except Exception as exc:
            self._page.show_dialog(
                ft.SnackBar(ft.Text(f"Session error: {exc}"))
            )
            self._verifying = False
            return

        self._page.session.store.set("user_id", pending_id)
        self._page.session.store.set("session_token", token)
        self._page.session.store.remove("pending_user_id")
        self._page.session.store.remove("pending_totp_secret")

        self._page.navigate("/hub")

    # ── Section builders ──────────────────────────────────────────────── #

    def _build_header(self) -> ft.Column:
        totp_secret = self._page.session.store.get("pending_totp_secret") or ""
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.VERIFIED_USER,
                                    color=Colors.ON_PRIMARY_CONTAINER, size=26),
                    width=52, height=52,
                    bgcolor=Colors.PRIMARY_CONTAINER,
                    border_radius=Radius.DEFAULT,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=20),
                ft.Text("Verify Your Account",
                        size=FontSize.HEADLINE_MOBILE,
                        weight=FontWeight.BOLD,
                        color=Colors.ON_SURFACE),
                ft.Container(height=8),
                ft.Text(
                    "Open Google Authenticator and enter the 6-digit code "
                    "for this account.",
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
        if not secret:
            return ft.Container(height=0)

        grouped = " ".join(secret[i:i+4] for i in range(0, len(secret), 4))
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCK, color=Colors.PRIMARY, size=14),
                            ft.Text("Add this key to Google Authenticator",
                                    size=FontSize.LABEL_LG,
                                    color=Colors.ON_SURFACE_VARIANT,
                                    weight=FontWeight.MEDIUM),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Container(height=6),
                    ft.Text(grouped, size=FontSize.BODY_MD,
                            weight=FontWeight.BOLD,
                            color=Colors.PRIMARY,
                            selectable=True),
                ],
                spacing=0,
            ),
            padding=ft.Padding.all(14),
            bgcolor=Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
        )

    def _build_otp_grid(self) -> ft.Column:
        visual_row = ft.Row(
            controls=self._boxes,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=0,
        )

        hidden_overlay = ft.Container(
            content=self._hidden,
            opacity=0,
            left=0,
            top=0,
            right=0,
            bottom=0,
        )

        otp_stack = ft.Stack(
            controls=[visual_row, hidden_overlay],
            height=56,
        )

        paste_btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CONTENT_PASTE,
                            color=Colors.ON_SURFACE_VARIANT, size=16),
                    ft.Text("Paste from Clipboard",
                            size=FontSize.LABEL_LG,
                            color=Colors.ON_SURFACE_VARIANT,
                            weight=FontWeight.MEDIUM),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=40,
            border_radius=Radius.FULL,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            ink=True,
            on_click=self._on_paste,
            padding=ft.Padding.symmetric(horizontal=16, vertical=0),
        )

        return ft.Column(
            controls=[
                otp_stack,
                ft.Container(height=24),
                ft.Row(
                    controls=[paste_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=0,
        )

    # ── Build ─────────────────────────────────────────────────────────── #

    def build(self) -> ft.View:
        return ft.View(
            route="/verify",
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.symmetric(horizontal=Spacing.H_MARGIN),
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(height=48),
                        ft.Container(
                            content=ft.Icon(ft.Icons.ARROW_BACK,
                                            color=Colors.ON_SURFACE, size=22),
                            width=40, height=40,
                            border_radius=Radius.FULL,
                            ink=True,
                            on_click=self._on_back,
                        ),
                        ft.Container(height=28),
                        self._build_header(),
                        ft.Container(height=36),
                        self._build_otp_grid(),
                        ft.Container(height=32),
                    ],
                    spacing=0,
                )
            ],
        )


async def verify_view(page: ft.Page) -> ft.View:
    return VerifyView(page).build()
