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
    TAG_RULES_COUNT = "rules_count_text"

    _full_mod_list: List[str] = []
    _mod_id_name_map = {}
    _all_mod_ids = set()
    _current_rules_filter: str = ""

    @staticmethod
    def create():
        with dpg.tab(
            label=loc.get_string("tab-user-rules"),
            parent="main_tab_bar",
            tag=RulesTab.TAG_TAB
        ):
            dpg.add_text(
                loc.get_string("header-add-rule"),
                color=UIColors.HEADER
            )

            with dpg.group(horizontal=True):
                with dpg.group():
                    dpg.add_text(loc.get_string("label-mod-subject"), color=UIColors.SUCCESS)
                    dpg.add_input_text(
                        hint=loc.get_string("combo-search"),
                        width=300,
                        callback=RulesTab.on_combo_search_changed,
                        user_data=RulesTab.TAG_COMBO_A
                    )
                    dpg.add_combo([], tag=RulesTab.TAG_COMBO_A, width=300)

                with dpg.group():
                    dpg.add_spacer(height=18)
                    arrow_text = dpg.add_text("  ▲\n  |\n  ▼", color=UIColors.VALUE)
                    with dpg.tooltip(arrow_text):
                        dpg.add_text(loc.get_string("tooltip-rule-direction"), wrap=300)

                with dpg.group():
                    dpg.add_text(loc.get_string("label-mod-target"), color=UIColors.ERROR)
                    dpg.add_input_text(
                        hint=loc.get_string("combo-search"),
                        width=300,
                        callback=RulesTab.on_combo_search_changed,
                        user_data=RulesTab.TAG_COMBO_B
                    )
                    dpg.add_combo([], tag=RulesTab.TAG_COMBO_B, width=300)

                with dpg.group():
                    dpg.add_spacer(height=18)
                    dpg.add_button(
                        label=loc.get_string("btn-add-rule"),
                        callback=RulesTab.add_rule
                    )
                    dpg.add_button(
                        label=loc.get_string("btn-generate-rules"),
                        callback=RulesTab.generate_rules
                    )
                    dpg.add_button(
                        label=loc.get_string("btn-clear-rules"),
                        callback=RulesTab.clear_all_rules
                    )

            dpg.add_text("", tag=RulesTab.TAG_STATUS, color=UIColors.ERROR)
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_text(
                    loc.get_string("header-current-rules"),
                    color=UIColors.HEADER
                )
                dpg.add_spacer(width=10)
                dpg.add_text("", tag=RulesTab.TAG_RULES_COUNT, color=UIColors.LABEL)
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
                    init_width_or_weight=120
                )

            RulesTab.refresh_data()

    @staticmethod
    def refresh_data():
        all_mods = list(ModManager.active_mods) + list(ModManager.inactive_mods)
        all_mods.sort(key=lambda x: x.name.lower())

        RulesTab._full_mod_list = [f"{m.name} ({m.id})" for m in all_mods]
        RulesTab._mod_id_name_map = {m.id: m.name for m in all_mods}
        RulesTab._all_mod_ids = {m.id for m in all_mods}

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
        displayed = 0

        for idx, rule in enumerate(rules):
            subject_id = rule["subject"]
            target_id = rule["target"]

            s_name = RulesTab._mod_id_name_map.get(subject_id, subject_id)
            t_name = RulesTab._mod_id_name_map.get(target_id, target_id)

            s_missing = subject_id not in RulesTab._all_mod_ids
            t_missing = target_id not in RulesTab._all_mod_ids

            rule_text = f"{s_name}  ▲  {t_name}"
            if search_term and search_term not in rule_text.lower():
                continue

            displayed += 1
            with dpg.table_row(parent=RulesTab.TAG_RULES_TABLE):
                with dpg.group(horizontal=True):
                    dpg.add_text(
                        s_name,
                        color=UIColors.WARNING if s_missing else UIColors.SUCCESS
                    )
                    if s_missing:
                        dpg.add_text(loc.get_string("label-rule-missing"), color=UIColors.ERROR)
                    dpg.add_text("  ▲  ", color=UIColors.VALUE)
                    dpg.add_text(
                        t_name,
                        color=UIColors.WARNING if t_missing else UIColors.DEFAULT
                    )
                    if t_missing:
                        dpg.add_text(loc.get_string("label-rule-missing"), color=UIColors.ERROR)

                dpg.add_button(
                    label=loc.get_string("btn-remove-rule"),
                    user_data=idx,
                    callback=lambda s, a, u: RulesTab.remove_rule(u)
                )

        total = len(rules)
        if dpg.does_item_exist(RulesTab.TAG_RULES_COUNT):
            dpg.set_value(
                RulesTab.TAG_RULES_COUNT,
                loc.get_string("label-rules-count", count=total)
            )

    @staticmethod
    def add_rule():
        val_a = dpg.get_value(RulesTab.TAG_COMBO_A)
        val_b = dpg.get_value(RulesTab.TAG_COMBO_B)

        if not val_a or not val_b:
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("error-adding-rule", error="Select both mods"))
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.ERROR)
            return

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
    def generate_rules():
        active_mods = ModManager.active_mods
        mod_id_map = {m.id: m for m in active_mods}
        added = 0
        skipped = 0

        patch_keywords = ('patch', 'compat', 'compatibility', 'патч', 'совместимость')

        for mod in active_mods:
            mname_lower = mod.name.lower()

            # Name-based: patch/compat mod → find targets by name similarity
            if any(k in mname_lower for k in patch_keywords):
                for other in active_mods:
                    if other.id == mod.id:
                        continue
                    if ModManager._patch_matches_target(mname_lower, other.name.lower()):
                        ok, _ = UserRulesManager.add_rule(mod.id, other.id)
                        if ok:
                            added += 1
                        else:
                            skipped += 1

            # Metadata-based: declared patch dependencies
            for dep in mod.metadata.dependencies:
                if dep.type == "patch" and dep.id in mod_id_map:
                    ok, _ = UserRulesManager.add_rule(mod.id, dep.id)
                    if ok:
                        added += 1
                    else:
                        skipped += 1

        RulesTab.refresh_data()
        dpg.set_value(
            RulesTab.TAG_STATUS,
            loc.get_string("msg-rules-generated", added=added, skipped=skipped)
        )
        dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.SUCCESS)

    @staticmethod
    def clear_all_rules():
        UserRulesManager.clear_all()
        RulesTab.refresh_table()
        dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("msg-rules-cleared"))
        dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.DEFAULT)

    @staticmethod
    def remove_rule(index):
        if UserRulesManager.remove_rule(index):
            dpg.set_value(RulesTab.TAG_STATUS, loc.get_string("confirm-delete-rule"))
            dpg.configure_item(RulesTab.TAG_STATUS, color=UIColors.DEFAULT)
            RulesTab.refresh_table()
