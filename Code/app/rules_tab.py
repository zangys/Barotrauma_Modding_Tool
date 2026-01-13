
import dearpygui.dearpygui as dpg
from typing import List, Optional
from Code.loc import Localization as loc
from Code.handlers.mod_manager import ModManager
from Code.handlers.user_rules import UserRulesManager
from Code.app.ui_utils import UIColors 

class RulesTab:
    TAG_TAB = "rules_tab"
    TAG_COMBO_A = "rules_combo_a"
    TAG_COMBO_B = "rules_combo_b"
    TAG_RULES_TABLE = "rules_table"
    TAG_STATUS = "rules_status"

    _mod_list_cache: List[str] = []
    _mod_id_name_map = {}

    @staticmethod
    def create():
        with dpg.tab(label=loc.get_string("tab-user-rules"), parent="main_tab_bar", tag=RulesTab.TAG_TAB):
            
            # --- Add Rule Section ---
            with dpg.group(horizontal=False):
                dpg.add_text(loc.get_string("header-add-rule"), color=UIColors.HEADER)
                
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text(loc.get_string("label-mod-subject"))
                        dpg.add_combo([], tag=RulesTab.TAG_COMBO_A, width=300)
                    
                    dpg.add_text("-->", color=UIColors.VALUE)
                    
                    with dpg.group():
                        dpg.add_text(loc.get_string("label-mod-target"))
                        dpg.add_combo([], tag=RulesTab.TAG_COMBO_B, width=300)
                    
                    dpg.add_button(label=loc.get_string("btn-add-rule"), callback=RulesTab.add_rule)

                dpg.add_text("", tag=RulesTab.TAG_STATUS, color=UIColors.ERROR)

            dpg.add_separator()
            
            # --- List Rules Section ---
            dpg.add_text(loc.get_string("header-current-rules"), color=UIColors.HEADER)
            with dpg.table(
                header_row=True, 
                tag=RulesTab.TAG_RULES_TABLE, 
                borders_innerH=True, 
                borders_outerH=True, 
                borders_innerV=True,
                policy=dpg.mvTable_SizingStretchSame
            ):
                dpg.add_table_column(label=loc.get_string("column-rule"))
                dpg.add_table_column(label=loc.get_string("column-actions"), width_fixed=True, init_width_or_weight=100)

            # Initial Refresh
            RulesTab.refresh_data()

    @staticmethod
    def refresh_data():
        # Update Mod List for Combos
        # We want all mods, active or inactive.
        all_mods = ModManager.active_mods + ModManager.inactive_mods
        # Sort by name
        all_mods.sort(key=lambda x: x.name.lower())
        
        RulesTab._mod_list_cache = [f"{m.name} ({m.id})" for m in all_mods]
        RulesTab._mod_id_name_map = {m.id: m.name for m in all_mods}
        
        dpg.configure_item(RulesTab.TAG_COMBO_A, items=RulesTab._mod_list_cache)
        dpg.configure_item(RulesTab.TAG_COMBO_B, items=RulesTab._mod_list_cache)

        RulesTab.refresh_table()

    @staticmethod
    def refresh_table():
        # Clear table
        if dpg.does_item_exist(RulesTab.TAG_RULES_TABLE):
            children = dpg.get_item_children(RulesTab.TAG_RULES_TABLE, slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)
        
        rules = UserRulesManager.get_rules()
        for idx, rule in enumerate(rules):
            subject_id = rule["subject"]
            target_id = rule["target"]
            
            subject_name = RulesTab._mod_id_name_map.get(subject_id, subject_id)
            target_name = RulesTab._mod_id_name_map.get(target_id, target_id)
            
            with dpg.table_row(parent=RulesTab.TAG_RULES_TABLE):
                dpg.add_text(f"{subject_name}  -->  {target_name}")
                dpg.add_button(
                    label=loc.get_string("btn-remove-rule"), 
                    user_data=idx, 
                    callback=lambda s, a, u: RulesTab.remove_rule(u)
                )

    @staticmethod
    def add_rule():
        # Get selected strings
        val_a = dpg.get_value(RulesTab.TAG_COMBO_A)
        val_b = dpg.get_value(RulesTab.TAG_COMBO_B)
        
        if not val_a or not val_b:
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("error-adding-rule", error="Select both mods"))
            return

        # Extract IDs (Assuming format "Name (ID)")
        # Robust extraction: find last '('
        def extract_id(val):
            if "(" in val and val.endswith(")"):
                return val.rsplit("(", 1)[1][:-1]
            return val

        id_a = extract_id(val_a)
        id_b = extract_id(val_b)
        
        success, msg = UserRulesManager.add_rule(id_a, id_b)
        
        if success:
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("msg-rule-added", subject=id_a, target=id_b))
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.SUCCESS)
            RulesTab.refresh_table()
        else:
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("error-adding-rule", error=msg))
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.ERROR)

    @staticmethod
    def remove_rule(index):
        if UserRulesManager.remove_rule(index):
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("confirm-delete-rule"))
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.DEFAULT)
            RulesTab.refresh_table()
