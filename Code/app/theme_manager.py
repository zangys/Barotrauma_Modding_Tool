"""
Менеджер тем приложения.

Содержит определения цветовых палитр и логику применения тем к DearPyGui.
"""
import dearpygui.dearpygui as dpg
from Code.app_vars import AppConfig
from Code.app.ui_utils import UIColors


# Маппинг имён ключей палитры → констант DearPyGui
COLOR_MAP = {
    "window_bg": dpg.mvThemeCol_WindowBg,
    "text": dpg.mvThemeCol_Text,
    "button": dpg.mvThemeCol_Button,
    "button_hovered": dpg.mvThemeCol_ButtonHovered,
    "button_active": dpg.mvThemeCol_ButtonActive,
    "frame_bg": dpg.mvThemeCol_FrameBg,
    "title_bg": dpg.mvThemeCol_TitleBg,
    "title_bg_active": dpg.mvThemeCol_TitleBgActive,
    "tab": dpg.mvThemeCol_Tab,
    "tab_hovered": dpg.mvThemeCol_TabHovered,
    "tab_active": dpg.mvThemeCol_TabActive,
    "header": dpg.mvThemeCol_Header,
    "header_hovered": dpg.mvThemeCol_HeaderHovered,
    "header_active": dpg.mvThemeCol_HeaderActive,
    "child_bg": dpg.mvThemeCol_ChildBg,
    "popup_bg": dpg.mvThemeCol_PopupBg,
    "border": dpg.mvThemeCol_Border,
    "border_shadow": dpg.mvThemeCol_BorderShadow,
    "menu_bar_bg": dpg.mvThemeCol_MenuBarBg,
    "scrollbar_bg": dpg.mvThemeCol_ScrollbarBg,
    "scrollbar_grab": dpg.mvThemeCol_ScrollbarGrab,
    "scrollbar_grab_hovered": dpg.mvThemeCol_ScrollbarGrabHovered,
    "scrollbar_grab_active": dpg.mvThemeCol_ScrollbarGrabActive,
    "check_mark": dpg.mvThemeCol_CheckMark,
    "slider_grab": dpg.mvThemeCol_SliderGrab,
    "slider_grab_active": dpg.mvThemeCol_SliderGrabActive,
    "table_header_bg": dpg.mvThemeCol_TableHeaderBg,
    "table_border_strong": dpg.mvThemeCol_TableBorderStrong,
    "table_border_light": dpg.mvThemeCol_TableBorderLight,
    "table_row_bg": dpg.mvThemeCol_TableRowBg,
    "table_row_bg_alt": dpg.mvThemeCol_TableRowBgAlt,
    "text_selected_bg": dpg.mvThemeCol_TextSelectedBg,
    "nav_highlight": dpg.mvThemeCol_NavHighlight,
}


# Определение цветовых палитр для каждой темы
PALETTES = {
    "dark": {
        "window_bg": (30, 30, 30),
        "text": (255, 255, 255),
        "button": (60, 60, 60),
        "button_hovered": (80, 80, 80),
        "button_active": (100, 100, 100),
        "frame_bg": (45, 45, 45),
        "title_bg": (40, 40, 40),
        "title_bg_active": (50, 50, 50),
        "tab": (40, 40, 40),
        "tab_hovered": (60, 60, 60),
        "tab_active": (80, 80, 80),
        "header": (50, 50, 50),
        "header_hovered": (60, 60, 60),
        "header_active": (70, 70, 70),
        "child_bg": (35, 35, 35),
        "popup_bg": (40, 40, 40),
        "border": (60, 60, 60),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (40, 40, 40),
        "scrollbar_bg": (30, 30, 30),
        "scrollbar_grab": (60, 60, 60),
        "scrollbar_grab_hovered": (80, 80, 80),
        "scrollbar_grab_active": (100, 100, 100),
        "check_mark": (100, 150, 250),
        "table_header_bg": (50, 50, 50),
        "table_border_strong": (60, 60, 60),
        "table_border_light": (60, 60, 60),
        "table_row_bg": (30, 30, 30),
        "table_row_bg_alt": (35, 35, 35),
        "text_selected_bg": (60, 60, 60),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (255, 255, 255),
        "ui_label": (100, 150, 250),
        "ui_value": (200, 200, 250),
        "ui_header": (255, 215, 0),
        "ui_author": (0, 102, 204),
        "ui_error": (255, 70, 70),
        "ui_warning": (255, 255, 100),
        "ui_success": (50, 205, 50),
        "ui_license": (169, 169, 169),
        "ui_version": (34, 139, 34),
    },
    "light": {
        "window_bg": (240, 240, 240),
        "text": (20, 20, 20),
        "button": (200, 200, 200),
        "button_hovered": (180, 180, 180),
        "button_active": (160, 160, 160),
        "frame_bg": (255, 255, 255),
        "title_bg": (220, 220, 220),
        "title_bg_active": (200, 200, 200),
        "tab": (220, 220, 220),
        "tab_hovered": (200, 200, 200),
        "tab_active": (180, 180, 180),
        "header": (200, 200, 200),
        "header_hovered": (180, 180, 180),
        "header_active": (160, 160, 160),
        "child_bg": (240, 240, 240),
        "popup_bg": (255, 255, 255),
        "border": (180, 180, 180),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (230, 230, 230),
        "scrollbar_bg": (240, 240, 240),
        "scrollbar_grab": (200, 200, 200),
        "scrollbar_grab_hovered": (180, 180, 180),
        "scrollbar_grab_active": (160, 160, 160),
        "check_mark": (0, 102, 204),
        "slider_grab": (200, 200, 200),
        "slider_grab_active": (180, 180, 180),
        "table_header_bg": (220, 220, 220),
        "table_border_strong": (200, 200, 200),
        "table_border_light": (200, 200, 200),
        "table_row_bg": (250, 250, 250),
        "table_row_bg_alt": (245, 245, 245),
        "text_selected_bg": (180, 200, 255),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (20, 20, 20),
        "ui_label": (0, 0, 150),
        "ui_value": (50, 50, 50),
        "ui_header": (0, 0, 0),
        "ui_author": (0, 51, 102),
        "ui_error": (200, 0, 0),
        "ui_warning": (200, 150, 0),
        "ui_success": (0, 150, 0),
        "ui_license": (100, 100, 100),
        "ui_version": (0, 100, 0),
    },
    "oceanic": {
        "window_bg": (10, 30, 40),
        "text": (220, 240, 255),
        "button": (30, 80, 100),
        "button_hovered": (40, 100, 120),
        "button_active": (50, 120, 140),
        "frame_bg": (20, 50, 60),
        "title_bg": (15, 40, 50),
        "title_bg_active": (25, 60, 75),
        "tab": (20, 50, 60),
        "tab_hovered": (30, 70, 80),
        "tab_active": (40, 90, 100),
        "header": (30, 70, 90),
        "header_hovered": (40, 90, 110),
        "header_active": (50, 110, 130),
        "child_bg": (15, 35, 45),
        "popup_bg": (15, 40, 50),
        "border": (30, 80, 100),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (15, 40, 50),
        "scrollbar_bg": (10, 30, 40),
        "scrollbar_grab": (30, 80, 100),
        "scrollbar_grab_hovered": (40, 100, 120),
        "scrollbar_grab_active": (50, 120, 140),
        "check_mark": (100, 255, 200),
        "table_header_bg": (20, 60, 80),
        "table_border_strong": (30, 80, 100),
        "table_border_light": (30, 80, 100),
        "table_row_bg": (10, 30, 40),
        "table_row_bg_alt": (15, 35, 45),
        "text_selected_bg": (40, 90, 110),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (220, 240, 255),
        "ui_label": (100, 255, 200),
        "ui_value": (200, 255, 255),
        "ui_header": (255, 215, 0),
        "ui_author": (135, 206, 250),
        "ui_error": (255, 100, 100),
        "ui_warning": (255, 255, 100),
        "ui_success": (100, 255, 200),
        "ui_license": (150, 200, 200),
        "ui_version": (100, 200, 150),
    },
    "crimson": {
        "window_bg": (25, 5, 5),
        "text": (255, 200, 200),
        "button": (80, 20, 20),
        "button_hovered": (100, 30, 30),
        "button_active": (120, 40, 40),
        "frame_bg": (40, 10, 10),
        "title_bg": (60, 10, 10),
        "title_bg_active": (100, 20, 20),
        "tab": (60, 10, 10),
        "tab_hovered": (80, 20, 20),
        "tab_active": (100, 30, 30),
        "header": (80, 20, 20),
        "header_hovered": (100, 30, 30),
        "header_active": (120, 40, 40),
        "child_bg": (20, 5, 5),
        "popup_bg": (25, 10, 10),
        "border": (100, 30, 30),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (30, 5, 5),
        "scrollbar_bg": (20, 5, 5),
        "scrollbar_grab": (60, 20, 20),
        "scrollbar_grab_hovered": (80, 30, 30),
        "scrollbar_grab_active": (100, 40, 40),
        "check_mark": (255, 69, 0),
        "table_header_bg": (60, 10, 10),
        "table_border_strong": (80, 30, 30),
        "table_border_light": (80, 30, 30),
        "table_row_bg": (30, 10, 10),
        "table_row_bg_alt": (35, 15, 15),
        "text_selected_bg": (100, 40, 40),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (255, 200, 200),
        "ui_label": (255, 100, 100),
        "ui_value": (255, 150, 150),
        "ui_header": (255, 69, 0),
        "ui_author": (255, 100, 100),
        "ui_error": (255, 200, 200),
        "ui_warning": (255, 255, 0),
        "ui_success": (255, 150, 100),
        "ui_license": (200, 150, 150),
        "ui_version": (255, 100, 50),
    },
    "forest": {
        "window_bg": (20, 30, 20),
        "text": (220, 255, 220),
        "button": (34, 70, 34),
        "button_hovered": (40, 90, 40),
        "button_active": (50, 110, 50),
        "frame_bg": (30, 50, 30),
        "title_bg": (25, 60, 25),
        "title_bg_active": (35, 80, 35),
        "tab": (30, 60, 30),
        "tab_hovered": (40, 80, 40),
        "tab_active": (50, 100, 50),
        "header": (30, 70, 30),
        "header_hovered": (40, 90, 40),
        "header_active": (50, 110, 50),
        "child_bg": (25, 40, 25),
        "popup_bg": (25, 45, 25),
        "border": (50, 100, 50),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (25, 45, 25),
        "scrollbar_bg": (20, 35, 20),
        "scrollbar_grab": (40, 80, 40),
        "scrollbar_grab_hovered": (50, 100, 50),
        "scrollbar_grab_active": (60, 120, 60),
        "check_mark": (50, 205, 50),
        "table_header_bg": (30, 60, 30),
        "table_border_strong": (50, 100, 50),
        "table_border_light": (50, 100, 50),
        "table_row_bg": (25, 45, 25),
        "table_row_bg_alt": (30, 50, 30),
        "text_selected_bg": (50, 100, 50),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (220, 255, 220),
        "ui_label": (144, 238, 144),
        "ui_value": (152, 251, 152),
        "ui_header": (50, 205, 50),
        "ui_author": (143, 188, 143),
        "ui_error": (255, 100, 100),
        "ui_warning": (255, 215, 0),
        "ui_success": (50, 205, 50),
        "ui_license": (150, 200, 150),
        "ui_version": (100, 180, 100),
    },
    "amethyst": {
        "window_bg": (20, 10, 30),
        "text": (240, 220, 255),
        "button": (60, 20, 80),
        "button_hovered": (80, 30, 100),
        "button_active": (100, 40, 120),
        "frame_bg": (40, 20, 60),
        "title_bg": (40, 10, 60),
        "title_bg_active": (60, 20, 90),
        "tab": (40, 20, 60),
        "tab_hovered": (60, 30, 80),
        "tab_active": (80, 40, 100),
        "header": (60, 30, 80),
        "header_hovered": (80, 40, 100),
        "header_active": (100, 50, 120),
        "child_bg": (25, 15, 35),
        "popup_bg": (30, 20, 45),
        "border": (80, 40, 100),
        "border_shadow": (0, 0, 0, 0),
        "menu_bar_bg": (30, 15, 45),
        "scrollbar_bg": (20, 10, 30),
        "scrollbar_grab": (60, 30, 80),
        "scrollbar_grab_hovered": (80, 40, 100),
        "scrollbar_grab_active": (100, 50, 120),
        "check_mark": (255, 0, 255),
        "table_header_bg": (50, 20, 70),
        "table_border_strong": (80, 40, 100),
        "table_border_light": (80, 40, 100),
        "table_row_bg": (30, 20, 40),
        "table_row_bg_alt": (35, 25, 45),
        "text_selected_bg": (100, 50, 120),
        "nav_highlight": (0, 0, 0, 0),
        # UIColors
        "ui_default": (240, 220, 255),
        "ui_label": (218, 112, 214),
        "ui_value": (238, 130, 238),
        "ui_header": (255, 0, 255),
        "ui_author": (186, 85, 211),
        "ui_error": (255, 50, 50),
        "ui_warning": (255, 255, 100),
        "ui_success": (200, 100, 255),
        "ui_license": (180, 150, 200),
        "ui_version": (180, 100, 200),
    },
}


class ThemeManager:
    """Менеджер тем для DearPyGui."""

    _current_theme_tag = "global_theme"

    THEMES = {
        "Dark": "dark",
        "Light": "light",
        "Oceanic": "oceanic",
        "Crimson": "crimson",
        "Forest": "forest",
        "Amethyst": "amethyst",
    }

    @classmethod
    def init(cls) -> None:
        """Инициализирует менеджер тем и применяет сохранённую тему."""
        saved_theme = AppConfig.get("app_theme", "Dark")
        if saved_theme not in cls.THEMES:
            saved_theme = "Dark"
        cls.apply_theme(saved_theme)

    @classmethod
    def get_themes(cls) -> list:
        """Возвращает список доступных тем."""
        return list(cls.THEMES.keys())

    @classmethod
    def apply_theme(cls, theme_name: str) -> None:
        """Применяет указанную тему к приложению.

        Args:
            theme_name: Название темы (ключ из THEMES).
        """
        if theme_name not in cls.THEMES:
            return

        AppConfig.set("app_theme", theme_name)

        # Удаляем старую тему
        if dpg.does_item_exist(cls._current_theme_tag):
            dpg.delete_item(cls._current_theme_tag)

        palette_key = cls.THEMES[theme_name]
        palette = PALETTES.get(palette_key, PALETTES["dark"])

        # Создаём новую тему
        with dpg.theme(tag=cls._current_theme_tag):
            with dpg.theme_component(dpg.mvAll):
                cls._apply_palette(palette)

                # Общие стили
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 5, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 4, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 4, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4, category=dpg.mvThemeCat_Core)

        # Применяем глобально
        dpg.bind_theme(cls._current_theme_tag)

        # Обновляем UIColors
        cls._update_ui_colors(palette)

    @staticmethod
    def _apply_palette(palette: dict) -> None:
        """Применяет цвета из палитры к теме DearPyGui.

        Args:
            palette: Словарь с цветами.
        """
        for key, color in palette.items():
            if key.startswith("ui_"):
                continue  # UIColors обрабатываются отдельно
            dpg_const = COLOR_MAP.get(key)
            if dpg_const is not None:
                dpg.add_theme_color(dpg_const, color)

    @staticmethod
    def _update_ui_colors(palette: dict) -> None:
        """Обновляет класс UIColors значениями из палитры.

        Args:
            palette: Словарь с цветами.
        """
        UIColors.DEFAULT = palette.get("ui_default", (255, 255, 255))
        UIColors.LABEL = palette.get("ui_label", (100, 150, 250))
        UIColors.VALUE = palette.get("ui_value", (200, 200, 250))
        UIColors.HEADER = palette.get("ui_header", (255, 215, 0))
        UIColors.AUTHOR = palette.get("ui_author", (0, 102, 204))
        UIColors.ERROR = palette.get("ui_error", (255, 70, 70))
        UIColors.WARNING = palette.get("ui_warning", (255, 255, 100))
        UIColors.SUCCESS = palette.get("ui_success", (50, 205, 50))
        UIColors.LICENSE = palette.get("ui_license", (169, 169, 169))
        UIColors.VERSION = palette.get("ui_version", (34, 139, 34))
