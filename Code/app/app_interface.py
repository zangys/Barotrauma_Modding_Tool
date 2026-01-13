import json
import logging
import threading
import webbrowser

import dearpygui.dearpygui as dpg
import requests

import Code.dpg_tools as dpg_tools
from Code.app_vars import AppConfig
from Code.app.conflicts_tab import ConflictsTab
from Code.app.rules_tab import RulesTab
from Code.app.auto_updater import AutoUpdater
from Code.game import Game
from Code.handlers import ModManager
from Code.handlers.user_rules import UserRulesManager
from Code.app.theme_manager import ThemeManager
from Code.loc import Localization as loc

from .mods_tab import ModsTab
from .settings_tab import SettingsTab


logger = logging.getLogger(__name__)


class AppInterface:
    TAG_VERSION_ITEM = "menu_item_version_check"

    @staticmethod
    def initialize():
        AppInterface._create_viewport_menu_bar()
        AppInterface._create_main_window()
        
        ModManager.load_mods()
        UserRulesManager.init()
        ThemeManager.init()
        AutoUpdater.init()

        SettingsTab.create()
        ModsTab.create()
        ConflictsTab.create()
        RulesTab.create()

        # Устанавливаем активную вкладку
        if dpg.does_item_exist("mod_tab"):
            dpg.set_value("main_tab_bar", "mod_tab")

        dpg.set_viewport_resize_callback(AppInterface._res_callback)
        dpg_tools.rc_windows()

        # Асинхронная проверка версии
        threading.Thread(target=AppInterface._async_check_version, daemon=True).start()

    @staticmethod
    def _res_callback() -> None:
        dpg_tools.rc_windows()
        # ИСПРАВЛЕНИЕ 1: Сохраняем в конфиг Python, а не в DPG виджет
        AppConfig.set(
            "last_viewport_size", 
            f"{dpg.get_viewport_width()} {dpg.get_viewport_height()}"
        )

    @staticmethod
    def _create_main_window():
        with dpg.window(
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            tag="main_window",
        ):
            dpg.add_tab_bar(tag="main_tab_bar")

    @staticmethod
    def _create_viewport_menu_bar():
        with dpg.viewport_menu_bar(tag="main_view_bar"):
            dpg.add_menu_item(
                label=loc.get_string("menu-bar-start-game"),
                callback=AppInterface.start_game,
            )

            dpg.add_menu_item(
                label=loc.get_string("cac-window-name"),
                callback=AppInterface.create_cac_window,
            )

            dpg.add_menu_item(
                label=f"{loc.get_string('cur-version-latest')} ...",
                tag=AppInterface.TAG_VERSION_ITEM,
                callback=lambda: webbrowser.open(
                    "https://github.com/zangys/Barotrauma_Modding_Tool_Enchanted/releases/latest"
                ),
                enabled=False, 
            )

            if AppConfig.get("debug", False):
                dpg.add_menu_item(
                    label="Console",
                    callback=AppInterface._setup_console,
                )

    @staticmethod
    def _async_check_version():
        """Асинхронно проверяет версию через AutoUpdater."""
        update_info = AutoUpdater.check_for_updates()
        is_latest = update_info is None  # None означает что уже на последней версии

        AppInterface._update_version_ui(is_latest, update_info)

    @staticmethod
    def _update_version_ui(is_latest: bool | None, update_info: dict | None = None):
        """Обновляет пункт меню с версией и показывает диалог обновления."""
        if is_latest is True:
            status = loc.get_string("base-yes")
            should_enable = False 
        elif is_latest is False:
            status = loc.get_string("base-no")
            should_enable = True
        else:
            status = loc.get_string("base-unknown")
            should_enable = True

        new_label = f"{loc.get_string('cur-version-latest')} {status}"
        
        if dpg.does_item_exist(AppInterface.TAG_VERSION_ITEM):
            # Меняем callback на показ диалога обновления
            def show_update_or_github():
                if AutoUpdater.is_update_available():
                    AutoUpdater.show_update_dialog()
                else:
                    webbrowser.open(
                        "https://github.com/zangys/Barotrauma_Modding_Tool_Enchanted/releases/latest"
                    )

            dpg.configure_item(
                AppInterface.TAG_VERSION_ITEM, 
                label=new_label, 
                enabled=should_enable,
                callback=show_update_or_github,
            )

    @staticmethod
    def _process_command(sender, app_data, user_data):
        try:
            command = app_data.strip()
            if command:
                AppInterface._append_console_output(f"> {command}")
                try:
                    exec_result = eval(command, globals())
                    if exec_result is not None:
                        AppInterface._append_console_output(str(exec_result))
                except SyntaxError:
                    exec(command, globals())
                    
        except Exception as e:
            AppInterface._append_console_output(f"Error: {e}")

        finally:
            dpg.set_value(sender, "")
            dpg.focus_item(sender)

    @staticmethod
    def _append_console_output(text):
        if dpg.does_item_exist("console_output"):
            dpg.add_text(text, parent="console_output", wrap=0)
            if dpg.does_item_exist("console_window"):
                y_max = dpg.get_y_scroll_max("console_window")
                dpg.set_y_scroll("console_window", y_max)

    @staticmethod
    def _setup_console():
        if dpg.does_item_exist("debug_console"):
            dpg.delete_item("debug_console")

        with dpg.window(label="Debug Console", tag="debug_console", width=600, height=400):
            with dpg.child_window(
                tag="console_window", border=True, autosize_x=True, height=-30
            ):
                with dpg.group(tag="console_output"):
                    dpg.add_text("Debug Console Initialized")

            dpg.add_input_text(
                label="Command",
                tag="console_input",
                on_enter=True,
                callback=AppInterface._process_command,
                width=-1
            )
            dpg.focus_item("console_input")

        dpg_tools.rc_windows()

    @staticmethod
    def start_game():
        ModManager.save_mods()

        game_dir = AppConfig.get("barotrauma_dir", None)
        if game_dir is None:
            AppInterface.show_error(loc.get_string("error-game-dir-not-set"))
            return

        skip_intro = AppConfig.get("game_config_skip_intro", False)
        auto_install_lua = AppConfig.get("game_config_auto_lua", False)
        try:
            Game.run_game(auto_install_lua, skip_intro)  # type: ignore
        except Exception as err:
            logger.error(f"Failed to start game: {err}")
            AppInterface.show_error(str(err))

    @staticmethod
    def show_error(message):
        with dpg.window(label="Error", modal=True, width=400, height=150):
            dpg.add_text(message, wrap=380)
            dpg.add_button(label="OK", width=75, callback=lambda s, a, u: dpg.delete_item(dpg.get_item_parent(s)))

    @staticmethod
    def create_cac_window():
        if dpg.does_item_exist("cac_window"):
            dpg.focus_item("cac_window")
            return

        contributors_path = AppConfig.get_data_root_path() / "contributors.json"

        try:
            with open(contributors_path, "r", encoding="utf-8") as f:
                contributors_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load contributors: {e}")
            return

        category_config = {
            "сaс-devs": {
                "name_field": "name",
                "info_field": "role",
                "get_info": lambda v: loc.get_string(v),
            },
            "сaс-translators": {
                "name_field": "name",
                "info_field": "code",
                "get_info": lambda v: loc.get_string("cac-translators-thx", lang_code=loc.get_string(f"lang_code-{v}")),
            },
            "cac-special-thanks": {
                "name_field": "to",
                "info_field": "desc",
                "get_info": lambda v: loc.get_string(v),
            },
        }

        with dpg.window(
            label=loc.get_string("cac-window-name"),
            tag="cac_window",
            width=500,
            height=600,
            no_collapse=True
        ):
            for category_label, contributors_list in contributors_data.items():
                if not isinstance(contributors_list, list): continue
                
                with dpg.collapsing_header(label=loc.get_string(category_label), default_open=True):
                    conf = category_config.get(category_label)
                    
                    for person in contributors_list:
                        name = person.get(conf["name_field"], "Unknown") if conf else "Unknown"
                        
                        info_text = ""
                        if conf and conf["info_field"] in person:
                            raw_info = person[conf["info_field"]]
                            try:
                                info_text = conf["get_info"](raw_info)
                            except Exception:
                                info_text = str(raw_info)

                        with dpg.group(horizontal=True):
                            dpg.add_text(f"• {name}", color=(0, 150, 255))
                            if info_text:
                                dpg.add_text(f"- {info_text}", color=(200, 200, 200), wrap=350)

    @staticmethod
    def rebuild_interface():
        current_tab = dpg.get_value("main_tab_bar")

        dpg.delete_item("main_tab_bar", children_only=True)
        dpg.delete_item("main_view_bar")

        AppInterface._create_viewport_menu_bar()
        SettingsTab.create()
        ModsTab.create()
        ConflictsTab.create()
        RulesTab.create() # Added as per instruction

        if current_tab:
            dpg.set_value("main_tab_bar", current_tab)

        dpg_tools.rc_windows()