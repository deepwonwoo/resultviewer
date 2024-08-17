import dash_mantine_components as dmc
from dash import html

def create_notification(
    message,
    title="Something went wrong!",
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
    
    if position == "center":
        style.update({
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
        })
    elif position == "top-center":
        style.update({
            "top": 20,
            "left": "50%",
            "transform": "translateX(-50%)",
        })
    elif position == "top-right":
        style.update({
            "top": 20,
            "right": 20,
        })
    elif position == "bottom-right":
        style.update({
            "bottom": 70,
            "right": 25,
        })

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