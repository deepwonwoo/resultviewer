"""Common form components for ResultViewer Edit operations"""

import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from typing import List, Dict, Any, Optional
from dash import no_update, exceptions, Patch
from utils.data_processing import displaying_df


# Function to search for a tab with specific ID in the entire layout
def find_tab_in_layout(model, tab_id):
    # Search in borders section
    for border in model.get("borders", []):
        children = border.get("children", [])
        for i, child in enumerate(children):
            if child.get("id") == tab_id:
                return {"found": True, "location": "borders", "border_index": model["borders"].index(border), "tab_index": i}

    # Search in main layout (recursively)
    def search_in_layout(layout_item):
        if isinstance(layout_item, dict):
            if layout_item.get("id") == tab_id:
                return True

            # Recursively search through children if they exist
            children = layout_item.get("children", [])
            if isinstance(children, list):
                for child in children:
                    if search_in_layout(child):
                        return True
        return False

    if "layout" in model and search_in_layout(model["layout"]):
        return {"found": True, "location": "layout"}

    return {"found": False}


def handle_tab_button_click(n_clicks, current_model, tab_id, tab_name, tab_component="button"):
    """편집 메뉴의 버튼 클릭 시 우측 패널에 탭을 추가하는 공통 로직"""

    if n_clicks is None:
        raise exceptions.PreventUpdate

    dff = displaying_df()
    if dff is None:
        return no_update, [dbpc.Toast(message=f"데이터가 로드되지 않았습니다", intent="warning", icon="warning-sign")]

    # 기존 탭 검색
    tab_search_result = find_tab_in_layout(current_model, tab_id)

    # 이미 탭이 존재한다면
    if tab_search_result["found"]:
        # borders에 있을 경우 해당 탭으로 이동
        if tab_search_result["location"] == "borders":

            patched_model = Patch()
            border_index = tab_search_result["border_index"]
            tab_index = tab_search_result["tab_index"]
            patched_model["borders"][border_index]["selected"] = tab_index
            return patched_model, no_update
        else:
            # 메인 레이아웃에 있다면 경고 메시지 출력
            return no_update, [dbpc.Toast(message=f"기존 탭이 레이아웃에 있습니다.", intent="warning", icon="info-sign")]

    # 탭이 존재하지 않으면 정상적으로 진행
    right_border_index = next((i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), None)

    # 새로운 탭 정의
    new_tab = {"type": "tab", "name": tab_name, "component": tab_component, "enableClose": True, "id": tab_id}

    patched_model = Patch()

    if right_border_index is not None:
        # 기존 right border 수정
        patched_model["borders"][right_border_index]["children"].append(new_tab)
        patched_model["borders"][right_border_index]["selected"] = len(current_model["borders"][right_border_index]["children"])
    else:
        # right border가 없으면 새로 추가
        patched_model["borders"].append({"type": "border", "location": "right", "size": 400, "selected": 0, "children": [new_tab]})

    return patched_model, no_update


class FormComponents:
    """Reusable form components with consistent styling and behavior"""

    @staticmethod
    def create_section_card(title: str, icon: str, children: List[Any], description: Optional[str] = None) -> dmc.Card:
        """Create a consistent section card for edit forms"""
        return dmc.Card(children=[dmc.Group([dbpc.Icon(icon=icon, size=20), dmc.Title(title, order=4)], mb="sm"), dmc.Text(description, size="sm", c="dimmed", mb="md") if description else None, *children], withBorder=True, shadow="sm", radius="md", p="lg", mb="md")

    @staticmethod
    def create_column_selector(id: str, label: str = "Select Columns", description: str = "Choose columns to process", multi: bool = True, required: bool = True, data: List[Dict[str, str]] = None) -> dmc.MultiSelect:
        """Create a consistent column selector"""
        component = dmc.MultiSelect if multi else dmc.Select
        return component(id=id, label=label, description=description, placeholder="Select columns...", required=required, searchable=True, clearable=True, data=data or [], leftSection=dbpc.Icon(icon="th"), size="md", styles={"dropdown": {"maxHeight": 400}})

    @staticmethod
    def create_action_button(id: str, label: str, icon: str = "tick", intent: str = "primary", loading_id: Optional[str] = None) -> dmc.Button:
        """Create a consistent action button with loading state"""
        return dmc.Button(label, id=id, leftSection=dbpc.Icon(icon=icon), variant="filled" if intent == "primary" else "outline", color="blue" if intent == "primary" else "gray", size="md", loading=False, loaderProps={"type": "dots"})

    @staticmethod
    def create_preview_section(id: str, initial_content: str = "Preview will appear here after configuration") -> dmc.Paper:
        """Create a consistent preview section"""
        return dmc.Paper(id=id, withBorder=True, p="md", radius="md", style={"maxHeight": "300px", "overflow": "auto"}, children=[dmc.Text(initial_content, size="sm", c="dimmed", ta="center")])

    @staticmethod
    def create_help_section(items: List[str]) -> dmc.Accordion:
        """Create a consistent help section"""
        return dmc.Accordion(value="", children=[dmc.AccordionItem([dmc.AccordionControl(dmc.Group([dbpc.Icon(icon="help"), dmc.Text("Help & Instructions")])), dmc.AccordionPanel(dmc.Timeline(active=len(items), bulletSize=15, lineWidth=2, children=[dmc.TimelineItem(children=dmc.Text(item, size="sm")) for item in items]))], value="help")])
