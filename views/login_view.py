import secrets

import flet as ft
import bcrypt

import database
from theme import Colors, Radius, Spacing, FontSize, FontWeight


class LoginView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._email_field    = self._make_email_field()
        self._password_field = self._make_password_field()

    # ------------------------------------------------------------------ #
    #  Field factories                                                     #
    # ------------------------------------------------------------------ #

    def _make_email_field(self) -> ft.TextField:
        return ft.TextField(
            hint_text="example@flux.chat",
            hint_style=ft.TextStyle(color=Colors.OUTLINE_VARIANT, size=FontSize.BODY_LG),
            prefix_icon=ft.Icons.ALTERNATE_EMAIL,
            keyboard_type=ft.KeyboardType.EMAIL,
            # Background — fill_color triggers filled=True automatically
            fill_color=Colors.SURFACE_CONTAINER,
            border=ft.InputBorder.OUTLINE,
            border_color=Colors.OUTLINE_VARIANT,
            focused_border_color=Colors.PRIMARY,
            border_radius=Radius.DEFAULT,
            border_width=1,
            focused_border_width=1.5,
            color=Colors.ON_SURFACE,
            text_size=FontSize.BODY_LG,
            cursor_color=Colors.PRIMARY,
            # vertical=20 → total height ≈ 64px to match h-16 in design
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=20),
        )

    def _make_password_field(self) -> ft.TextField:
        return ft.TextField(
            hint_text="••••••••",
            hint_style=ft.TextStyle(color=Colors.OUTLINE_VARIANT, size=FontSize.BODY_LG),
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            fill_color=Colors.SURFACE_CONTAINER,
            border=ft.InputBorder.OUTLINE,
            border_color=Colors.OUTLINE_VARIANT,
            focused_border_color=Colors.PRIMARY,
            border_radius=Radius.DEFAULT,
            border_width=1,
            focused_border_width=1.5,
            color=Colors.ON_SURFACE,
            text_size=FontSize.BODY_LG,
            cursor_color=Colors.PRIMARY,
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=20),
        )

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #

    def _build_logo(self) -> ft.Container:
        return ft.Container(
            content=ft.Icon(ft.Icons.BLUR_ON, color=Colors.ON_PRIMARY_CONTAINER, size=34),
            width=68,
            height=68,
            bgcolor=Colors.PRIMARY_CONTAINER,
            border_radius=Radius.DEFAULT,
            alignment=ft.Alignment.CENTER,
        )

    def _build_header(self) -> ft.Column:
        return ft.Column(
            controls=[
                self._build_logo(),
                ft.Container(height=20),
                ft.Text(
                    "Welcome Back",
                    size=FontSize.HEADLINE_MOBILE,
                    weight=FontWeight.BOLD,
                    color=Colors.ON_SURFACE,
                ),
                ft.Container(height=6),
                ft.Text(
                    "Sign in to continue your secure conversations.",
                    size=FontSize.BODY_MD,
                    color=Colors.ON_SURFACE_VARIANT,
                    max_lines=2,
                ),
            ],
            spacing=0,
        )

    def _build_form(self) -> ft.Column:
        return ft.Column(
            controls=[
                # Email field
                ft.Text("Email or Phone Number",
                        size=FontSize.LABEL_LG,
                        weight=FontWeight.MEDIUM,
                        color=Colors.ON_SURFACE_VARIANT),
                ft.Container(height=6),
                self._email_field,

                ft.Container(height=20),

                # Password field
                ft.Text("Password",
                        size=FontSize.LABEL_LG,
                        weight=FontWeight.MEDIUM,
                        color=Colors.ON_SURFACE_VARIANT),
                ft.Container(height=6),
                self._password_field,

                ft.Container(height=6),

                # Forgot password — right aligned
                ft.Row(
                    controls=[
                        ft.Text(
                            "Forgot Password?",
                            size=FontSize.LABEL_LG,
                            color=Colors.PRIMARY,
                            weight=FontWeight.MEDIUM,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),

                ft.Container(height=28),
                self._build_login_button(),
            ],
            spacing=0,
        )

    def _build_login_button(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("Login",
                            size=FontSize.TITLE_LG,
                            weight=FontWeight.SEMIBOLD,
                            color=Colors.ON_PRIMARY_CONTAINER),
                    ft.Icon(ft.Icons.ARROW_FORWARD,
                            color=Colors.ON_PRIMARY_CONTAINER,
                            size=20),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            height=64,
            bgcolor=Colors.PRIMARY_CONTAINER,
            border_radius=Radius.DEFAULT,
            on_click=self._on_login,
            ink=True,
        )

    def _build_divider_row(self, label: str) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Container(
                    height=1,
                    bgcolor=Colors.OUTLINE_VARIANT,
                    expand=True,
                    opacity=0.35,
                ),
                ft.Text(label,
                        size=FontSize.LABEL_SM,
                        color=Colors.ON_SURFACE_VARIANT,
                        weight=FontWeight.MEDIUM),
                ft.Container(
                    height=1,
                    bgcolor=Colors.OUTLINE_VARIANT,
                    expand=True,
                    opacity=0.35,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_google_button(self) -> ft.Container:
        """Google button with branded 'G' circle approximation."""
        google_g = ft.Container(
            content=ft.Text("G", size=13, weight=FontWeight.BOLD, color="#FFFFFF"),
            width=22,
            height=22,
            bgcolor="#4285F4",
            border_radius=11,
            alignment=ft.Alignment.CENTER,
        )
        return ft.Container(
            content=ft.Row(
                controls=[
                    google_g,
                    ft.Text("Google",
                            size=FontSize.LABEL_LG,
                            weight=FontWeight.MEDIUM,
                            color=Colors.ON_SURFACE),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            height=56,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
            on_click=self._on_google_login,
            ink=True,
            expand=True,
        )

    def _build_biometric_button(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FINGERPRINT,
                            color=Colors.ON_SURFACE_VARIANT,
                            size=22),
                    ft.Text("Biometric",
                            size=FontSize.LABEL_LG,
                            weight=FontWeight.MEDIUM,
                            color=Colors.ON_SURFACE),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            height=56,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
            on_click=self._on_biometric_login,
            ink=True,
            expand=True,
        )

    def _build_social_section(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Container(height=32),
                self._build_divider_row("OR LOGIN WITH"),
                ft.Container(height=20),
                ft.Row(
                    controls=[
                        self._build_google_button(),
                        self._build_biometric_button(),
                    ],
                    spacing=12,
                ),
                ft.Container(height=28),
                # Footer — single Text with spans to guarantee one-line rendering
                ft.Row(
                    controls=[
                        ft.Text(
                            spans=[
                                ft.TextSpan(
                                    "Don't have an account?  ",
                                    style=ft.TextStyle(
                                        color=Colors.ON_SURFACE_VARIANT,
                                        size=FontSize.BODY_MD,
                                    ),
                                ),
                                ft.TextSpan(
                                    "Register",
                                    style=ft.TextStyle(
                                        color=Colors.PRIMARY,
                                        size=FontSize.BODY_MD,
                                        weight=FontWeight.BOLD,
                                    ),
                                    on_click=self._on_go_register,
                                ),
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=24),
            ],
            spacing=0,
        )

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    async def _on_login(self, e: ft.ControlEvent) -> None:
        email    = self._email_field.value.strip().lower()
        password = self._password_field.value

        # ── Basic presence check ─────────────────────────────────────── #
        if not email or not password:
            self._email_field.error = "Enter your email and password"
            self._email_field.update()
            return

        self._email_field.error    = None
        self._password_field.error = None
        self._email_field.update()
        self._password_field.update()

        # ── DB lookup ────────────────────────────────────────────────── #
        try:
            user = await database.get_user_by_email(email)
        except Exception as exc:
            self._page.show_dialog(
                ft.SnackBar(ft.Text(f"Connection error — please try again. ({exc})"))
            )
            return

        invalid = user is None or not bcrypt.checkpw(
            password.encode(), user["password_hash"].encode()
        )
        if invalid:
            self._email_field.error    = "Invalid email or password"
            self._password_field.error = " "
            self._email_field.update()
            self._password_field.update()
            return

        # ── Unverified account — send a fresh OTP and route to verify ── #
        if not user["is_verified"]:
            otp_code = f"{secrets.randbelow(1_000_000):06d}"
            database.send_verification_email(user["email"], otp_code)
            await database.store_email_otp(user["id"], otp_code)
            self._page.session.store.set("pending_user_id", str(user["id"]))
            self._page.session.store.set("pending_email",   user["email"])
            self._page.navigate("/verify")
            return

        # ── Create Redis session ──────────────────────────────────────── #
        try:
            token = await database.create_session(user["id"])
        except Exception as exc:
            self._page.show_dialog(
                ft.SnackBar(ft.Text(f"Session error — please try again. ({exc})"))
            )
            return

        self._page.session.store.set("user_id",       str(user["id"]))
        self._page.session.store.set("session_token", token)

        self._page.navigate("/hub")

    async def _on_forgot_password(self, e) -> None:
        self._page.navigate("/forgot-password")

    async def _on_google_login(self, e: ft.ControlEvent) -> None:
        pass  # TODO: Google OAuth

    async def _on_biometric_login(self, e: ft.ControlEvent) -> None:
        pass  # TODO: biometric

    async def _on_go_register(self, e) -> None:
        self._page.navigate("/register")

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def build(self) -> ft.View:
        return ft.View(
            route="/login",
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.symmetric(horizontal=Spacing.H_MARGIN),
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(height=64),   # top breathing room
                        self._build_header(),
                        ft.Container(height=40),
                        self._build_form(),
                        self._build_social_section(),
                    ],
                    spacing=0,
                )
            ],
        )


async def login_view(page: ft.Page) -> ft.View:
    return LoginView(page).build()
