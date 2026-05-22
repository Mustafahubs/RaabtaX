import flet as ft

from views.chat_hub_view import chat_hub_view
from views.dm_chat_view  import dm_chat_view
from views.dms_view      import dms_view
from views.login_view    import login_view
from views.register_view import register_view
from views.verify_view   import verify_view


class AppRouter:
    """
    Central SPA routing controller.

    Strategy: full stack replacement on every route change.
    page.views.clear() drops all references to the old view object so
    Python's GC can reclaim it immediately — no stale field values or
    dangling callbacks survive the transition.
    """

    # Redirect map — keys are resolved before view lookup
    _REDIRECTS: dict[str, str] = {
        "/": "/hub",
    }

    def __init__(self, page: ft.Page) -> None:
        self._page = page
        page.on_route_change = self._on_route_change
        page.on_view_pop     = self._on_view_pop

    # ------------------------------------------------------------------ #
    #  Route resolution                                                    #
    # ------------------------------------------------------------------ #

    async def _resolve(self, route: str) -> ft.View:
        """Map a route string to a freshly built ft.View."""
        match route:
            case "/login":
                return await login_view(self._page)
            case "/register":
                return await register_view(self._page)
            case "/verify":
                return await verify_view(self._page)
            case "/hub":
                return await chat_hub_view(self._page)
            case "/dms":
                return await dms_view(self._page)
            case "/dm":
                return await dm_chat_view(self._page)
            case _:
                # Fallback: send unknown routes to login
                return await login_view(self._page)

    # ------------------------------------------------------------------ #
    #  Flet event hooks                                                    #
    # ------------------------------------------------------------------ #

    async def _on_route_change(self, e: ft.RouteChangeEvent) -> None:
        route = self._REDIRECTS.get(e.route, e.route)

        # Full replacement — old view objects go out of scope here
        self._page.views.clear()
        self._page.views.append(await self._resolve(route))
        self._page.update()

    async def _on_view_pop(self, view: ft.View) -> None:
        """Handles Android hardware back button."""
        self._page.views.pop()
        self._page.update()
