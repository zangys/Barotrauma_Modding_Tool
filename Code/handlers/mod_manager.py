import atexit
import logging
import platform
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Code.app_vars import AppConfig
from Code.loc import Localization as loc
from Code.package.dataclasses import ModUnit
from Code.xml_object import XMLBuilder, XMLComment, XMLElement
from Code.handlers.cache_manager import CacheManager
from Code.handlers.user_rules import UserRulesManager
from .condition_manager import process_condition
from .parts_manager import PartsManager

logger = logging.getLogger(__name__)


class DependencyPriority:
    USER_RULE = 1000
    REQUIREMENT = 500
    PATCH = 400
    OVERRIDE = 300
    IMPLICIT_PATCH = 200
    NAME_MATCH = 100


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
    def get_player_config_path() -> Optional[Path]:
        game_path = ModManager.get_game_path()
        system = platform.system()
        if system == "Windows":
            return game_path / "config_player.xml" if game_path else None
        elif system == "Linux" or system == "Darwin":
            if system == "Linux":
                base = Path.home() / ".local" / "share"
            else:
                base = Path.home() / "Library" / "Application Support"
            config_path = (
                base / "Daedalic Entertainment GmbH" / "Barotrauma"
                / "config_player.xml"
            )
            return config_path
        return game_path / "config_player.xml" if game_path else None

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
        presets_path.mkdir(parents=True, exist_ok=True)
        return presets_path

    @staticmethod
    def get_available_presets() -> List[str]:
        p_dir = ModManager.get_presets_dir()
        if not p_dir:
            return []
        return sorted([f.stem for f in p_dir.glob("*.xml") if f.is_file()])


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

        new_active = []
        missing = []
        all_mods = ModManager._mod_map.values()
        local_mods = {m.name: m for m in all_mods if m.local}

        for node in xml_obj.iter_non_comment_childrens():
            tag = node.tag.lower()
            mod = None
            if tag == "workshop":
                w_id = node.attributes.get("id")
                mod = ModManager.get_mod_by_id(w_id)
                if not mod:
                    missing.append(node.attributes.get("name", f"ID: {w_id}"))
            elif tag == "local":
                l_name = node.attributes.get("name")
                mod = local_mods.get(l_name)
                if not mod:
                    missing.append(l_name)
            if mod and mod not in new_active:
                new_active.append(mod)

        ModManager.active_mods = new_active
        active_ids = {m.id for m in new_active}
        ModManager.inactive_mods = [
            m for m in ModManager._mod_map.values() if m.id not in active_ids
        ]
        for i, mod in enumerate(ModManager.active_mods, 1):
            mod.load_order = i
        return True, missing

    @staticmethod
    def save_preset(preset_name: str) -> bool:
        p_dir = ModManager.get_presets_dir()
        if not p_dir:
            return False
        root = XMLElement("mods", {"name": preset_name})
        root.add_child(XMLElement("Vanilla"))
        for mod in ModManager.active_mods:
            if mod.local:
                root.add_child(XMLElement("Local", {"name": mod.name}))
            else:
                w_id = mod.steam_id or mod.id
                root.add_child(
                    XMLElement("Workshop", {"name": mod.name, "id": w_id})
                )
        try:
            XMLBuilder.save(root, p_dir / f"{preset_name}.xml")
            return True
        except Exception:
            return False

    @staticmethod
    def load_mods():
        ModManager._game_path_cache = None
        game_path = ModManager.get_game_path()
        if not game_path:
            return

        ModManager.active_mods.clear()
        ModManager.inactive_mods.clear()
        ModManager._mod_map.clear()

        config_path = ModManager.get_player_config_path()
        active_configs = {}
        if config_path:
            active_configs = ModManager._get_active_mod_configs(config_path)

        # Build search list
        paths = [game_path / "LocalMods"]
        ws_sync = AppConfig.get("workshop_sync_path")
        if ws_sync:
            paths.append(Path(ws_sync))
        st_mod = AppConfig.get("steam_mod_dir")
        if st_mod:
            paths.append(Path(st_mod))

        mod_folders = []
        seen = set()
        for p in paths:
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir() and item not in seen:
                        mod_folders.append(item)
                        seen.add(item)

        with ThreadPoolExecutor() as executor:
            loaded = list(executor.map(
                ModManager._parse_mod_safe, mod_folders
            ))

        CacheManager.save()

        # Deduplicate
        grouped = defaultdict(list)
        for m in loaded:
            if m:
                grouped[m.name].append(m)

        unique = []
        for group in grouped.values():
            if len(group) == 1:
                unique.append(group[0])
            else:
                # Priority: Workshop with steam_id > Local
                group.sort(
                    key=lambda x: (not x.local, x.steam_id is not None),
                    reverse=True
                )
                unique.append(group[0])

        for mod in unique:
            ModManager._mod_map[mod.id] = mod
            mod_key = str(mod.str_path).replace("\\", "/").lower()
            if mod_key in active_configs:
                mod.load_order = active_configs[mod_key]
                ModManager.active_mods.append(mod)
            else:
                ModManager.inactive_mods.append(mod)

        # Normal order: Smallest load_order at Top
        ModManager.active_mods.sort(key=lambda x: x.load_order or 9999)

    @staticmethod
    def _get_active_mod_configs(path: Path) -> Dict[str, int]:
        xml = XMLBuilder.load(path)
        if not xml:
            return {}
        configs = {}
        pkgs = list(xml.find_only_elements("package"))
        for i, pkg in enumerate(pkgs, 1):
            p_attr = pkg.attributes.get("path")
            if p_attr:
                # Store normalized path (minus /filelist.xml) as key
                norm = p_attr.replace("\\", "/").lower()
                if norm.endswith("/filelist.xml"):
                    norm = norm[:-13]
                configs[norm] = i
        return configs

    @staticmethod
    def load_cslua_config():
        game_path = ModManager.get_game_path()
        if not game_path:
            return
        # Lua detection
        deps_path = game_path / "Barotrauma.deps.json"
        has_lua = False
        if deps_path.exists():
            content = deps_path.read_text(errors="ignore")
            has_lua = "Luatrauma" in content
        AppConfig.set("has_lua", has_lua)
        # CS detection
        cs_xml = game_path / "LuaCsSetupConfig.xml"
        if cs_xml.exists():
            obj = XMLBuilder.load(cs_xml)
            if obj:
                val = obj.attributes.get("EnableCsScripting", "false")
                AppConfig.set("has_cs", val.lower() == "true")

    @staticmethod
    def get_mod_by_id(mod_id: str):
        return ModManager._mod_map.get(mod_id)

    @staticmethod
    def activate_mod(mod_id: str) -> bool:
        mod = ModManager.get_mod_by_id(mod_id)
        if mod and mod in ModManager.inactive_mods:
            ModManager.inactive_mods.remove(mod)
            ModManager.active_mods.append(mod)
            return True
        return False

    @staticmethod
    def deactivate_mod(mod_id: str) -> bool:
        mod = ModManager.get_mod_by_id(mod_id)
        if mod and mod in ModManager.active_mods:
            ModManager.active_mods.remove(mod)
            ModManager.inactive_mods.append(mod)
            return True
        return False

    @staticmethod
    def activate_all_mods():
        ModManager.active_mods.extend(ModManager.inactive_mods)
        ModManager.inactive_mods.clear()

    @staticmethod
    def swap_active_mods(id1, id2):
        mods = ModManager.active_mods
        try:
            i1 = next(i for i, m in enumerate(mods) if m.id == id1)
            i2 = next(i for i, m in enumerate(mods) if m.id == id2)
            mods[i1], mods[i2] = mods[i2], mods[i1]
        except (StopIteration, ValueError):
            pass

    @staticmethod
    def swap_inactive_mods(id1, id2):
        mods = ModManager.inactive_mods
        try:
            i1 = next(i for i, m in enumerate(mods) if m.id == id1)
            i2 = next(i for i, m in enumerate(mods) if m.id == id2)
            mods[i1], mods[i2] = mods[i2], mods[i1]
        except (StopIteration, ValueError):
            pass

    @staticmethod
    def insert_mod_in_list(target_list, mod_id, target_mod_id):
        try:
            mod = next(m for m in target_list if m.id == mod_id)
            target = next(m for m in target_list if m.id == target_mod_id)
            target_list.remove(mod)
            idx = target_list.index(target)
            target_list.insert(idx, mod)
        except (StopIteration, ValueError):
            pass

    @staticmethod
    def insert_active_mod(m1, m2):
        ModManager.insert_mod_in_list(ModManager.active_mods, m1, m2)

    @staticmethod
    def insert_inactive_mod(m1, m2):
        ModManager.insert_mod_in_list(ModManager.inactive_mods, m1, m2)

    @staticmethod
    def move_mod_to_end(target_list, mod_id):
        try:
            mod = next(m for m in target_list if m.id == mod_id)
            target_list.remove(mod)
            target_list.append(mod)
        except (StopIteration, ValueError):
            pass

    @staticmethod
    def move_active_mod_to_end(ident):
        ModManager.move_mod_to_end(ModManager.active_mods, ident)

    @staticmethod
    def move_inactive_mod_to_end(ident):
        ModManager.move_mod_to_end(ModManager.inactive_mods, ident)

    @staticmethod
    def save_mods():
        config_path = ModManager.get_player_config_path()
        if not config_path:
            return
        xml = XMLBuilder.load(config_path) or XMLElement("config")
        pkgs_node = list(xml.find_only_elements("regularpackages"))
        if not pkgs_node:
            pkgs_node = XMLElement("regularpackages")
            xml.add_child(pkgs_node)
        else:
            pkgs_node = pkgs_node[0]
        pkgs_node.childrens.clear()

        active_ids = {m.id for m in ModManager.active_mods}

        # Saving in UI order: Top mod is FIRST in XML
        for mod in ModManager.active_mods:
            if mod.has_toggle_content:
                PartsManager.do_changes(mod, active_ids)

            p = str(mod.str_path).replace("\\", "/")
            if not p.endswith("/"):
                p += "/"
            full_p = p + "filelist.xml"
            pkgs_node.add_child(XMLComment(mod.name))
            pkgs_node.add_child(XMLElement("package", {"path": full_p}))

        config_path.parent.mkdir(parents=True, exist_ok=True)
        XMLBuilder.save(xml, config_path)
        logger.info(
            f"Saved {len(ModManager.active_mods)} mods to {config_path}"
        )

    @staticmethod
    def _on_exit():
        ModManager.save_mods()

    @staticmethod
    def process_errors():
        active_ids = {m.id for m in ModManager.active_mods}
        bind_id = {}
        for mod in ModManager.active_mods:
            for oid in mod.override_id:
                if oid not in bind_id:
                    bind_id[oid] = (mod.name, mod.id)

        for mod in ModManager.active_mods:
            # Preserve runtime cycle warnings
            runtime = [
                w for w in mod.metadata.warnings
                if w.startswith("Order cycle")
            ]
            mod.update_meta_errors()
            mod.metadata.warnings.extend(runtime)

            for dep in mod.metadata.dependencies:
                if dep.type == "conflict" and dep.id in active_ids:
                    msg = dep.attributes.get("message", "conflict")
                    mod.metadata.errors.append(msg)
                elif dep.type != "requiredAnyOrder" and dep.id not in active_ids:
                    if (not dep.condition or
                            process_condition(dep.condition, active_mod_ids=active_ids)):
                        err = loc.get_string(
                            "mod-unfind-mod",
                            mod_name=dep.name,
                            mod_id=dep.steam_id
                        )
                        mod.metadata.errors.append(err)

            for oid in mod.override_id:
                if oid in bind_id and bind_id[oid][1] != mod.id:
                    warn = loc.get_string(
                        "mod-override-id",
                        mod_name=bind_id[oid][0],
                        mod_id=bind_id[oid][1],
                        key_id=oid
                    )
                    mod.metadata.warnings.append(warn)

    @staticmethod
    def sort():
        mods = ModManager.active_mods
        if not mods:
            return
        logger.info(f"Sorting {len(mods)} mods")
        UserRulesManager.init()
        active_ids = {m.id for m in mods}
        id_to_name = {m.id: m.name for m in mods}

        # Build weighted graph
        adj = defaultdict(dict)
        for mod in mods:
            mid = mod.id
            mname = mod.name.lower()
            for dep in mod.metadata.dependencies:
                if dep.id in active_ids and dep.type != "conflict":
                    if (not dep.condition or
                            process_condition(dep.condition,
                                             active_mod_ids=active_ids)):
                        w = (DependencyPriority.REQUIREMENT
                             if dep.type != "patch" else
                             DependencyPriority.PATCH)
                        if w > adj[mid].get(dep.id, (0, ""))[0]:
                            adj[mid][dep.id] = (w, f"Meta-{dep.type}")

            if any(k in mname for k in ('patch', 'compat')):
                for o in mods:
                    if o.id != mid and o.name.lower() in mname:
                        priority = DependencyPriority.IMPLICIT_PATCH
                        if priority > adj[mid].get(o.id, (0, ""))[0]:
                            adj[mid][o.id] = (priority, "Implicit-Patch")

        for rule in UserRulesManager.get_rules():
            s, t = rule["subject"], rule["target"]
            if s in active_ids and t in active_ids:
                # User says: Subject (s) should be ABOVE Target (t).
                # Above = Earlier in XML. So t depends on s. (s -> t)
                adj[t][s] = (DependencyPriority.USER_RULE, "UserRule")

        # Kahn's with cycle break
        in_degree = {mid: 0 for mid in active_ids}
        graph = defaultdict(list)
        edges = []
        for child, p_dict in adj.items():
            for parent, (w, r) in p_dict.items():
                in_degree[child] += 1
                graph[parent].append(child)
                edges.append({"u": parent, "v": child, "w": w, "r": r})

        orig_order = {m.id: i for i, m in enumerate(mods)}

        def run_kahn(deg, g):
            starts = [m for m in active_ids if deg[m] == 0]
            q = deque(sorted(starts, key=orig_order.get))
            res = []
            while q:
                u = q.popleft()
                res.append(u)
                for v in g[u]:
                    deg[v] -= 1
                    if deg[v] == 0:
                        q.append(v)
            return res

        sorted_ids = run_kahn(in_degree.copy(), graph)
        while len(sorted_ids) != len(mods):
            rem = set(active_ids) - set(sorted_ids)
            cands = [e for e in edges if e["u"] in rem and e["v"] in rem]
            if not cands:
                for mid in rem:
                    in_degree[mid] = 0
            else:
                cands.sort(key=lambda x: x["w"])
                e = cands[0]
                logger.warning(
                    f"Breaking cycle: {e['r']} '{id_to_name[e['u']]}' "
                    f"-> '{id_to_name[e['v']]}'"
                )
                if e['v'] in ModManager._mod_map:
                    ModManager._mod_map[e['v']].metadata.warnings.append(
                        f"Order cycle broken: dependency on "
                        f"'{id_to_name[e['u']]}' ignored."
                    )
                in_degree[e["v"]] -= 1
                graph[e["u"]].remove(e["v"])
                edges.remove(e)
            sorted_ids = run_kahn(in_degree.copy(), graph)

        # Kahn returns [Top ... Bottom].
        ModManager.active_mods = [
            ModManager._mod_map[mid] for mid in sorted_ids
        ]

        # Re-assign load_order: 1 at top, N at bottom
        for i, mod in enumerate(ModManager.active_mods, 1):
            mod.load_order = i

        ModManager.process_errors()
        logger.info("Sort complete")
