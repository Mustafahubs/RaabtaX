import flet as ft

import database
from router import AppRouter
from theme  import Colors


async def main(page: ft.Page) -> None:
    # ── Ensure DB pools exist (idempotent after first call) ────────────
    await database.init_db()

    # ── App-wide page configuration ────────────────────────────────────
    page.title       = "RaabtaX"
    page.theme_mode  = ft.ThemeMode.DARK
    page.bgcolor     = Colors.BACKGROUND
    page.padding     = 0
    page.fonts       = {
        "Inter": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"
    }
    page.theme = ft.Theme(font_family="Inter")

    # ── Boot router, then navigate to the initial route ─────────────────
    AppRouter(page)
    page.navigate("/login")


if __name__ == "__main__":
    ft.run(main)
