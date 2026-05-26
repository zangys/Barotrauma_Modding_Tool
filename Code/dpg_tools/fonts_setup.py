import dearpygui.dearpygui as dpg

from Code.app_vars import AppConfig


class FontManager:
    @staticmethod
    def load_fonts():
        font_base_path = AppConfig.get_data_root_path() / "fonts"
        default_font_path = font_base_path / "Monocraft" / "Monocraft.otf"
        with dpg.font_registry():
            with dpg.font(str(default_font_path), 13) as default_font:
                pass

        dpg.bind_font(default_font)
