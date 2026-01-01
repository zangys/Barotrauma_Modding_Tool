import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Set, Pattern

from Code.app_vars import AppConfig
from Code.package import ModUnit
from Code.xml_object import XMLBuilder, XMLComment, XMLElement
from .condition_manager import process_condition

logger = logging.getLogger(__name__)


class PartsManager:
    _RE_BTM_START = "BTM:.*start"
    _RE_BTM_END = "BTM:.*end"
    _RE_COND: Pattern = re.compile(r'conditions="(.*?)"')
    _RE_STATE: Pattern = re.compile(r'setState="(.*?)"')

    @classmethod
    def do_changes(cls, mod: ModUnit, active_mod_ids: Set[str]) -> None:
        cls._process_config(mod.path, active_mod_ids, is_rollback=False)
        cls._process_files_concurrently(mod.path, active_mod_ids, is_rollback=False)

    @classmethod
    def rollback_changes(cls, mod: ModUnit) -> None:
        cls._process_config(mod.path, set(), is_rollback=True)
        cls._process_files_concurrently(mod.path, set(), is_rollback=True)

    @classmethod
    def rollback_changes_no_thread(cls, mod: ModUnit) -> None:
        cls._process_config(mod.path, set(), is_rollback=True)
        
        # Синхронный обход
        files = cls._get_target_files(mod.path)
        for xml_path in files:
            cls._process_single_xml(xml_path, set(), is_rollback=True)

    # --- Internals ---

    @staticmethod
    def _get_target_files(mod_path: Path) -> List[Path]:
        return [
            p for p in mod_path.rglob("*.xml")
            if p.name.lower() not in AppConfig.xml_system_dirs
        ]

    @classmethod
    def _process_files_concurrently(cls, mod_path: Path, active_mod_ids: Set[str], is_rollback: bool):
        files = cls._get_target_files(mod_path)
        if not files:
            return
        max_workers = min(32, (os.cpu_count() or 4) * 4)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(cls._process_single_xml, f, active_mod_ids, is_rollback)
                for f in files
            ]

    @classmethod
    def _process_single_xml(cls, file_path: Path, active_mod_ids: Set[str], is_rollback: bool):
        try:
            xml_obj = XMLBuilder.load(file_path)
            if xml_obj is None:
                return

            modified = False
            iterator = xml_obj.find_between_comments(cls._RE_BTM_START, cls._RE_BTM_END)
            
            for com_start, content_objects, _ in iterator:
                cond_match = cls._RE_COND.search(com_start.content)
                state_match = cls._RE_STATE.search(com_start.content)

                if not state_match:
                    logger.error(f"Missing setState in {file_path}")
                    continue
                state_str = state_match.group(1).lower()
                target_is_active = state_str in ("on", "1", "true")

                should_be_active = False

                if is_rollback:
                    should_be_active = not target_is_active
                else:
                    condition_val = cond_match.group(1) if cond_match else None
                    if condition_val and not process_condition(condition_val, active_mod_ids=active_mod_ids):
                        continue
                    
                    should_be_active = target_is_active

                for obj in content_objects:
                    if obj.index is None: 
                        continue

                    is_currently_element = isinstance(obj, XMLElement)
                    is_currently_comment = isinstance(obj, XMLComment)

                    new_obj = None

                    if should_be_active and is_currently_comment:
                        try:
                            new_obj = obj.to_element()
                        except Exception:
                            continue
                            
                    elif not should_be_active and is_currently_element:
                        new_obj = obj.to_comment()

                    if new_obj:
                        xml_obj.replace(obj.index, new_obj)
                        modified = True

            if modified:
                XMLBuilder.save(xml_obj, file_path)

        except Exception as e:
            logger.error(f"Error processing XML {file_path}: {e}")

    @classmethod
    def _process_config(cls, mod_path: Path, active_mod_ids: Set[str], is_rollback: bool):
        modparts_path = mod_path / "modparts.xml"
        filelist_path = mod_path / "filelist.xml"

        if not modparts_path.exists() or not filelist_path.exists():
            return

        xml_parts = XMLBuilder.load(modparts_path)
        xml_filelist = XMLBuilder.load(filelist_path)

        if not xml_parts or not xml_filelist:
            return

        filelist_modified = False

        for action in xml_parts.iter_non_comment_childrens():
            if not is_rollback:
                cond_attr = action.get_attribute_ignore_case("conditions")
                if cond_attr and not process_condition(cond_attr, active_mod_ids=active_mod_ids):
                    continue

            rel_path_raw = action.get_attribute_ignore_case("file")
            target_tag = action.get_attribute_ignore_case("type")
            set_state_raw = action.get_attribute_ignore_case("setState")

            if not all((rel_path_raw, target_tag, set_state_raw)):
                continue

            target_is_active = set_state_raw.lower() in ("on", "1", "true")
            should_be_active = not target_is_active if is_rollback else target_is_active

            for item in xml_filelist.childrens:
                check_item = item
                is_comment = isinstance(item, XMLComment)
                
                if is_comment:
                    try:
                        check_item = item.to_element()
                    except Exception:
                        continue
                
                item_tag = check_item.tag
                item_file_attr = check_item.get_attribute_ignore_case("file")

                if not item_tag or not item_file_attr:
                    continue

                if (item_tag.lower() == target_tag.lower() and 
                    Path(item_file_attr).as_posix() == Path(rel_path_raw).as_posix()):
                    if should_be_active and is_comment:
                        xml_filelist.replace(item.index, new_node)
                        filelist_modified = True
                        cls._rename_file_on_disk(rel_path_raw, to_active=True)

                    elif not should_be_active and not is_comment:
                        new_node = item.to_comment()
                        xml_filelist.replace(item.index, new_node)
                        filelist_modified = True
                        cls._rename_file_on_disk(rel_path_raw, to_active=False)
                    break 

        if filelist_modified:
            XMLBuilder.save(xml_filelist, filelist_path)

    @staticmethod
    def _rename_file_on_disk(raw_path: str, to_active: bool):
        try:
            resolved_path_str = raw_path.replace("%ModDir%", str(AppConfig.get_steam_mod_path())) \
                                        .replace("LocalMods", str(AppConfig.get_local_mod_path()))
            
            target_path = Path(resolved_path_str)
            
            if to_active:
                if target_path.suffix == ".xml":
                    current_disabled = target_path.with_name(target_path.stem + ".xml_off")
                    if current_disabled.exists():
                        current_disabled.rename(target_path)
            else:
                if target_path.exists() and target_path.suffix == ".xml":
                    new_disabled = target_path.with_name(target_path.stem + ".xml_off")
                    target_path.rename(new_disabled)

        except Exception as e:
            logger.error(f"Failed to rename file {raw_path}: {e}")