import secrets

import flet as ft
import asyncpg
import bcrypt

import database
from theme import Colors, Radius, Spacing, FontSize, FontWeight


class RegisterView:
    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._name_field     = self._make_field("Full Name",      ft.Icons.PERSON)
        self._email_field    = self._make_field("Email Address",  ft.Icons.MAIL,
                                                keyboard_type=ft.KeyboardType.EMAIL)
        self._phone_field    = self._make_field("Phone Number",   ft.Icons.CALL,
                                                keyboard_type=ft.KeyboardType.PHONE)
        self._password_field = self._make_password_field()
        self._terms_checkbox = ft.Checkbox(
            value=False,
            fill_color=Colors.PRIMARY_CONTAINER,
            check_color=Colors.ON_PRIMARY_CONTAINER,
        )

    # ------------------------------------------------------------------ #
    #  Field factories                                                     #
    # ------------------------------------------------------------------ #

    def _make_field(
        self,
        label: str,
        icon: str,
        keyboard_type: ft.KeyboardType = ft.KeyboardType.TEXT,
    ) -> ft.TextField:
        return ft.TextField(
            label=label,
            label_style=ft.TextStyle(
                color=Colors.ON_SURFACE_VARIANT,
                size=FontSize.BODY_MD,
            ),
            prefix_icon=icon,
            keyboard_type=keyboard_type,
            # fill_color triggers filled=True automatically
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
            # vertical=16 for labeled fields — label already provides height
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=16),
        )

    def _make_password_field(self) -> ft.TextField:
        return ft.TextField(
            label="Choose Password",
            label_style=ft.TextStyle(
                color=Colors.ON_SURFACE_VARIANT,
                size=FontSize.BODY_MD,
            ),
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
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=16),
        )

    # ------------------------------------------------------------------ #
    #  Section builders                                                    #
    # ------------------------------------------------------------------ #

    def _build_header(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.VERIFIED_USER,
                                    color=Colors.ON_PRIMARY_CONTAINER,
                                    size=26),
                    width=52,
                    height=52,
                    bgcolor=Colors.PRIMARY_CONTAINER,
                    border_radius=Radius.DEFAULT,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=20),
                ft.Text(
                    "Create Account",
                    size=FontSize.HEADLINE_MOBILE,
                    weight=FontWeight.BOLD,
                    color=Colors.ON_SURFACE,
                ),
                ft.Container(height=6),
                ft.Text(
                    "Join the Obsidian Flux network and experience high-fidelity focus.",
                    size=FontSize.BODY_MD,
                    color=Colors.ON_SURFACE_VARIANT,
                    max_lines=2,
                ),
            ],
            spacing=0,
        )

    def _build_terms_row(self) -> ft.Row:
        return ft.Row(
            controls=[
                self._terms_checkbox,
                ft.Text(
                    spans=[
                        ft.TextSpan("I agree to the "),
                        ft.TextSpan(
                            "Terms of Service",
                            style=ft.TextStyle(
                                color=Colors.PRIMARY,
                                weight=FontWeight.SEMIBOLD,
                            ),
                        ),
                        ft.TextSpan(" and "),
                        ft.TextSpan(
                            "Privacy Policy",
                            style=ft.TextStyle(
                                color=Colors.PRIMARY,
                                weight=FontWeight.SEMIBOLD,
                            ),
                        ),
                        ft.TextSpan("."),
                    ],
                    style=ft.TextStyle(
                        color=Colors.ON_SURFACE_VARIANT,
                        size=FontSize.LABEL_LG,
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

    def _build_continue_button(self) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("Continue",
                            size=FontSize.TITLE_LG,
                            weight=FontWeight.SEMIBOLD,
                            color=Colors.ON_PRIMARY),
                    ft.Icon(ft.Icons.ARROW_FORWARD,
                            color=Colors.ON_PRIMARY,
                            size=20),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            height=56,
            bgcolor=Colors.PRIMARY,
            border_radius=Radius.FULL,
            on_click=self._on_register,
            ink=True,
        )

    def _build_divider_row(self, label: str) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Container(height=1, bgcolor=Colors.OUTLINE_VARIANT,
                             expand=True, opacity=0.35),
                ft.Text(label,
                        size=FontSize.LABEL_SM,
                        color=Colors.OUTLINE,
                        style=ft.TextStyle(letter_spacing=1.0)),
                ft.Container(height=1, bgcolor=Colors.OUTLINE_VARIANT,
                             expand=True, opacity=0.35),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_social_icon(self, icon: str, handler) -> ft.Container:
        return ft.Container(
            content=ft.Icon(icon, color=Colors.ON_SURFACE_VARIANT, size=24),
            width=68,
            height=56,
            bgcolor=Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1, Colors.OUTLINE_VARIANT),
            border_radius=Radius.DEFAULT,
            alignment=ft.Alignment.CENTER,
            on_click=handler,
            ink=True,
        )

    def _build_footer(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Container(height=32),

                # "Already have an account? Sign In" — single Text widget,
                # no wrapping risk from TextButton padding
                ft.Row(
                    controls=[
                        ft.Text(
                            spans=[
                                ft.TextSpan(
                                    "Already have an account?  ",
                                    style=ft.TextStyle(
                                        color=Colors.ON_SURFACE_VARIANT,
                                        size=FontSize.BODY_MD,
                                    ),
                                ),
                                ft.TextSpan(
                                    "Sign In",
                                    style=ft.TextStyle(
                                        color=Colors.PRIMARY,
                                        size=FontSize.BODY_MD,
                                        weight=FontWeight.BOLD,
                                    ),
                                    on_click=self._on_go_login,
                                ),
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),

                ft.Container(height=24),
                self._build_divider_row("OR CONNECT WITH"),
                ft.Container(height=20),

                ft.Row(
                    controls=[
                        self._build_social_icon(ft.Icons.LANGUAGE, self._on_google),
                        self._build_social_icon(ft.Icons.FINGERPRINT, self._on_biometric),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                ),
                ft.Container(height=24),
            ],
            spacing=0,
        )

    def _build_form(self) -> ft.Column:
        return ft.Column(
            controls=[
                self._name_field,
                ft.Container(height=16),
                self._email_field,
                ft.Container(height=16),
                self._phone_field,
                ft.Container(height=16),
                self._password_field,
                ft.Container(height=16),
                self._build_terms_row(),
                ft.Container(height=28),
                self._build_continue_button(),
            ],
            spacing=0,
        )

    # ------------------------------------------------------------------ #
    #  Event handlers                                                      #
    # ------------------------------------------------------------------ #

    def _clear_errors(self) -> None:
        for field in (self._name_field, self._email_field,
                      self._phone_field, self._password_field):
            field.error = None
            field.update()

    async def _on_register(self, e: ft.ControlEvent) -> None:
        name     = self._name_field.value.strip()
        email    = self._email_field.value.strip().lower()
        phone    = self._phone_field.value.strip()
        password = self._password_field.value

        # ── Validation ──────────────────────────────────────────────── #
        has_error = False

        if not name:
            self._name_field.error = "Required"
            self._name_field.update()
            has_error = True

        if not email or "@" not in email:
            self._email_field.error = "Enter a valid email address"
            self._email_field.update()
            has_error = True

        if not phone:
            self._phone_field.error = "Required"
            self._phone_field.update()
            has_error = True

        if len(password) < 8:
            self._password_field.error = "Minimum 8 characters"
            self._password_field.update()
            has_error = True

        if not self._terms_checkbox.value:
            self._page.show_dialog(
                ft.SnackBar(ft.Text("Please accept the Terms of Service to continue."))
            )
            return

        if has_error:
            return

        self._clear_errors()

        # ── Hash password ────────────────────────────────────────────── #
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # ── Persist to Postgres ─────────────────────────────────────── #
        try:
            user_id = await database.create_user(name, email, phone, pw_hash)
        except asyncpg.UniqueViolationError:
            self._email_field.error = "Email or phone is already registered"
            self._email_field.update()
            return
        except Exception as exc:
            self._page.show_dialog(
                ft.SnackBar(ft.Text(f"Registration failed — please try again. ({exc})"))
            )
            return

        # ── Generate & dispatch email OTP ────────────────────────────── #
        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        await database.send_verification_email(email, otp_code)
        await database.store_email_otp(user_id, otp_code)

        # ── Hand off context to verify view via session store ────────── #
        self._page.session.store.set("pending_user_id", str(user_id))
        self._page.session.store.set("pending_email",   email)

        self._page.navigate("/verify")

    async def _on_go_login(self, e) -> None:
        self._page.navigate("/login")

    async def _on_google(self, e: ft.ControlEvent) -> None:
        pass  # TODO: Google OAuth

    async def _on_biometric(self, e: ft.ControlEvent) -> None:
        pass  # TODO: biometric

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def build(self) -> ft.View:
        return ft.View(
            route="/register",
            bgcolor=Colors.BACKGROUND,
            padding=ft.Padding.symmetric(horizontal=Spacing.H_MARGIN),
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Column(
                    controls=[
                        ft.Container(height=48),
                        self._build_header(),
                        ft.Container(height=28),
                        self._build_form(),
                        self._build_footer(),
                    ],
                    spacing=0,
                )
            ],
        )


async def register_view(page: ft.Page) -> ft.View:
    return RegisterView(page).build()
