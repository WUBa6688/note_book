"""
Zhuibook Theme System
Three themes: 🌿 MATCHA / 🍋 LEMON / ☁️ FOG
All colors centralized, no hardcoded tokens in widgets.
"""
from __future__ import annotations
from typing import Dict, Any


THEMES: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# 🌿 MATCHA (抹茶绿 — 默认主题，清新护眼浅绿色系)
# ---------------------------------------------------------------------------
THEMES["matcha"] = {
    "name": "🌿 抹茶绿",

    # ---- 主色（温和抹茶绿，低饱和不刺眼） ----
    "primary":              "#5A9E7E",   # 主强调色（深抹茶）
    "primary_text":         "#4B8A6D",   # 主色文字（略深）
    "primary_light":        "#6CB18F",   # 浅主色
    "primary_gradient_top": "#6EBD98",   # 渐变顶部
    "primary_gradient_bot": "#529477",   # 渐变底部
    "primary_hover_top":    "#60AE87",
    "primary_hover_bot":    "#46856A",
    "primary_pressed_top":  "#549F7D",
    "primary_pressed_bot":  "#3D7860",

    # ---- 背景层 ----
    "global_bg":            "#F2F7F0",   # 最外层（MainWindow）
    "sidebar_bg":           "#EFF5EC",   # 侧边栏底
    "sidebar_header_top":   "#E6F0E1",   # 侧栏 header 渐变顶
    "sidebar_header_bot":   "#EFF5EC",   # 侧栏 header 渐变底
    "editor_header_bg":     "#FFFFFF",   # 编辑区 header
    "editor_bg":            "#FFFFFF",   # 编辑内容区
    "toolbar_bg":           "#F0F5ED",   # 工具栏容器背景
    "status_bar_bg":        "#F2F7F0",   # 状态栏

    # ---- 边框 / 分隔 ----
    "border":               "#D6E0D1",   # 柔和分隔
    "border_strong":        "#C5D2BF",   # hover 时边框

    # ---- 文本 ----
    "text_primary":         "#2E3630",   # 正文深墨绿灰（不是纯黑，更温和）
    "text_secondary":       "#828E86",   # 次级：字数、分类标签
    "text_tertiary":        "#B9C2BB",   # 分隔点 dot
    "title_color":          "#5A9E7E",   # 侧栏 logo、标题输入

    # ---- 选中 / hover 底 ----
    "selection_bg":         "#DFEEE4",   # 文本选中淡绿底
    "selection_fg":         "#4B8A6D",   # 选中文本字色
    "list_hover_bg":        "#E7EEE3",   # 笔记项 hover（暖绿米）
    "list_selected_bg":     "#E5EEE7",   # 笔记项选中底
    "list_selected_left":   "#5A9E7E",   # 选中左侧主色竖条
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
    "save_color":           "#4B9A6D",   # 已保存提示绿色
}

# ---------------------------------------------------------------------------
# 🍋 LEMON (柠檬奶黄 — 温暖浅黄色系)
# ---------------------------------------------------------------------------
THEMES["lemon"] = {
    "name": "🍋 柠檬奶黄",

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
# ☁️ FOG (雾蓝 — 原冷蓝色系，作为保留可选)
# ---------------------------------------------------------------------------
THEMES["fog"] = {
    "name": "☁️  雾蓝",

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
            background: #FFFFFF;
            font-size: 13px;
            color: {t['text_primary']};
            selection-background-color: {t['selection_bg']};
            selection-color: {t['selection_fg']};
        }}
        QLineEdit:hover {{ border: 1px solid {t['border_strong']}; }}
        QLineEdit:focus {{
            border: 1px solid {t['primary']};
            background: #FFFFFF;
        }}
        """,
        "combo": f"""
        QComboBox {{
            padding: 8px 12px;
            border: 1px solid {t['border']};
            border-radius: 8px;
            background: #FFFFFF;
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
            background: #FFFFFF;
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
            background: #FFFFFF;
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
            background: #FFFFFF;
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
            background: #FFFFFF;
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
            background: #FFFFFF;
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
        "theme_btn": f"""
        QToolButton {{
            padding: 5px 12px;
            border: 1px solid {t['border']};
            border-radius: 7px;
            background: #FFFFFF;
            font-size: 13px;
            color: {t['primary_text']};
        }}
        QToolButton:hover {{
            background: {t['selection_bg']};
            border: 1px solid {t['primary']};
        }}
        """,
    }
