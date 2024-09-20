import dash_mantine_components as dmc
from dash import html

def create_notification(
    message,
    title="오류가 발생했습니다!",
    color="yellow",
    action="show",
    icon_name="bx-tired",
    position="bottom-right",
):
    style = {
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

    style.update(position_styles.get(position, {}))

    return dmc.Notification(
        title=title,
        message=message,
        color=color,
        action=action,
        icon=get_icon(icon_name),
        style=style,
        withCloseButton=True,
        withBorder=True,
    )

def get_icon(icon, width=20, height=20):
    return html.Img(src=f"assets/icons/{icon}.png", width=width, height=height)
