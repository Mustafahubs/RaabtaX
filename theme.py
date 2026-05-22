"""
Obsidian Flux design tokens — single source of truth for all views.
Derived from UI_Screens/obsidian_flux/DESIGN.md and screen code.html files.
"""
import flet as ft


class Colors:
    # Surfaces (dark-to-light layering)
    BACKGROUND             = "#0b1326"
    SURFACE                = "#0b1326"
    SURFACE_CONTAINER_LOW  = "#131b2e"
    SURFACE_CONTAINER      = "#171f33"
    SURFACE_CONTAINER_HIGH = "#222a3d"
    SURFACE_VARIANT        = "#2d3449"
    SURFACE_BRIGHT         = "#31394d"

    # On-surface text
    ON_SURFACE         = "#dae2fd"
    ON_SURFACE_VARIANT = "#c2c6d6"

    # Borders
    OUTLINE         = "#8c909f"
    OUTLINE_VARIANT = "#424754"

    # Primary brand (electric blue)
    PRIMARY              = "#adc6ff"
    ON_PRIMARY           = "#002e6a"
    PRIMARY_CONTAINER    = "#4d8eff"
    ON_PRIMARY_CONTAINER = "#00285d"

    # Secondary
    SECONDARY           = "#b9c7e0"
    ON_SECONDARY        = "#233144"
    SECONDARY_CONTAINER = "#3c4a5e"

    # Tertiary (accent green — online/success)
    TERTIARY           = "#4ae176"
    TERTIARY_CONTAINER = "#00a74b"

    # Semantic
    ERROR           = "#ffb4ab"
    ON_ERROR        = "#690005"
    ERROR_CONTAINER = "#93000a"


class Radius:
    SM      = 8
    DEFAULT = 16   # rounded-2xl equivalent
    MD      = 20
    LG      = 28
    FULL    = 999  # pill shape


class Spacing:
    H_MARGIN = 24   # strict horizontal side margin
    GUTTER   = 8
    SM       = 4
    MD       = 12
    LG       = 24
    TOUCH    = 48   # minimum Android touch target height


class FontSize:
    HEADLINE_MOBILE = 24
    HEADLINE_MD     = 22
    TITLE_LG        = 18
    BODY_LG         = 16
    BODY_MD         = 14
    LABEL_LG        = 12
    LABEL_SM        = 11


class FontWeight:
    REGULAR   = ft.FontWeight.W_400
    MEDIUM    = ft.FontWeight.W_500
    SEMIBOLD  = ft.FontWeight.W_600
    BOLD      = ft.FontWeight.BOLD
