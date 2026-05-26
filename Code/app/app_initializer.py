import sys

import dearpygui.dearpygui as dpg

from Code.app_vars import AppConfig
from Code.dpg_tools import FontManager
from Code.loc import Localization as loc

from .app_interface import AppInterface
from .error_handler import ErrorHandler


class AppInitializer:
    @staticmethod
    def init():
        AppInitializer._init_dpg()
        AppInitializer._init_viewport()
        AppInitializer._init_fronts()
        AppInitializer._init_error_handler()
        AppInterface.initialize()

    @staticmethod
    def _init_dpg():
        dpg.create_context()
        dpg.setup_dearpygui()

    @staticmethod
    def _init_viewport():
        try:
            size = AppConfig.get("last_viewport_size", "600 400")
            width, height = size.split(" ")
            width, height = int(width), int(height)
        except Exception:
            width, height = 600, 400
        dpg.create_viewport(
            title=loc.get_string("viewport-name"),
            width=width,
            min_width=600,
            height=height,
            min_height=400,
        )
        dpg.show_viewport()

    @staticmethod
    def _init_fronts():
        FontManager.load_fonts()

    @staticmethod
    def _init_error_handler():
        sys.excepthook = ErrorHandler.global_exception_handler
