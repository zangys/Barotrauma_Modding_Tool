import atexit
import logging
import os
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from Code.app_vars import AppConfig
from Code.loc import Localization as loc
from Code.package.dataclasses import ModUnit
from Code.xml_object import XMLBuilder, XMLComment, XMLElement
from .cache_manager import CacheManager
from .condition_manager import process_condition
from .parts_manager import PartsManager

logger = logging.getLogger(__name__)


class ModManager:
    active_mods: List[ModUnit] = []
    inactive_mods: List[ModUnit] = []
    _mod_map: Dict[str, ModUnit] = {}
    _game_path_cache: Optional[Path] = None

    @staticmethod
    def get_game_path() -> Optional[Path]:
        if ModManager._game_path_cache:
            return ModManager._game_path_cache
        path = AppConfig.get_game_path()
        if path:
            ModManager._game_path_cache = path
        return path

    @staticmethod
    def init():
        CacheManager.init()
        ModManager.load_mods()
        ModManager.load_cslua_config()
        atexit.register(ModManager._on_exit)

    @staticmethod
    def _parse_mod_safe(path: Path) -> Optional[ModUnit]:
        try:
            if not (path / "filelist.xml").exists():
                return None

            cached_mod = CacheManager.get_cached_mod(path)
            if cached_mod:
                return cached_mod

            mod = ModUnit.build(path)
        
            if mod:
                CacheManager.update_cache(mod)
            
            return mod

        except Exception as e:
            logger.error(f"Error parsing mod folder {path.name}: {e}")
            return None

    @staticmethod
    def get_presets_dir() -> Optional[Path]:
        game_path = ModManager.get_game_path()
        if not game_path:
            return None
        
        presets_path = game_path / "ModLists"
        if not presets_path.exists():
            try:
                presets_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                return None
        return presets_path

    @staticmethod
    def get_available_presets() -> List[str]:
        p_dir = ModManager.get_presets_dir()
        if not p_dir:
            return []
        
        return sorted([
            f.stem for f in p_dir.glob("*.xml") 
            if f.is_file()
        ])

    @staticmethod
    def load_preset(preset_name: str) -> Tuple[bool, List[str]]:
        p_dir = ModManager.get_presets_dir()
        if not p_dir:
            return False, []
        
        file_path = p_dir / f"{preset_name}.xml"
        if not file_path.exists():
            return False, []

        xml_obj = XMLBuilder.load(file_path)
        if not xml_obj:
            return False, []

        new_active_mods = []
        missing_mods = []
        
        local_mods_by_name = {
            m.name: m for m in ModManager._mod_map.values() if m.local
        }

        for node in xml_obj.iter_non_comment_childrens():
            tag = node.tag.lower()
            mod_to_add = None
            
            if tag == "vanilla":
                continue
            
            elif tag == "workshop":
                w_id = node.attributes.get("id")
                w_name = node.attributes.get("name", f"ID: {w_id}")
                
                mod_to_add = ModManager.get_mod_by_id(w_id)
                if not mod_to_add:
                    missing_mods.append(w_name)
            
            elif tag == "local":
                l_name = node.attributes.get("name")
                mod_to_add = local_mods_by_name.get(l_name)
                if not mod_to_add:
                    mod_to_add = next((m for m in ModManager._mod_map.values() if m.name == l_name), None)
                
                if not mod_to_add:
                    missing_mods.append(l_name)

            if mod_to_add:
                if mod_to_add not in new_active_mods:
                    new_active_mods.append(mod_to_add)

        ModManager.active_mods = new_active_mods
        
        active_ids = {m.id for m in new_active_mods}
        ModManager.inactive_mods = [
            m for m in ModManager._mod_map.values() 
            if m.id not in active_ids
        ]
        
        for i, mod in enumerate(ModManager.active_mods, 1):
            mod.load_order = i

        logger.info(f"Loaded preset '{preset_name}'. Missing: {len(missing_mods)}")
        return True, missing_mods

    @staticmethod
    def save_preset(preset_name: str) -> bool:
        p_dir = ModManager.get_presets_dir()
        if not p_dir:
            return False

        file_path = p_dir / f"{preset_name}.xml"
        
        root = XMLElement("mods")
        
        root.add_child(XMLElement("Vanilla"))
        
        for mod in ModManager.active_mods:
            if mod.local:
                root.add_child(XMLElement("Local", {"name": mod.name}))
            else:
        
                w_id = mod.steam_id if mod.steam_id else mod.id
                root.add_child(XMLElement("Workshop", {"name": mod.name, "id": w_id}))
        
        try:
            XMLBuilder.save(root, file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save preset {preset_name}: {e}")
            return False

    @staticmethod
    def load_mods():
        game_path = ModManager.get_game_path()
        if not game_path:
            return

        ModManager.active_mods.clear()
        ModManager.inactive_mods.clear()
        ModManager._mod_map.clear()

        config_player = game_path / "config_player.xml"
        active_mod_configs = ModManager._get_active_mod_configs(config_player)

        paths_to_check = [
            game_path / "LocalMods",
            Path(AppConfig.get("workshop_sync_path") or ""),
            Path(AppConfig.get("steam_mod_dir") or "")
        ]

        mod_folders_to_process = []
        seen_paths = set()

        for p in paths_to_check:
            if p and p.name and p.exists():
                try:
                    for item in p.iterdir():
                        if item.is_dir() and not item.name.startswith('.') and item not in seen_paths:
                            mod_folders_to_process.append(item)
                            seen_paths.add(item)
                except OSError:
                    continue

        max_workers = min(32, (os.cpu_count() or 4) * 4)
        loaded_mods_raw = []
        
        if mod_folders_to_process:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(ModManager._parse_mod_safe, mod_folders_to_process))
                for mod in results:
                    if mod:
                        loaded_mods_raw.append(mod)

        CacheManager.save()

        grouped_by_name: Dict[str, List[ModUnit]] = defaultdict(list)
        for mod in loaded_mods_raw:
            grouped_by_name[mod.name].append(mod)

        unique_mods_list = []

        for name, group in grouped_by_name.items():
            if len(group) == 1:
                unique_mods_list.append(group[0])
                continue
            
            
            mods_with_steam = [m for m in group if m.steam_id]
            mods_without_steam = [m for m in group if not m.steam_id]
            
            selected_mod = None

            if mods_with_steam and mods_without_steam:
                selected_mod = mods_with_steam[0]
            
            elif len(mods_with_steam) > 1:
                locals = [m for m in mods_with_steam if m.local]
                if locals:
                    selected_mod = locals[0]
                else:
                    selected_mod = mods_with_steam[0]
            else:

                selected_mod = group[0]

            if selected_mod:
                unique_mods_list.append(selected_mod)

        for mod in unique_mods_list:
            ModManager._mod_map[mod.id] = mod

        for mod in ModManager._mod_map.values():
            if mod.id in active_mod_configs:
                mod.load_order = active_mod_configs[mod.id]
                ModManager.active_mods.append(mod)
            else:
                ModManager.inactive_mods.append(mod)

        ModManager.active_mods.sort(key=lambda m: m.load_order if m.load_order is not None else 9999)

    @staticmethod
    def _get_active_mod_configs(path_to_config: Path) -> Dict[str, int]:
        if not path_to_config.exists():
            return {}

        xml_obj = XMLBuilder.load(path_to_config)
        if not xml_obj:
            return {}

        active_configs = {}
        packages = list(xml_obj.find_only_elements("package"))
        
        for i, pkg in enumerate(packages, start=1):
            path_attr = pkg.attributes.get("path")
            if not path_attr:
                continue
            
            try:
                parts = path_attr.replace('\\', '/').split('/')
                if len(parts) >= 2:
                    mod_id = parts[-2]
                    active_configs[mod_id] = i
            except Exception:
                continue

        return active_configs

    @staticmethod
    def load_cslua_config():
        game_path = ModManager.get_game_path()
        if not game_path:
            return

        lua_path = game_path / "Barotrauma.deps.json"
        has_lua = False
        if lua_path.exists():
            try:
                content = lua_path.read_text(encoding="utf-8")
                has_lua = "Luatrauma" in content
            except Exception:
                pass
        
        AppConfig.set("has_lua", has_lua)
        if has_lua:
            logger.debug(f"Lua support enabled: {has_lua}")

        cs_path = game_path / "LuaCsSetupConfig.xml"
        has_cs = False
        if cs_path.exists():
            try:
                xml_obj = XMLBuilder.load(cs_path)
                has_cs = (
                    xml_obj.attributes.get("EnableCsScripting", "false").lower() == "true"
                    if xml_obj else False
                )
            except Exception:
                pass
        
        AppConfig.set("has_cs", has_cs)
        if has_cs:
            logger.debug(f"CS scripting enabled: {has_cs}")

    @staticmethod
    def get_mod_by_id(mod_id: str) -> Optional[ModUnit]:
        return ModManager._mod_map.get(mod_id)
    
    find_mod_by_id = get_mod_by_id

    @staticmethod
    def activate_mod(mod_id: str) -> bool:
        mod = ModManager._mod_map.get(mod_id)
        if not mod:
            return False
            
        if mod in ModManager.inactive_mods:
            ModManager.inactive_mods.remove(mod)
            ModManager.active_mods.append(mod)
            return True
        return False

    @staticmethod
    def deactivate_mod(mod_id: str) -> bool:
        mod = ModManager._mod_map.get(mod_id)
        if not mod:
            return False

        if mod in ModManager.active_mods:
            ModManager.active_mods.remove(mod)
            ModManager.inactive_mods.append(mod)
            return True
        return False
        
    @staticmethod
    def activate_all_mods():
        if not ModManager.inactive_mods:
            return
        ModManager.active_mods.extend(ModManager.inactive_mods)
        ModManager.inactive_mods.clear()
        logger.info("all mods active")

    @staticmethod
    def swap_active_mods(mod_id1: str, mod_id2: str) -> None:
        if mod_id1 not in ModManager._mod_map or mod_id2 not in ModManager._mod_map:
            return
        
        try:
            idx1 = -1
            idx2 = -1
            for i, m in enumerate(ModManager.active_mods):
                if m.id == mod_id1: idx1 = i
                elif m.id == mod_id2: idx2 = i
                
                if idx1 != -1 and idx2 != -1:
                    break
            
            if idx1 != -1 and idx2 != -1:
                ModManager.active_mods[idx1], ModManager.active_mods[idx2] = (
                    ModManager.active_mods[idx2],
                    ModManager.active_mods[idx1],
                )
        except Exception:
            pass

    @staticmethod
    def swap_inactive_mods(mod_id1: str, mod_id2: str) -> None:
        try:
            m1 = ModManager.get_mod_by_id(mod_id1)
            m2 = ModManager.get_mod_by_id(mod_id2)
            if m1 and m2 and m1 in ModManager.inactive_mods and m2 in ModManager.inactive_mods:
                idx1 = ModManager.inactive_mods.index(m1)
                idx2 = ModManager.inactive_mods.index(m2)
                ModManager.inactive_mods[idx1], ModManager.inactive_mods[idx2] = \
                    ModManager.inactive_mods[idx2], ModManager.inactive_mods[idx1]
        except ValueError:
            pass

    @staticmethod
    def move_active_mod_to_end(mod_id: str) -> None:
        mod = ModManager.get_mod_by_id(mod_id)
        if mod and mod in ModManager.active_mods:
            ModManager.active_mods.remove(mod)
            ModManager.active_mods.append(mod)

    @staticmethod
    def move_inactive_mod_to_end(mod_id: str) -> None:
        mod = ModManager.get_mod_by_id(mod_id)
        if mod and mod in ModManager.inactive_mods:
            ModManager.inactive_mods.remove(mod)
            ModManager.inactive_mods.append(mod)

    @staticmethod
    def save_mods() -> None:
        game_path = ModManager.get_game_path()
        if not game_path or not game_path.exists():
            logger.error(f"Game path does not exist!\n|Path: {game_path}")
            return

        user_config_path = game_path / "config_player.xml"
        if not user_config_path.exists():
            logger.error(f"config_player.xml does not exist!\n|Path: {user_config_path}")
            return

        try:
            xml_obj = XMLBuilder.load(user_config_path)
            if not xml_obj:
                logger.error(f"Invalid config_player.xml\n|Path: {user_config_path}")
                return

            regularpackages_list = list(xml_obj.find_only_elements("regularpackages"))
            
            if not regularpackages_list:
                reg_pkg_node = XMLElement("regularpackages")
                xml_obj.add_child(reg_pkg_node)
            else:
                reg_pkg_node = regularpackages_list[0]
            
            reg_pkg_node.childrens.clear()

            active_ids_set = {mod.id for mod in ModManager.active_mods}

            for mod in ModManager.active_mods:
                if mod.has_toggle_content:
                    try:
                        PartsManager.do_chenges(mod, active_ids_set)
                    except AttributeError:
                        if hasattr(PartsManager, 'do_changes'):
                            PartsManager.do_changes(mod, active_ids_set)

                mod_path = mod.str_path 
                reg_pkg_node.add_child(XMLComment(mod.name))
                reg_pkg_node.add_child(
                    XMLElement("package", {"path": f"{mod_path}/filelist.xml"})
                )

            temp_path = user_config_path.with_suffix('.tmp')
            XMLBuilder.save(xml_obj, temp_path)
            if temp_path.exists():
                temp_path.replace(user_config_path)
            
        except Exception as e:
            logger.error(f"Error saving mods: {e}", exc_info=True)

    @staticmethod
    def _on_exit():
        try:
            if not ModManager.active_mods:
                return

            game_path = ModManager.get_game_path()
            if not game_path:
                return

            user_config_path = game_path / "config_player.xml"
            if not user_config_path.exists():
                return

            xml_obj = XMLBuilder.load(user_config_path)
            if not xml_obj: return

            pkgs = list(xml_obj.find_only_elements("regularpackages"))
            if not pkgs: return
            reg_pkg = pkgs[0]
            
            reg_pkg.childrens.clear()

            for mod in ModManager.active_mods:
                try:
                    mod_path = mod.str_path
                    reg_pkg.add_child(XMLComment(mod.name))
                    reg_pkg.add_child(
                        XMLElement("package", {"path": f"{mod_path}/filelist.xml"})
                    )

                    if mod.has_toggle_content:
                        try:
                            PartsManager.rollback_changes_no_thread(mod)
                        except Exception as e:
                            logger.error(f"Error rolling back changes for mod {mod.name}: {e}")
                except Exception as e:
                    logger.error(f"Error processing mod {mod.name} on exit: {e}")

            tmp = user_config_path.with_suffix('.tmp')
            XMLBuilder.save(xml_obj, tmp)
            if tmp.exists():
                tmp.replace(user_config_path)

        except Exception as e:
            logger.error(f"Error during exit processing: {e}")

    @staticmethod
    def process_errors():
        active_ids = {mod.id for mod in ModManager.active_mods}
        
        bind_id = {}
        for mod in ModManager.active_mods:
            for over_id in mod.override_id:
                if over_id not in bind_id:
                    bind_id[over_id] = (mod.name, mod.id)

        for mod in ModManager.active_mods:
            mod.update_meta_errors()
            
            meta = mod.metadata
            deps = meta.dependencies
            
            for dep in deps:
                if dep.type == "conflict":
                    if dep.id in active_ids:
                        level = dep.attributes.get("level", "error")
                        msg = dep.attributes.get("message", "base-conflict")
                        if level == "warning":
                            meta.warnings.append(msg)
                        else:
                            meta.errors.append(msg)

                elif dep.type == "requiredAnyOrder":
                     pass
                
                else:
                    is_missing = dep.id not in active_ids
                    
                    if dep.condition:
                        if process_condition(dep.condition, active_mods_ids=active_ids):
                            if is_missing:
                                meta.errors.append(loc.get_string("mod-unfind-mod", mod_name=dep.name, mod_id=dep.steam_id))
                    elif is_missing:
                         meta.errors.append(loc.get_string("mod-unfind-mod", mod_name=dep.name, mod_id=dep.steam_id))

            if mod.override_id:
                for over_id in mod.override_id:
                    if over_id in bind_id and bind_id[over_id][1] != mod.id:
                        meta.warnings.append(
                            loc.get_string(
                                "mod-override-id",
                                mod_name=bind_id[over_id][0],
                                mod_id=bind_id[over_id][1],
                                key_id=over_id,
                            )
                        )

    @staticmethod
    def sort():
        mods = ModManager.active_mods
        if not mods:
            return

        logger.info(f"Starting sort for {len(mods)} active mods")

        id_to_mod = ModManager._mod_map 
        id_to_name = {m.id: m.name for m in mods}
        active_mod_map = {m.id: m for m in mods}
        active_mod_ids = set(active_mod_map.keys())
        
        ban_ids = set()
        dependencies = defaultdict(set)
        hard_edges = set()
        
        missing_dependencies = []

        for mod in mods:
            mod_deps = mod.metadata.dependencies
            for dep in mod_deps:
                if dep.type == "conflict":
                    if dep.id in active_mod_ids:
                        ban_ids.add(dep.id)
                        logger.error(f"Conflict: '{mod.name}' <-> '{id_to_name.get(dep.id, dep.id)}'.")
                
                elif dep.type in ("requirement", "patch"):

                    if dep.condition and not process_condition(dep.condition, active_mod_ids=active_mod_ids):
                        continue
                    
                    if dep.id not in active_mod_ids and dep.id not in ban_ids:
                        candidate = ModManager.get_mod_by_id(dep.id)
                        if candidate:
                             missing_dependencies.append(candidate)
                        else:

                            pass

        if missing_dependencies:
            for new_mod in missing_dependencies:
                if new_mod.id not in active_mod_ids and new_mod.id not in ban_ids:
                    if ModManager.activate_mod(new_mod.id):
                        active_mod_map[new_mod.id] = new_mod
                        active_mod_ids.add(new_mod.id)
                        id_to_name[new_mod.id] = new_mod.name
                        logger.info(f"Auto-activated: '{new_mod.name}'")
  
            mods = ModManager.active_mods

        added_ids = {}
        for mod in mods:
            for aid in mod.add_id:
                if aid not in added_ids:
                    added_ids[aid] = mod.id

        for mod in mods:
            mod_id = mod.id
            mod_name_lower = mod.name.lower()
            
            for dep in mod.metadata.dependencies:
                if dep.id not in active_mod_ids: continue
                if dep.type == "conflict": continue
                if dep.condition and not process_condition(dep.condition, active_mod_ids=active_mod_ids): continue

                target_id = dep.id
                if dep.type == "patch" or dep.type == "requirement":
                    dependencies[mod_id].add(target_id)
                    hard_edges.add((mod_id, target_id))

            is_potential_patch = any(k in mod_name_lower for k in ('patch', 'compatibility', 'compat'))
            if is_potential_patch:
                for other_mod in mods:
                    if other_mod.id == mod_id: continue
                    other_name = other_mod.name.lower()
                    if len(other_name) > 3 and other_name in mod_name_lower:
                        dependencies[mod_id].add(other_mod.id)

            if not mod.get_bool_setting("IgnoreOverrideCheck"):
                for oid in mod.override_id:
                    if oid in added_ids:
                        adder_id = added_ids[oid]
                        if adder_id != mod_id:
                            dependencies[mod_id].add(adder_id)

        
        in_degree = defaultdict(int)
        for u, parents in dependencies.items():
            in_degree[u] = len(parents)

        children_graph = defaultdict(list)
        for child, parents in dependencies.items():
            for parent in parents:
                children_graph[parent].append(child)

        current_order = {m.id: i for i, m in enumerate(mods)}
        queue = []
        for mod in mods:
            if in_degree[mod.id] == 0:
                queue.append(mod.id)
        queue.sort(key=lambda x: current_order.get(x, 0))
        queue = deque(queue)

        sorted_mods = []
        processed_ids = set()

        def process_queue():
            while queue:
                u = queue.popleft()
                if u in processed_ids or u not in active_mod_map:
                    continue
                
                sorted_mods.append(active_mod_map[u])
                processed_ids.add(u)
                
                if u in children_graph:
                    for v in children_graph[u]:
                        in_degree[v] -= 1
                        if in_degree[v] == 0:
                            queue.append(v)

        process_queue()
        
        if len(sorted_mods) != len(mods):
            unresolved = set(active_mod_ids) - processed_ids
            logger.warning(f"Cycle detected! Unresolved mods: {len(unresolved)}")

            has_soft_resolves = True
            while has_soft_resolves and len(sorted_mods) != len(mods):
                has_soft_resolves = False
                unresolved = set(active_mod_ids) - processed_ids
                
                for u in list(unresolved):
                    holders = [p for p in dependencies[u] if p in unresolved]
                    for p in holders:
                        if (u, p) not in hard_edges:
                            in_degree[u] -= 1
                            dependencies[u].remove(p)
                            logger.info(f"Resolving cycle (soft): '{id_to_name[u]}' -> '{id_to_name[p]}'")
                            
                            if in_degree[u] == 0:
                                queue.append(u)
                                has_soft_resolves = True
                
                if has_soft_resolves:
                    process_queue()

            while len(sorted_mods) != len(mods):
                unresolved = set(active_mod_ids) - processed_ids
                if not unresolved: break

                best_mod_id = min(
                    unresolved,
                    key=lambda mid: len([p for p in dependencies[mid] if p in unresolved])
                )
                
                queue.append(best_mod_id)
                in_degree[best_mod_id] = 0 
                process_queue()

        for i, mod in enumerate(sorted_mods, 1):
            mod.load_order = i
        
        ModManager.active_mods = sorted_mods
        logger.info(f"Sorted {len(sorted_mods)} mods")
        
        ModManager.process_errors()