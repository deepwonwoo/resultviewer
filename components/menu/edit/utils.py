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
