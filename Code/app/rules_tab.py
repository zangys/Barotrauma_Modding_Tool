import dearpygui.dearpygui as dpg
from typing import List
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
    TAG_SEARCH_RULES = "rules_table_search"

    _full_mod_list: List[str] = []
    _mod_id_name_map = {}
    _current_rules_filter: str = ""

    @staticmethod
    def create():
        with dpg.tab(
            label=loc.get_string("tab-user-rules"),
            parent="main_tab_bar",
            tag=RulesTab.TAG_TAB
        ):
            # --- Add Rule Section ---
            with dpg.group(horizontal=False):
                dpg.add_text(
                    loc.get_string("header-add-rule"),
                    color=UIColors.HEADER
                )

                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text(loc.get_string("label-mod-subject"))
                        dpg.add_input_text(
                            hint=loc.get_string("combo-search"),
                            width=300,
                            callback=RulesTab.on_combo_search_changed,
                            user_data=RulesTab.TAG_COMBO_A
                        )
                        dpg.add_combo([], tag=RulesTab.TAG_COMBO_A, width=300)

                    dpg.add_text("-->", color=UIColors.VALUE)

                    with dpg.group():
                        dpg.add_text(loc.get_string("label-mod-target"))
                        dpg.add_input_text(
                            hint=loc.get_string("combo-search"),
                            width=300,
                            callback=RulesTab.on_combo_search_changed,
                            user_data=RulesTab.TAG_COMBO_B
                        )
                        dpg.add_combo([], tag=RulesTab.TAG_COMBO_B, width=300)

                    with dpg.group():
                        dpg.add_spacer(height=18)
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label=loc.get_string("btn-add-rule"),
                                callback=RulesTab.add_rule
                            )
                            dpg.add_button(
                                label=loc.get_string("btn-generate-rules"),
                                callback=RulesTab.generate_rules
                            )

                dpg.add_text("", tag=RulesTab.TAG_STATUS, color=UIColors.ERROR)

            dpg.add_separator()

            # --- List Rules Section ---
            with dpg.group(horizontal=True):
                dpg.add_text(
                    loc.get_string("header-current-rules"),
                    color=UIColors.HEADER
                )
                dpg.add_spacer(width=20)
                dpg.add_input_text(
                    hint=loc.get_string("rule-search"),
                    width=250,
                    tag=RulesTab.TAG_SEARCH_RULES,
                    callback=RulesTab.on_rules_filter_changed
                )

            with dpg.table(
                header_row=True,
                tag=RulesTab.TAG_RULES_TABLE,
                borders_innerH=True,
                borders_outerH=True,
                borders_innerV=True,
                policy=dpg.mvTable_SizingStretchSame
            ):
                dpg.add_table_column(label=loc.get_string("column-rule"))
                dpg.add_table_column(
                    label=loc.get_string("column-actions"),
                    width_fixed=True,
                    init_width_or_weight=100
                )

            # Initial Refresh
            RulesTab.refresh_data()

    @staticmethod
    def refresh_data():
        all_mods = list(ModManager.active_mods) + list(ModManager.inactive_mods)
        all_mods.sort(key=lambda x: x.name.lower())

        RulesTab._full_mod_list = [f"{m.name} ({m.id})" for m in all_mods]
        RulesTab._mod_id_name_map = {m.id: m.name for m in all_mods}

        dpg.configure_item(RulesTab.TAG_COMBO_A, items=RulesTab._full_mod_list)
        dpg.configure_item(RulesTab.TAG_COMBO_B, items=RulesTab._full_mod_list)

        RulesTab.refresh_table()

    @staticmethod
    def on_combo_search_changed(sender, app_data, user_data):
        search_text = app_data.lower()
        filtered = [
            m for m in RulesTab._full_mod_list
            if search_text in m.lower()
        ]
        dpg.configure_item(user_data, items=filtered)

    @staticmethod
    def on_rules_filter_changed(sender, app_data):
        RulesTab._current_rules_filter = app_data.lower()
        RulesTab.refresh_table()

    @staticmethod
    def refresh_table():
        if dpg.does_item_exist(RulesTab.TAG_RULES_TABLE):
            children = dpg.get_item_children(RulesTab.TAG_RULES_TABLE, slot=1)
            if children:
                for child in children:
                    dpg.delete_item(child)

        rules = UserRulesManager.get_rules()
        search_term = RulesTab._current_rules_filter

        for idx, rule in enumerate(rules):
            subject_id = rule["subject"]
            target_id = rule["target"]

            s_name = RulesTab._mod_id_name_map.get(subject_id, subject_id)
            t_name = RulesTab._mod_id_name_map.get(target_id, target_id)
            rule_text = f"{s_name}  -->  {t_name}"

            if search_term and search_term not in rule_text.lower():
                continue

            with dpg.table_row(parent=RulesTab.TAG_RULES_TABLE):
                dpg.add_text(rule_text)
                dpg.add_button(
                    label=loc.get_string("btn-remove-rule"),
                    user_data=idx,
                    callback=lambda s, a, u: RulesTab.remove_rule(u)
                )

    @staticmethod
    def add_rule():
        val_a = dpg.get_value(RulesTab.TAG_COMBO_A)
        val_b = dpg.get_value(RulesTab.TAG_COMBO_B)

        if not val_a or not val_b:
            err_msg = loc.get_string(
                "error-adding-rule", error="Select both mods"
            )
            dpg.set_value(RulesTab.TAG_STATUS, err_msg)
            return

        def extract_id(val):
            if "(" in val and val.endswith(")"):
                return val.rsplit("(", 1)[1][:-1]
            return val

        id_a = extract_id(val_a)
        id_b = extract_id(val_b)

        success, msg = UserRulesManager.add_rule(id_a, id_b)

        if success:
            dpg.set_value(
                RulesTab.TAG_STATUS,
                loc.get_string("msg-rule-added", subject=id_a, target=id_b)
            )
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.SUCCESS)
            RulesTab.refresh_table()
        else:
            dpg.set_value(
                RulesTab.TAG_STATUS,
                loc.get_string("error-adding-rule", error=msg)
            )
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.ERROR)

    @staticmethod
    def generate_rules():
        import re
        active_mods = ModManager.active_mods
        active_names_map = {m.name.lower(): m for m in active_mods}
        count = 0

        keywords = [
            'patch', 'compatibility', 'compat', 'патч', 'совместимость'
        ]
        separators = r'[&+\-/|,]'

        for mod in active_mods:
            mname_lower = mod.name.lower()
            if any(k in mname_lower for k in keywords):
                parts = re.split(separators, mname_lower)
                for p in parts:
                    p_clean = p.strip()
                    for k in keywords:
                        p_clean = p_clean.replace(k, "").strip()

                    if len(p_clean) < 3:
                        continue

                    target_mod = active_names_map.get(p_clean)
                    if not target_mod:
                        for name, amod in active_names_map.items():
                            if (name == p_clean or
                                    (len(name) > 5 and name in p_clean) or
                                    (len(p_clean) > 5 and p_clean in name)):
                                if amod.id != mod.id:
                                    target_mod = amod
                                    break

                    if target_mod and target_mod.id != mod.id:
                        # Subject = Patch (mod), Target = Main mod (target_mod)
                        # This ensures Patch is HIGHER than Main mod.
                        success, _ = UserRulesManager.add_rule(
                            mod.id, target_mod.id
                        )
                        if success:
                            count += 1

        RulesTab.refresh_data()
        dpg.set_value(
            RulesTab.TAG_STATUS,
            loc.get_string("msg-rules-generated", count=count)
        )
        dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.SUCCESS)

    @staticmethod
    def remove_rule(index):
        if UserRulesManager.remove_rule(index):
            dpg.set_value(
                RulesTab.TAG_STATUS,
                loc.get_string("confirm-delete-rule")
            )
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.DEFAULT)
            RulesTab.refresh_table()
