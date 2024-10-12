import dash_mantine_components as dmc
from dash import html
from typing import Optional, Dict, Any


def create_notification(
    message: str,
    title: str = "오류가 발생했습니다!",
    color: str = "yellow",
    action: str = "show",
    icon_name: str = "bx-tired",
    position: str = "bottom-right",
    autoClose: Optional[int] = None,
    disallowClose: bool = False,
    loading: bool = False,
    style: Optional[Dict[str, Any]] = None,
):
    default_style = {
        "position": "fixed",
        "zIndex": 9999,
        "width": "auto" if position == "center" else 400,
    }

    position_styles = {
        "center": {"top": "50%", "left": "50%", "transform": "translate(-50%, -50%)"},
        "top-center": {"top": 20, "left": "50%", "transform": "translateX(-50%)"},
        "top-right": {"top": 20, "right": 20},
        "bottom-right": {"bottom": 70, "right": 25},
    }

    default_style.update(position_styles.get(position, {}))
    if style:
        default_style.update(style)

    return dmc.Notification(
        title=title,
        message=message,
        color=color,
        action=action,
        icon=get_icon(icon_name),
        style=default_style,
        withCloseButton=not disallowClose,
        withBorder=True,
        autoClose=autoClose,
        loading=loading,
    )


def get_icon(icon, width=20, height=20):
    return html.Img(src=f"assets/icons/{icon}.png", width=width, height=height)
