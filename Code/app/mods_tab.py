import logging
import threading
from typing import Dict, List, Optional, Any, Tuple

import dearpygui.dearpygui as dpg

try:
    from Code.app import App
except ImportError:
    App = None

from Code.app_vars import AppConfig
from Code.handlers import ModManager
from Code.loc import Localization as loc
from Code.package import ModUnit

logger = logging.getLogger(__name__)


class UIColors:
    AUTHOR = (0, 102, 204)
    LICENSE = (169, 169, 169)
    VERSION = (34, 139, 34)
    ERROR = (255, 70, 70)
    WARNING = (255, 255, 100)
    DEFAULT = (255, 255, 255)
    LABEL = (100, 150, 250)
    VALUE = (200, 200, 250)
    SUCCESS = (50, 205, 50)


class ModsTab:

    active_mod_search_text: str = ""
    inactive_mod_search_text: str = ""

    TAG_TAB = "mod_tab"
    TAG_ACTIVE_LIST = "active_mods_child"
    TAG_INACTIVE_LIST = "inactive_mods_child"
    TAG_ERROR_TEXT = "error_count_text"
    TAG_WARNING_TEXT = "warning_count_text"
    TAG_RELOAD_STATUS = "reload_status_text"
    TAG_BTN_RELOAD = "reload_mods_button"

    @staticmethod
    def create():
        """Создает структуру вкладки модов."""
        with dpg.tab(label=loc.get_string("mod-tab-label"), parent="main_tab_bar", tag=ModsTab.TAG_TAB):
            ModsTab._create_toolbar()
            ModsTab._create_info_panel()
            
            dpg.add_separator()

            with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchSame, 
                           resizable=True, borders_innerV=True, scrollX=False, scrollY=False):
                
                dpg.add_table_column()
                dpg.add_table_column() 

                with dpg.table_row():
                    with dpg.group():
                        dpg.add_text(loc.get_string("label-active-mods"))
                        dpg.add_input_text(
                            hint=loc.get_string("input-hint-search"),
                            callback=ModsTab.on_search_changed,
                            user_data="active",
                            width=-1 
                        )
                        with dpg.child_window(
                            tag=ModsTab.TAG_ACTIVE_LIST,
                            drop_callback=ModsTab.on_mod_dropped,
                            user_data="active",
                            payload_type="MOD_DRAG",
                            border=True 
                        ):
                            pass

                    with dpg.group():
                        dpg.add_text(loc.get_string("label-inactive-mods"))
                        dpg.add_input_text(
                            hint=loc.get_string("input-hint-search"),
                            callback=ModsTab.on_search_changed,
                            user_data="inactive",
                            width=-1
                        )
                        with dpg.child_window(
                            tag=ModsTab.TAG_INACTIVE_LIST,
                            drop_callback=ModsTab.on_mod_dropped,
                            user_data="inactive",
                            payload_type="MOD_DRAG",
                            border=True
                        ):
                            pass

        ModsTab.render_mods()

    @staticmethod
    def _create_toolbar():
        with dpg.group(horizontal=True):
            dpg.add_button(
                label=loc.get_string("btn-sort-mods"),
                callback=ModsTab.sort_active_mods,
                tag="sort_button",
            )
            with dpg.tooltip("sort_button"):
                dpg.add_text(loc.get_string("btn-sort-mods-desc"))

            dpg.add_button(
                label=loc.get_string("btn-activate-all"),
                callback=ModsTab.on_activate_all_clicked,
                tag="activate_all_button",
            )
            with dpg.tooltip("activate_all_button"):
                dpg.add_text(loc.get_string("btn-activate-all-desc"))

            dpg.add_button(
                label=loc.get_string("btn-sync-workshop"),
                callback=ModsTab.on_reload_mods_clicked,
                tag=ModsTab.TAG_BTN_RELOAD
            )
            with dpg.tooltip(ModsTab.TAG_BTN_RELOAD):
                dpg.add_text(loc.get_string("tooltip-sync-workshop"))

            dpg.add_text("", tag=ModsTab.TAG_RELOAD_STATUS)

    @staticmethod
    def _create_info_panel():
        with dpg.group(horizontal=True):
            dpg.add_text(loc.get_string("label-directory-found"), color=UIColors.LABEL)
            dpg.add_text(
                str(AppConfig.get("barotrauma_dir", loc.get_string("base-not-set"))),
                color=UIColors.VALUE,
            )

        has_cs = AppConfig.get("has_cs")
        with dpg.group(horizontal=True):
            dpg.add_text(loc.get_string("label-enable-cs-scripting"), color=UIColors.LABEL)
            dpg.add_text(
                loc.get_string("base-yes") if has_cs else loc.get_string("base-no"),
                color=UIColors.SUCCESS if has_cs else UIColors.ERROR,
            )

        has_lua = AppConfig.get("has_lua")
        with dpg.group(horizontal=True):
            dpg.add_text(loc.get_string("label-lua-installed"), color=UIColors.LABEL)
            dpg.add_text(
                loc.get_string("base-yes") if has_lua else loc.get_string("base-no"),
                color=UIColors.SUCCESS if has_lua else UIColors.ERROR,
            )

        with dpg.group(horizontal=True):
            dpg.add_text(loc.get_string("label-errors"), tag=ModsTab.TAG_ERROR_TEXT)
            dpg.add_text("|")
            dpg.add_text(loc.get_string("label-warnings"), tag=ModsTab.TAG_WARNING_TEXT)


    @staticmethod
    def on_reload_mods_clicked():
        dpg.set_value(ModsTab.TAG_RELOAD_STATUS, "Загрузка...")
        dpg.configure_item(ModsTab.TAG_BTN_RELOAD, enabled=False)
        
        threading.Thread(target=ModsTab._thread_reload_mods, daemon=True).start()

    @staticmethod
    def _thread_reload_mods():
        try:
            ModManager.load_mods()
            ModsTab._dispatch_ui_update(ModsTab._finalize_reload, success=True)
        except Exception as e:
            logger.error(f"Error reloading mods: {e}", exc_info=True)
            ModsTab._dispatch_ui_update(ModsTab._finalize_reload, success=False)

    @staticmethod
    def _finalize_reload(success: bool):
        ModsTab.render_mods()
        status_text = "Готово!" if success else "Ошибка!"
        dpg.set_value(ModsTab.TAG_RELOAD_STATUS, status_text)
        dpg.configure_item(ModsTab.TAG_BTN_RELOAD, enabled=True)

    @staticmethod
    def on_activate_all_clicked():
        ModManager.activate_all_mods()
        ModsTab.render_mods()

    @staticmethod
    def on_process_errors_clicked():
        dpg.set_value(ModsTab.TAG_ERROR_TEXT, "...")
        dpg.set_value(ModsTab.TAG_WARNING_TEXT, "...")
        
        threading.Thread(target=ModsTab._thread_process_errors, daemon=True).start()

    @staticmethod
    def _thread_process_errors():
        ModManager.process_errors()
        ModsTab._dispatch_ui_update(ModsTab._finalize_error_processing)

    @staticmethod
    def _finalize_error_processing():
        ModsTab.render_mods()

    @staticmethod
    def on_search_changed(sender, app_data, user_data):
        val = app_data.lower()
        if user_data == "active":
            ModsTab.active_mod_search_text = val
        elif user_data == "inactive":
            ModsTab.inactive_mod_search_text = val
        ModsTab.render_mods()

    @staticmethod
    def sort_active_mods():
        try:
            ModManager.sort()
            ModsTab.render_mods()
        except Exception as e:
            logger.error(f"Sort failed: {e}", exc_info=True)

    @staticmethod
    def render_mods():
        ModsTab._render_mod_list(
            parent_tag=ModsTab.TAG_ACTIVE_LIST,
            mods=ModManager.active_mods,
            search_text=ModsTab.active_mod_search_text,
            status="active"
        )
        
        ModsTab._render_mod_list(
            parent_tag=ModsTab.TAG_INACTIVE_LIST,
            mods=ModManager.inactive_mods,
            search_text=ModsTab.inactive_mod_search_text,
            status="inactive"
        )

        error_count, warning_count = ModsTab.count_mods_with_issues()
        dpg.set_value(ModsTab.TAG_ERROR_TEXT, loc.get_string("error-count", count=error_count))
        dpg.set_value(ModsTab.TAG_WARNING_TEXT, loc.get_string("warning-count", count=warning_count))

    @staticmethod
    def _render_mod_list(parent_tag: str, mods: List[ModUnit], search_text: str, status: str):
        dpg.delete_item(parent_tag, children_only=True)
        
        for mod in mods:
            if search_text and search_text not in mod.name.lower():
                continue
            
            ModsTab._add_mod_item(mod, status, parent_tag)

    @staticmethod
    def _add_mod_item(mod: ModUnit, status: str, parent: str):
        safe_id = str(mod.id).replace(" ", "_")
        mod_group_tag = f"{safe_id}_{status}_group"
        text_color = UIColors.DEFAULT
        if mod.metadata.errors:
            text_color = UIColors.ERROR
        elif mod.metadata.warnings:
            text_color = UIColors.WARNING

        with dpg.group(tag=mod_group_tag, parent=parent):
            text_item = dpg.add_text(
                mod.name,
                color=text_color,
                drop_callback=ModsTab.on_mod_dropped,
                payload_type="MOD_DRAG",
                user_data={"mod_id": mod.id, "status": status},
            )
            with dpg.drag_payload(parent=text_item, payload_type="MOD_DRAG", drag_data={"mod_id": mod.id, "status": status}):
                dpg.add_text(f"{mod.name} ({status})")
            with dpg.tooltip(parent=text_item):
                ModsTab._build_mini_details(mod)
            with dpg.popup(parent=text_item, mousebutton=dpg.mvMouseButton_Right):
                dpg.add_button(
                    label=loc.get_string("btn-show-full-details"),
                    callback=lambda: ModsTab.show_details_window(mod),
                )
            
            dpg.add_separator()

    @staticmethod
    def _build_mini_details(mod: ModUnit):
        def _row(label_key, value, color=UIColors.DEFAULT):
            with dpg.group(horizontal=True):
                dpg.add_text(loc.get_string(label_key), color=UIColors.LABEL)
                dpg.add_text(str(value), color=color)

        _row("label-author", mod.metadata.author_name, UIColors.AUTHOR)
        _row("label-game-version", mod.metadata.game_version, UIColors.VERSION)
        
        if mod.metadata.errors:
            dpg.add_separator()
            dpg.add_text(loc.get_string("label-errors"), color=UIColors.ERROR)
            for err in mod.metadata.errors[:2]:
                dpg.add_text(f"- {err}", wrap=400)
            if len(mod.metadata.errors) > 2:
                dpg.add_text("...", color=UIColors.LABEL)

    @staticmethod
    def show_details_window(mod: ModUnit):
        window_tag = f"{mod.id}_details_window"
        if dpg.does_item_exist(window_tag):
            dpg.focus_item(window_tag)
            return

        with dpg.window(
            label=loc.get_string("label-mod-details-title", mod_name=mod.name),
            width=600, height=400,
            tag=window_tag,
            on_close=lambda: dpg.delete_item(window_tag),
        ):
            with dpg.group():
                ModsTab._details_row("label-mod-name", mod.name, UIColors.AUTHOR)
                ModsTab._details_row("label-modloader-id", mod.id, UIColors.VERSION)
                ModsTab._details_row("label-author", mod.metadata.author_name)
                ModsTab._details_row("label-is-local-mod", loc.get_string("base-yes") if mod.local else loc.get_string("base-no"))
            
            dpg.add_separator()

            if mod.metadata.errors:
                dpg.add_text(loc.get_string("label-errors"), color=UIColors.ERROR)
                for err in mod.metadata.errors:
                    dpg.add_text(f"• {err}", wrap=0)
                dpg.add_separator()

            if mod.metadata.warnings:
                dpg.add_text(loc.get_string("label-warnings"), color=UIColors.WARNING)
                for warn in mod.metadata.warnings:
                    dpg.add_text(f"• {warn}", wrap=0)
                dpg.add_separator()

            if mod.metadata.dependencies:
                dpg.add_text("Dependencies:", color=UIColors.LABEL)
                for dep in mod.metadata.dependencies:
                    dpg.add_text(f"• {dep.type}: {dep.id} (Optional: {dep.condition is not None})")

    @staticmethod
    def _details_row(label_key: str, value: str, val_color=UIColors.VALUE):
        with dpg.group(horizontal=True):
            dpg.add_text(loc.get_string(label_key), color=UIColors.LABEL)
            dpg.add_text(str(value), color=val_color)


    @staticmethod
    def on_mod_dropped(sender, app_data, user_data):
        drag_data = app_data
        drag_id = drag_data["mod_id"]
        drag_status = drag_data["status"]

        target_item_type = dpg.get_item_type(sender)
        target_status = None
        target_id = None

        if target_item_type == "mvAppItemType::mvChildWindow":
            target_status = user_data 
        elif target_item_type == "mvAppItemType::mvText":
            target_data = user_data 
            target_status = target_data.get("status")
            target_id = target_data.get("mod_id")

        if not target_status:
            return
        if drag_status != target_status:
            if target_status == "active":
                ModManager.activate_mod(drag_id)
            else:
                ModManager.deactivate_mod(drag_id)
            drag_status = target_status

        if drag_status == "active":
            if target_id and target_id != drag_id:
                ModManager.swap_active_mods(drag_id, target_id)
            elif target_item_type == "mvAppItemType::mvChildWindow":
                ModManager.move_active_mod_to_end(drag_id)
        else:
            if target_id and target_id != drag_id:
                ModManager.swap_inactive_mods(drag_id, target_id)
            elif target_item_type == "mvAppItemType::mvChildWindow":
                ModManager.move_inactive_mod_to_end(drag_id)

        ModsTab.render_mods()

    @staticmethod
    def count_mods_with_issues() -> Tuple[int, int]:
        error_count = 0
        warning_count = 0
        for mod in ModManager.active_mods:
            if mod.metadata.errors:
                error_count += 1
            if mod.metadata.warnings:
                warning_count += 1
        return error_count, warning_count

    @staticmethod
    def _dispatch_ui_update(callback, *args, **kwargs):

        if App and hasattr(App, "ui_tasks_queue"):
            App.ui_tasks_queue.put(lambda: callback(*args, **kwargs))
        else:
            logging.warning("App.ui_tasks_queue not found, executing UI update directly from thread.")
            callback(*args, **kwargs)