"""
Zhuibook Theme System
Light themes (3): 🌿 MATCHA / 🍋 LEMON / ☁️  FOG
Dark themes (3):  🌙 MATCHA DARK / 🌙 LEMON DARK / 🌙 FOG DARK
All colors centralized, no hardcoded tokens in widgets.
"""
from __future__ import annotations
from typing import Dict, Any


THEMES: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# 🌿 MATCHA (抹茶绿 — 默认浅色主题，清新护眼浅绿色系)
# ---------------------------------------------------------------------------
THEMES["matcha"] = {
    "name": "🌿 抹茶绿",
    "group": "light",

    # ---- 主色（温和抹茶绿，低饱和不刺眼） ----
    "primary":              "#5A9E7E",
    "primary_text":         "#4B8A6D",
    "primary_light":        "#6CB18F",
    "primary_gradient_top": "#6EBD98",
    "primary_gradient_bot": "#529477",
    "primary_hover_top":    "#60AE87",
    "primary_hover_bot":    "#46856A",
    "primary_pressed_top":  "#549F7D",
    "primary_pressed_bot":  "#3D7860",

    # ---- 背景层 ----
    "global_bg":            "#F2F7F0",
    "sidebar_bg":           "#EFF5EC",
    "sidebar_header_top":   "#E6F0E1",
    "sidebar_header_bot":   "#EFF5EC",
    "editor_header_bg":     "#FFFFFF",
    "editor_bg":            "#FFFFFF",
    "toolbar_bg":           "#F0F5ED",
    "status_bar_bg":        "#F2F7F0",
    "input_bg":             "#FFFFFF",
    "card_bg":              "#FFFFFF",
    "surface_bg":           "#FFFFFF",

    # ---- 边框 / 分隔 ----
    "border":               "#D6E0D1",
    "border_strong":        "#C5D2BF",

    # ---- 文本 ----
    "text_primary":         "#2E3630",
    "text_secondary":       "#828E86",
    "text_tertiary":        "#B9C2BB",
    "title_color":          "#5A9E7E",

    # ---- 选中 / hover 底 ----
    "selection_bg":         "#DFEEE4",
    "selection_fg":         "#4B8A6D",
    "list_hover_bg":        "#E7EEE3",
    "list_selected_bg":     "#E5EEE7",
    "list_selected_left":   "#5A9E7E",
    "list_selected_fg":     "#4B8A6D",

    # ---- Markdown 语法颜色 ----
    "h1":                   "#3F7F61",
    "h2":                   "#458968",
    "h3":                   "#4B926F",
    "h4":                   "#2E3630",
    "h5":                   "#39433D",
    "h6":                   "#828E86",
    "list_marker":          "#6CB18F",
    "link":                 "#5A9E7E",
    "link_url":             "#66756D",
    "quote_bg":             "#EEF4EA",
    "quote_fg":             "#5B645E",
    "inlinecode_bg":        "#F4EDE5",
    "inlinecode_fg":        "#C26B5A",
    "codeblock_bg":         "#F2EEE6",
    "codeblock_fg":         "#3E423F",
    "codeblock_fence":      "#6E6A62",
    "marker_visible":       "#95A09A",

    # ---- 滚动条 / 状态色 ----
    "scrollbar_handle":     "#C9D4C3",
    "scrollbar_hover":      "#B1BFA9",
    "save_color":           "#4B9A6D",
}

# ---------------------------------------------------------------------------
# 🍋 LEMON (柠檬奶黄 — 温暖浅色黄系)
# ---------------------------------------------------------------------------
THEMES["lemon"] = {
    "name": "🍋 柠檬奶黄",
    "group": "light",

    "primary":              "#D7A94A",
    "primary_text":         "#B98A2C",
    "primary_light":        "#E4B85C",
    "primary_gradient_top": "#E9BF6A",
    "primary_gradient_bot": "#CD9F3F",
    "primary_hover_top":    "#DCB050",
    "primary_hover_bot":    "#BD9036",
    "primary_pressed_top":  "#CFA13E",
    "primary_pressed_bot":  "#A87D2C",

    "global_bg":            "#FBF6E7",
    "sidebar_bg":           "#F9F2DF",
    "sidebar_header_top":   "#F4EAD0",
    "sidebar_header_bot":   "#F9F2DF",
    "editor_header_bg":     "#FFFFFF",
    "editor_bg":            "#FFFFFF",
    "toolbar_bg":           "#F8F1DA",
    "status_bar_bg":        "#FBF6E7",
    "input_bg":             "#FFFFFF",
    "card_bg":              "#FFFFFF",
    "surface_bg":           "#FFFFFF",

    "border":               "#E8DEBF",
    "border_strong":        "#DBCFA7",

    "text_primary":         "#3A362C",
    "text_secondary":       "#918874",
    "text_tertiary":        "#C7BD9F",
    "title_color":          "#D7A94A",

    "selection_bg":         "#F6EBD0",
    "selection_fg":         "#B98A2C",
    "list_hover_bg":        "#F2EAD0",
    "list_selected_bg":     "#F2EACE",
    "list_selected_left":   "#D7A94A",
    "list_selected_fg":     "#B98A2C",

    "h1":                   "#B68A36",
    "h2":                   "#C2933D",
    "h3":                   "#CC9E47",
    "h4":                   "#3A362C",
    "h5":                   "#413D32",
    "h6":                   "#918874",
    "list_marker":          "#E4B85C",
    "link":                 "#D7A94A",
    "link_url":             "#7A715D",
    "quote_bg":             "#FAF2DB",
    "quote_fg":             "#68604F",
    "inlinecode_bg":        "#F6EAEC",
    "inlinecode_fg":        "#C35A7D",
    "codeblock_bg":         "#F6F0DD",
    "codeblock_fg":         "#423E33",
    "codeblock_fence":      "#706A59",
    "marker_visible":       "#9D957D",

    "scrollbar_handle":     "#E3D7B2",
    "scrollbar_hover":      "#D3C496",
    "save_color":           "#B5A049",
}

# ---------------------------------------------------------------------------
# ☁️  FOG (雾蓝 — 原冷蓝浅色系)
# ---------------------------------------------------------------------------
THEMES["fog"] = {
    "name": "☁️  雾蓝",
    "group": "light",

    "primary":              "#5B8DEF",
    "primary_text":         "#4776D6",
    "primary_light":        "#6A9CF5",
    "primary_gradient_top": "#6A9CF5",
    "primary_gradient_bot": "#5182E6",
    "primary_hover_top":    "#5D92EF",
    "primary_hover_bot":    "#4573D8",
    "primary_pressed_top":  "#4B82E0",
    "primary_pressed_bot":  "#3A64C8",

    "global_bg":            "#FBFAF7",
    "sidebar_bg":           "#FBFAF7",
    "sidebar_header_top":   "#F6F3EC",
    "sidebar_header_bot":   "#FBFAF7",
    "editor_header_bg":     "#FFFFFF",
    "editor_bg":            "#FFFFFF",
    "toolbar_bg":           "#FBFAF7",
    "status_bar_bg":        "#FBFAF7",
    "input_bg":             "#FFFFFF",
    "card_bg":              "#FFFFFF",
    "surface_bg":           "#FFFFFF",

    "border":               "#EDE9E0",
    "border_strong":        "#CFC9BB",

    "text_primary":         "#2B2B29",
    "text_secondary":       "#8A8578",
    "text_tertiary":        "#C9C4B6",
    "title_color":          "#5B8DEF",

    "selection_bg":         "#EEF3FF",
    "selection_fg":         "#4776D6",
    "list_hover_bg":        "#F4F1E9",
    "list_selected_bg":     "#EEF3FF",
    "list_selected_left":   "#5B8DEF",
    "list_selected_fg":     "#4776D6",

    "h1":                   "#456FC9",
    "h2":                   "#4A75D2",
    "h3":                   "#517DDE",
    "h4":                   "#3F3D38",
    "h5":                   "#464440",
    "h6":                   "#8A8578",
    "list_marker":          "#6A9CF5",
    "link":                 "#5B8DEF",
    "link_url":             "#6a737d",
    "quote_bg":             "#F7F3EA",
    "quote_fg":             "#5E5B52",
    "inlinecode_bg":        "#F6F2EE",
    "inlinecode_fg":        "#C7527E",
    "codeblock_bg":         "#F6F2ED",
    "codeblock_fg":         "#3C3A36",
    "codeblock_fence":      "#646056",
    "marker_visible":       "#9D9686",

    "scrollbar_handle":     "#DDD7C7",
    "scrollbar_hover":      "#C5BEAC",
    "save_color":           "#3FA362",
}

# ---------------------------------------------------------------------------
# 🌙 MATCHA DARK (抹茶深夜绿 — 深色模式默认推荐，低灰绿光感不刺眼)
# ---------------------------------------------------------------------------
THEMES["matcha_dark"] = {
    "name": "🌙 深夜抹茶绿",
    "group": "dark",

    "primary":              "#7FC9A6",
    "primary_text":         "#A4DCBE",
    "primary_light":        "#8FD4B3",
    "primary_gradient_top": "#7FC9A6",
    "primary_gradient_bot": "#5FA585",
    "primary_hover_top":    "#8FD4B3",
    "primary_hover_bot":    "#6BB08F",
    "primary_pressed_top":  "#6BB08F",
    "primary_pressed_bot":  "#4E9174",

    "global_bg":            "#1A1F1D",
    "sidebar_bg":           "#1D2220",
    "sidebar_header_top":   "#212725",
    "sidebar_header_bot":   "#1D2220",
    "editor_header_bg":     "#1F2523",
    "editor_bg":            "#222927",
    "toolbar_bg":           "#242B29",
    "status_bar_bg":        "#1A1F1D",
    "input_bg":             "#262E2C",
    "card_bg":              "#242B29",
    "surface_bg":           "#2A322F",

    "border":               "#333D3A",
    "border_strong":        "#45534E",

    "text_primary":         "#E6EFEC",
    "text_secondary":       "#9DA8A3",
    "text_tertiary":        "#64716C",
    "title_color":          "#7FC9A6",

    "selection_bg":         "#2E4A3D",
    "selection_fg":         "#D8F0E4",
    "list_hover_bg":        "#272F2D",
    "list_selected_bg":     "#2A3A33",
    "list_selected_left":   "#7FC9A6",
    "list_selected_fg":     "#BEE6D4",

    "h1":                   "#A4DCBE",
    "h2":                   "#93D1B1",
    "h3":                   "#83C6A4",
    "h4":                   "#E6EFEC",
    "h5":                   "#CBD4D1",
    "h6":                   "#9DA8A3",
    "list_marker":          "#8FD4B3",
    "link":                 "#7FC9A6",
    "link_url":             "#92A79F",
    "quote_bg":             "#2A3330",
    "quote_fg":             "#BFCBC5",
    "inlinecode_bg":        "#3A312C",
    "inlinecode_fg":        "#E29D8C",
    "codeblock_bg":         "#2D2A24",
    "codeblock_fg":         "#D9E2DE",
    "codeblock_fence":      "#7A837F",
    "marker_visible":       "#82908B",

    "scrollbar_handle":     "#404B47",
    "scrollbar_hover":      "#505E58",
    "save_color":           "#7FC9A6",
}

# ---------------------------------------------------------------------------
# 🌙 LEMON DARK (柠檬深夜黄 — 温暖深色模式，适合夜间)
# ---------------------------------------------------------------------------
THEMES["lemon_dark"] = {
    "name": "🌙 深夜柠檬黄",
    "group": "dark",

    "primary":              "#E5B966",
    "primary_text":         "#F0CC88",
    "primary_light":        "#ECC478",
    "primary_gradient_top": "#ECC478",
    "primary_gradient_bot": "#C99A47",
    "primary_hover_top":    "#F1CE88",
    "primary_hover_bot":    "#D3A552",
    "primary_pressed_top":  "#D3A552",
    "primary_pressed_bot":  "#B18639",

    "global_bg":            "#1F1D17",
    "sidebar_bg":           "#22201A",
    "sidebar_header_top":   "#27241E",
    "sidebar_header_bot":   "#22201A",
    "editor_header_bg":     "#25221C",
    "editor_bg":            "#28251F",
    "toolbar_bg":           "#2A2721",
    "status_bar_bg":        "#1F1D17",
    "input_bg":             "#2D2A23",
    "card_bg":              "#2A2721",
    "surface_bg":           "#302C25",

    "border":               "#3B362B",
    "border_strong":        "#524A38",

    "text_primary":         "#F0EADB",
    "text_secondary":       "#B0A793",
    "text_tertiary":        "#706855",
    "title_color":          "#E5B966",

    "selection_bg":         "#4B3F25",
    "selection_fg":         "#F8ECC9",
    "list_hover_bg":        "#2B271F",
    "list_selected_bg":     "#3A3224",
    "list_selected_left":   "#E5B966",
    "list_selected_fg":     "#F0D9A3",

    "h1":                   "#F0CC88",
    "h2":                   "#EAC279",
    "h3":                   "#E5B966",
    "h4":                   "#F0EADB",
    "h5":                   "#D4CCBB",
    "h6":                   "#B0A793",
    "list_marker":          "#ECC478",
    "link":                 "#E5B966",
    "link_url":             "#A59B85",
    "quote_bg":             "#2E2A22",
    "quote_fg":             "#C6BCA7",
    "inlinecode_bg":        "#3A2A2E",
    "inlinecode_fg":        "#E29DB0",
    "codeblock_bg":         "#2F2B23",
    "codeblock_fg":         "#DCD4C0",
    "codeblock_fence":      "#7D7562",
    "marker_visible":       "#8E8571",

    "scrollbar_handle":     "#4A4332",
    "scrollbar_hover":      "#5D533F",
    "save_color":           "#D9BC6A",
}

# ---------------------------------------------------------------------------
# 🌙 FOG DARK (雾蓝深夜 — 冷蓝深色模式，原经典深色)
# ---------------------------------------------------------------------------
THEMES["fog_dark"] = {
    "name": "🌙 深夜雾蓝",
    "group": "dark",

    "primary":              "#7AA9F5",
    "primary_text":         "#9DBBF6",
    "primary_light":        "#8BB4F7",
    "primary_gradient_top": "#7AA9F5",
    "primary_gradient_bot": "#5C8DE0",
    "primary_hover_top":    "#8BB4F7",
    "primary_hover_bot":    "#6897EC",
    "primary_pressed_top":  "#6897EC",
    "primary_pressed_bot":  "#4E79D1",

    "global_bg":            "#171C26",
    "sidebar_bg":           "#1A1F2A",
    "sidebar_header_top":   "#1E2431",
    "sidebar_header_bot":   "#1A1F2A",
    "editor_header_bg":     "#1C222D",
    "editor_bg":            "#1F2631",
    "toolbar_bg":           "#212935",
    "status_bar_bg":        "#171C26",
    "input_bg":             "#232C39",
    "card_bg":              "#212935",
    "surface_bg":           "#283240",

    "border":               "#2F3948",
    "border_strong":        "#435064",

    "text_primary":         "#E4EAF4",
    "text_secondary":       "#98A1B1",
    "text_tertiary":        "#606978",
    "title_color":          "#7AA9F5",

    "selection_bg":         "#2B3B5F",
    "selection_fg":         "#D9E4FF",
    "list_hover_bg":        "#1F2531",
    "list_selected_bg":     "#253046",
    "list_selected_left":   "#7AA9F5",
    "list_selected_fg":     "#B9CCF4",

    "h1":                   "#9DBBF6",
    "h2":                   "#8FB2F5",
    "h3":                   "#81A8F4",
    "h4":                   "#E4EAF4",
    "h5":                   "#CCD3DF",
    "h6":                   "#98A1B1",
    "list_marker":          "#8BB4F7",
    "link":                 "#7AA9F5",
    "link_url":             "#8E97A7",
    "quote_bg":             "#242B37",
    "quote_fg":             "#BFC6D3",
    "inlinecode_bg":        "#352B31",
    "inlinecode_fg":        "#E59AB5",
    "codeblock_bg":         "#262A31",
    "codeblock_fg":         "#D7DEE9",
    "codeblock_fence":      "#6E7787",
    "marker_visible":       "#7F8795",

    "scrollbar_handle":     "#3A4355",
    "scrollbar_hover":      "#495469",
    "save_color":           "#7ECB98",
}

DEFAULT_THEME = "matcha"


# ===========================================================================
# QSS 模板 — 所有 {key} 会在 apply 时用主题字典注入
# ===========================================================================

def get_sidebar_note_list_qss(t: Dict[str, Any]) -> str:
    return f"""
    QListWidget {{
        border: none;
        background: {t['sidebar_bg']};
        font-size: 13px;
        outline: 0;
    }}
    QListWidget::item {{
        padding: 12px 16px;
        border-bottom: 1px solid {t['border']};
        color: {t['text_primary']};
    }}
    QListWidget::item:selected {{
        background: {t['list_selected_bg']};
        color: {t['list_selected_fg']};
        border-left: 3px solid {t['list_selected_left']};
        padding-left: 13px;
    }}
    QListWidget::item:hover:!selected {{
        background: {t['list_hover_bg']};
    }}
    """


def get_sidebar_qss(t: Dict[str, Any]) -> Dict[str, str]:
    """Returns dict with keys: header / title / search / combo / new_btn / cat_btn / list_label"""
    return {
        "header": f"""
        QFrame {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['sidebar_header_top']}, stop:1 {t['sidebar_header_bot']});
            border-bottom: 1px solid {t['border']};
        }}
        """,
        "title": f"""
        color: {t['title_color']};
        background: transparent;
        padding: 2px 0px;
        """,
        "search": f"""
        QLineEdit {{
            padding: 9px 14px;
            border: 1px solid {t['border']};
            border-radius: 8px;
            background: {t['input_bg']};
            font-size: 13px;
            color: {t['text_primary']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
        }}
        QLineEdit:hover {{ border: 1px solid {t['border_strong']}; }}
        QLineEdit:focus {{
            border: 1px solid {t['primary']};
            background: {t['input_bg']};
        }}
        """,
        "combo": f"""
        QComboBox {{
            padding: 8px 12px;
            border: 1px solid {t['border']};
            border-radius: 8px;
            background: {t['input_bg']};
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QComboBox:hover {{ border: 1px solid {t['border_strong']}; }}
        QComboBox:on {{ border: 1px solid {t['primary']}; }}
        QComboBox::drop-down {{
            border: none; width: 24px;
            subcontrol-origin: padding;
            subcontrol-position: center right;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            background: {t['input_bg']};
            color: {t['text_primary']};
            font-size: 13px;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
            outline: 0;
        }}
        """,
        "new_btn": f"""
        QPushButton {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_gradient_top']}, stop:1 {t['primary_gradient_bot']});
            color: white;
            border: none;
            padding: 9px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_hover_top']}, stop:1 {t['primary_hover_bot']});
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_pressed_top']}, stop:1 {t['primary_pressed_bot']});
        }}
        """,
        "cat_btn": f"""
        QPushButton {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            font-size: 16px;
            color: {t['primary']};
        }}
        QPushButton:hover {{
            background: {t['selection_bg']};
            border: 1px solid {t['primary']};
        }}
        QPushButton:pressed {{ background: {t['list_selected_bg']}; }}
        """,
        "theme_btn": f"""
        QPushButton {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            font-size: 16px;
            color: {t['primary']};
        }}
        QPushButton:hover {{
            background: {t['selection_bg']};
            border: 1px solid {t['primary']};
        }}
        QPushButton:pressed {{ background: {t['list_selected_bg']}; }}
        """,
        "list_label": (
            "padding: 10px 20px 4px;"
            f" color: {t['text_secondary']};"
            " font-size: 12px; font-weight: 600;"
            f" background: {t['sidebar_bg']};"
        ),
    }


def get_editor_qss(t: Dict[str, Any]) -> Dict[str, str]:
    return {
        "header": f"""
        QFrame {{
            background: {t['editor_header_bg']};
            border-bottom: 1px solid {t['border']};
        }}
        """,
        "title_edit": f"""
        QLineEdit {{
            border: none;
            outline: none;
            color: {t['text_primary']};
            padding: 2px 4px;
            background: transparent;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
        }}
        QLineEdit:hover {{
            background: {t['toolbar_bg']};
            border-radius: 6px;
        }}
        QLineEdit:focus {{
            background: {t['toolbar_bg']};
            border-radius: 6px;
        }}
        """,
        "category_combo": f"""
        QComboBox {{
            padding: 5px 12px;
            border: 1px solid {t['border']};
            border-radius: 7px;
            background: {t['input_bg']};
            color: {t['text_primary']};
            font-size: 12px;
            min-width: 140px;
        }}
        QComboBox:hover {{
            border: 1px solid {t['border_strong']};
            background: {t['sidebar_bg']};
        }}
        QComboBox:on {{ border: 1px solid {t['primary']}; }}
        QComboBox::drop-down {{
            border: none; width: 22px;
            subcontrol-origin: padding;
            subcontrol-position: center right;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {t['border']};
            border-radius: 6px;
            background: {t['input_bg']};
            color: {t['text_primary']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
            outline: 0;
        }}
        """,
        "save_btn": f"""
        QToolButton {{
            padding: 6px 14px;
            border: none;
            border-radius: 7px;
            font-size: 12px;
            font-weight: 600;
            color: #FFFFFF;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_gradient_top']}, stop:1 {t['primary_gradient_bot']});
        }}
        QToolButton:hover {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_hover_top']}, stop:1 {t['primary_hover_bot']});
        }}
        QToolButton:pressed {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {t['primary_pressed_top']}, stop:1 {t['primary_pressed_bot']});
        }}
        """,
        "export_btn": f"""
        QToolButton {{
            padding: 6px 14px;
            border: none;
            border-radius: 7px;
            font-size: 12px;
            font-weight: 600;
            color: #FFFFFF;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #10b981, stop:1 #059669);
        }}
        QToolButton:hover {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #34d399, stop:1 #10b981);
        }}
        QToolButton:pressed {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #059669, stop:1 #047857);
        }}
        """,
        "toolbar_container": f"""
        QFrame {{
            background: {t['toolbar_bg']};
            border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        """,
        "toolbar_btn": f"""
        QToolButton {{
            padding: 5px 9px;
            border: 1px solid transparent;
            border-radius: 6px;
            font-size: 12px;
            color: {t['text_primary']};
            background: transparent;
        }}
        QToolButton:hover {{
            background: {t['surface_bg']};
            border-color: {t['border_strong']};
            color: {t['primary_text']};
        }}
        QToolButton:pressed {{
            background: {t['selection_bg']};
            border-color: {t['primary']};
            color: {t['primary_text']};
        }}
        """,
        "toolbar_sep": f"background:{t['border']}; margin:6px 2px;",
        "textedit": f"""
        QTextEdit {{
            background: {t['editor_bg']};
            border: none;
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
            color: {t['text_primary']};
            font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
            font-size: 13px;
        }}
        QScrollBar:vertical {{
            width: 10px;
            background: transparent;
            margin: 2px 2px 2px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['scrollbar_handle']};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {t['scrollbar_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            height: 10px;
            background: transparent;
            margin: 0px 2px 2px 2px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t['scrollbar_handle']};
            border-radius: 5px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {t['scrollbar_hover']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """,
        "outline_panel": f"""
        QFrame#outline_panel {{
            background: {t['surface_bg']};
            border-left: 1px solid {t['border']};
        }}
        QTreeWidget {{
            background: transparent;
            border: none;
            font-size: 12px;
            color: {t['text_secondary']};
            outline: 0;
        }}
        QTreeWidget::item {{
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QTreeWidget::item:hover {{
            background: {t['list_hover_bg']};
            color: {t['text_primary']};
        }}
        QTreeWidget::item:selected {{
            background: {t['list_hover_bg']};
            color: {t['primary_text']};
        }}
        QToolButton#outline_toggle_btn {{
            border: none;
            border-radius: 5px;
            padding: 4px 8px;
            background: transparent;
            font-size: 12px;
            font-weight: 600;
            color: {t['text_secondary']};
        }}
        QToolButton#outline_toggle_btn:hover {{
            background: {t['list_hover_bg']};
            color: {t['text_primary']};
        }}
        QToolButton#outline_toggle_btn:checked {{
            background: {t['list_hover_bg']};
            color: {t['primary_text']};
        }}
        """,
    }


def get_mainwindow_qss(t: Dict[str, Any]) -> Dict[str, str]:
    return {
        "global": f"""
        QMainWindow {{ background: {t['global_bg']}; }}
        QSplitter::handle {{
            background: {t['border']};
            width: 1px;
        }}
        QSplitter::handle:hover {{
            background: {t['primary']};
            width: 2px;
        }}
        """,
        "status_bar": f"""
        QStatusBar {{
            background: {t['status_bar_bg']};
            color: {t['text_secondary']};
            border-top: 1px solid {t['border']};
            padding: 2px 4px;
        }}
        QStatusBar::item {{ border: none; }}
        """,
    }


# ===========================================================================
# 顶部 Tab 切换栏 QSS（笔记 / 画板 视图切换）
# ===========================================================================

def get_top_tab_bar_qss(t: Dict[str, Any]) -> Dict[str, str]:
    """返回顶部 Tab 栏样式：
    {'container', 'tab', 'tab_checked', 'tab_unchecked'}

    - 选中态：下划线 2px（accent），文字 text_primary，13pt 加粗
    - 未选中态：文字 text_secondary，13pt 常规
    - 背景：toolbar_bg（次级背景层）
    - 圆角：上方两角 8px，下方 0px
    - padding：12px 24px
    """
    return {
        "container": f"""
        QFrame {{
            background: {t['toolbar_bg']};
            border-bottom: 1px solid {t['border']};
        }}
        """,
        "tab": f"""
        QPushButton {{
            background: {t['toolbar_bg']};
            color: {t['text_secondary']};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            padding: 12px 24px;
            font-size: 13pt;
            font-weight: normal;
            text-align: center;
            outline: 0;
        }}
        QPushButton:hover:!checked {{
            color: {t['text_primary']};
            background: {t['list_hover_bg']};
        }}
        QPushButton:pressed:!checked {{
            background: {t['selection_bg']};
        }}
        """,
        "tab_checked": f"""
        QPushButton {{
            background: {t['toolbar_bg']};
            color: {t['text_primary']};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            border-bottom: 2px solid {t['primary']};
            padding: 12px 24px;
            font-size: 13pt;
            font-weight: bold;
            text-align: center;
            outline: 0;
        }}
        QPushButton:hover {{
            color: {t['primary_text']};
        }}
        """,
        "tab_unchecked": f"""
        QPushButton {{
            background: {t['toolbar_bg']};
            color: {t['text_secondary']};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            padding: 12px 24px;
            font-size: 13pt;
            font-weight: normal;
            text-align: center;
            outline: 0;
        }}
        QPushButton:hover {{
            color: {t['text_primary']};
            background: {t['list_hover_bg']};
        }}
        """,
    }


# ===========================================================================
# 画板视图 QSS（工具栏 / 工具按钮 / 调色板 / 画布 / 状态栏 / 滑块）
# ===========================================================================

def get_drawing_board_qss(t: Dict[str, Any]) -> Dict[str, str]:
    """返回画板视图样式：
    {'toolbar', 'tool_group_label', 'tool_button', 'tool_button_checked',
     'color_swatch', 'color_swatch_active', 'canvas_view', 'status_bar', 'slider'}

    颜色约定：
    - 工具栏背景：toolbar_bg
    - 工具按钮 hover：list_hover_bg
    - 工具按钮 checked：primary
    - 调色板边框：border
    - 状态栏文字：text_secondary
    - 画布视图背景：固定 #E0E0E0（衬托白色画布）
    """
    return {
        "toolbar": f"""
        QFrame#drawing_toolbar {{
            background: {t['toolbar_bg']};
            border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        QFrame#drawing_group {{
            background: transparent;
            border: none;
        }}
        """,
        "tool_group_label": f"""
        color: {t['text_secondary']};
        background: transparent;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 4px;
        """,
        "tool_button": f"""
        QPushButton {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
            color: {t['text_primary']};
            min-width: 28px;
            min-height: 24px;
        }}
        QPushButton:hover {{
            background: {t['list_hover_bg']};
            border: 1px solid {t['primary']};
            color: {t['primary_text']};
        }}
        QPushButton:pressed {{
            background: {t['selection_bg']};
        }}
        """,
        "tool_button_checked": f"""
        QPushButton {{
            background: {t['primary']};
            border: 1px solid {t['primary']};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
            color: #FFFFFF;
            font-weight: bold;
            min-width: 28px;
            min-height: 24px;
        }}
        QPushButton:hover {{
            background: {t['primary_hover_top']};
            border: 1px solid {t['primary']};
            color: #FFFFFF;
            font-weight: bold;
        }}
        QPushButton:pressed {{
            background: {t['primary_pressed_top']};
        }}
        """,
        "color_swatch": f"""
        QPushButton {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            min-width: 22px;
            min-height: 22px;
            max-width: 22px;
            max-height: 22px;
            padding: 0px;
        }}
        QPushButton:hover {{
            border: 2px solid {t['primary']};
            border-radius: 6px;
        }}
        """,
        "color_swatch_active": f"""
        QPushButton {{
            border: 2px solid {t['primary']};
            border-radius: 6px;
            min-width: 22px;
            min-height: 22px;
            max-width: 22px;
            max-height: 22px;
            padding: 0px;
        }}
        """,
        # 画布视图背景固定灰色，衬托白色画布（符合 Windows 画图习惯）
        "canvas_view": f"""
        QGraphicsView {{
            background: #E0E0E0;
            border: 1px solid {t['border']};
            border-radius: 8px;
        }}
        """,
        "status_bar": f"""
        QLabel {{
            color: {t['text_secondary']};
            background: {t['status_bar_bg']};
            border-top: 1px solid {t['border']};
            padding: 4px 10px;
            font-size: 12px;
        }}
        """,
        "slider": f"""
        QSlider::groove:horizontal {{
            border: none;
            height: 4px;
            background: {t['border']};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {t['primary']};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {t['card_bg']};
            border: 1px solid {t['primary']};
            width: 14px;
            height: 14px;
            margin: -6px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {t['primary']};
        }}
        """,
        # 折叠面板（标题栏 + 内容区）；圆角 10px，边框 border，hover 用 list_hover_bg
        "collapsible_section": f"""
        QFrame#collapsible_section {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        QPushButton#collapsible_section_title {{
            background: transparent;
            border: none;
            border-radius: 10px;
            text-align: left;
            padding: 6px 12px;
            color: {t['text_primary']};
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton#collapsible_section_title:hover {{
            background: {t['list_hover_bg']};
            color: {t['primary']};
        }}
        QWidget#collapsible_section_content {{
            background: transparent;
        }}
        """,
        # 比例尺背景（toolbar_bg）
        "ruler": f"""
        QWidget {{
            background: {t['toolbar_bg']};
            border: 1px solid {t['border']};
        }}
        """,
        # 富文本工具栏（card_bg + border + 圆角 8px）
        "text_toolbar": f"""
        QFrame#text_format_toolbar {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
        }}
        QFontComboBox, QSpinBox {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 2px 6px;
            color: {t['text_primary']};
            font-size: 12px;
        }}
        QFontComboBox:hover, QSpinBox:hover {{
            border: 1px solid {t['primary']};
        }}
        QToolButton {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            color: {t['text_primary']};
        }}
        QToolButton:hover {{
            background: {t['list_hover_bg']};
            border-color: {t['border']};
        }}
        QToolButton:checked {{
            background: {t['primary']};
            color: #FFFFFF;
            border: 1px solid {t['primary']};
        }}
        QPushButton#text_color_btn {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 4px 8px;
            color: {t['text_primary']};
            font-weight: bold;
        }}
        QPushButton#text_color_btn:hover {{
            background: {t['selection_bg']};
            border-color: {t['primary']};
        }}
        """,
        # 右键菜单
        "context_menu": f"""
        QMenu {{
            background: {t['card_bg']};
            border: 1px solid {t['border']};
            border-radius: 8px;
            padding: 4px;
            color: {t['text_primary']};
            font-size: 13px;
        }}
        QMenu::item {{
            padding: 6px 24px;
            border-radius: 6px;
        }}
        QMenu::item:selected {{
            background: {t['selection_bg']};
            color: {t['selection_fg']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t['border']};
            margin: 4px 8px;
        }}
        """,
    }
