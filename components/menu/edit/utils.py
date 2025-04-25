import dash_mantine_components as dmc
import dash_blueprint_components as dbpc
from dash import no_update, exceptions
from utils.data_processing import displaying_df


# Function to search for a tab with specific ID in the entire layout
def find_tab_in_layout(model, tab_id):
    # Search in borders section
    for border in model.get("borders", []):
        children = border.get("children", [])
        for i, child in enumerate(children):
            if child.get("id") == tab_id:
                return {
                    "found": True,
                    "location": "borders",
                    "border_index": model["borders"].index(border),
                    "tab_index": i
                }
    
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
    """ 편집 메뉴의 버튼 클릭 시 우측 패널에 탭을 추가하는 공통 로직 """

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
            from dash import Patch
            patched_model = Patch()
            border_index = tab_search_result["border_index"]
            tab_index = tab_search_result["tab_index"]
            patched_model["borders"][border_index]["selected"] = tab_index
            return patched_model, no_update
        else:
            # 메인 레이아웃에 있다면 경고 메시지 출력
            return no_update, [dbpc.Toast(message=f"기존 탭이 레이아웃에 있습니다.", intent="warning", icon="info-sign")]
    
    # 탭이 존재하지 않으면 정상적으로 진행
    right_border_index = next(
        (i for i, b in enumerate(current_model["borders"]) if b["location"] == "right"), 
        None
    )
    
    # 새로운 탭 정의
    new_tab = {
        "type": "tab",
        "name": tab_name,
        "component": tab_component,
        "enableClose": True,
        "id": tab_id
    }

    from dash import Patch
    patched_model = Patch()

    if right_border_index is not None:
        # 기존 right border 수정
        patched_model["borders"][right_border_index]["children"].append(new_tab)
        patched_model["borders"][right_border_index]["selected"] = len(current_model["borders"][right_border_index]["children"])
    else:
        # right border가 없으면 새로 추가
        patched_model["borders"].append({
            "type": "border", 
            "location": "right", 
            "size": 400, 
            "selected": 0, 
            "children": [new_tab]
        })
            
    return patched_model, no_update
