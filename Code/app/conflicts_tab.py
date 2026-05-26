
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import dearpygui.dearpygui as dpg

from Code.handlers import ModManager
from Code.loc import Localization as loc
from Code.package import ModUnit

logger = logging.getLogger(__name__)


from Code.app.ui_utils import UIColors


class ConflictsTab:
    TAG_TAB = "conflicts_tab"
    TAG_TABLE = "conflicts_table"
    TAG_FILTER_INPUT = "conflicts_filter_input"
    TAG_STATUS = "conflicts_status_text"

    _filter_text: str = ""

    @staticmethod
    def create():
        with dpg.tab(label=loc.get_string("tab-conflicts"), parent="main_tab_bar", tag=ConflictsTab.TAG_TAB):
            with dpg.group(horizontal=True):
                dpg.add_button(label=loc.get_string("btn-scan-conflicts"), callback=ConflictsTab.scan_conflicts)
                dpg.add_input_text(
                    label=loc.get_string("label-filter"),
                    tag=ConflictsTab.TAG_FILTER_INPUT,
                    width=200,
                    callback=ConflictsTab.on_filter_changed,
                )
                dpg.add_text("", tag=ConflictsTab.TAG_STATUS)

            dpg.add_separator()

            with dpg.table(
                header_row=True,
                policy=dpg.mvTable_SizingStretchSame,
                resizable=True,
                borders_innerV=True,
                tag=ConflictsTab.TAG_TABLE,
                scrollY=True,
            ):
                dpg.add_table_column(label=loc.get_string("col-identifier"))
                dpg.add_table_column(label=loc.get_string("col-status"), width_fixed=True, init_width_or_weight=100)
                dpg.add_table_column(label=loc.get_string("col-overridden-by"))

    @staticmethod
    def on_filter_changed(sender, app_data):
        ConflictsTab._filter_text = app_data.lower()
        ConflictsTab.scan_conflicts()

    @staticmethod
    def _is_intentional_patch(mods: List[ModUnit]) -> bool:
        patch_keywords = ("patch", "compat")
        names_lower = [m.name.lower() for m in mods]
        for i, name in enumerate(names_lower):
            if any(k in name for k in patch_keywords):
                for j, other in enumerate(names_lower):
                    if i != j and other in name:
                        return True
        return False

    @staticmethod
    def scan_conflicts():
        # Clear existing rows
        if dpg.does_item_exist(ConflictsTab.TAG_TABLE):
            children = dpg.get_item_children(ConflictsTab.TAG_TABLE, slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)

        dpg.set_value(ConflictsTab.TAG_STATUS, loc.get_string("status-scanning"))

        active_mods = ModManager.active_mods
        override_map: Dict[str, List[ModUnit]] = defaultdict(list)

        # 1. Collect Overrides
        for mod in active_mods:
            excluded_ids = {"togglevanillacontent", "load_screen.xml"}
            
            for oid in mod.override_id:
                if oid.lower() in excluded_ids:
                    continue
                override_map[oid].append(mod)

        # 2. Filter and Process
        conflict_count = 0
        sorted_keys = sorted(override_map.keys())

        for oid in sorted_keys:
            if ConflictsTab._filter_text and ConflictsTab._filter_text not in oid.lower():
                continue

            mods_involved = override_map[oid]
            count = len(mods_involved)

            if count > 1:
                if ConflictsTab._is_intentional_patch(mods_involved):
                    status_text = loc.get_string("status-override")
                    status_color = UIColors.VALUE
                else:
                    status_text = loc.get_string("status-conflict")
                    status_color = UIColors.ERROR
                    conflict_count += 1
            else:
                status_text = loc.get_string("status-override")
                status_color = UIColors.VALUE
            
            with dpg.table_row(parent=ConflictsTab.TAG_TABLE):
                dpg.add_text(oid)
                dpg.add_text(status_text, color=status_color)
                
                with dpg.group():
                    for i, mod in enumerate(mods_involved):
                        is_winner = (i == count - 1)
                        color = UIColors.SUCCESS if is_winner and count > 1 else UIColors.DEFAULT
                        
                        dpg.add_text(f"[{mod.load_order}] {mod.name}", color=color)

        if conflict_count > 0:
            dpg.set_value(ConflictsTab.TAG_STATUS, loc.get_string("status-found-conflicts", count=conflict_count))
        else:
            dpg.set_value(ConflictsTab.TAG_STATUS, loc.get_string("status-no-conflicts"))

