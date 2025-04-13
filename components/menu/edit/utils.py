
# 전체 레이아웃에서 col-tab ID를 가진 탭이 있는지 검색하는 함수
def find_tab_in_layout(model, tab_id):
    # borders 검색
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
    
    # 메인 레이아웃 검색 (재귀적으로)
    def search_in_layout(layout_item):
        if isinstance(layout_item, dict):
            if layout_item.get("id") == tab_id:
                return True
            
            # children이 있는 경우 재귀적으로 검색
            children = layout_item.get("children", [])
            if isinstance(children, list):
                for child in children:
                    if search_in_layout(child):
                        return True
        return False
    
    if "layout" in model and search_in_layout(model["layout"]):
        return {"found": True, "location": "layout"}
        
    return {"found": False}
