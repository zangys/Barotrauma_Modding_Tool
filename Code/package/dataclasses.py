import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Union

from Code.app_vars import AppConfig
from Code.xml_object import XMLBuilder
from .id_parser import extract_ids

logger = logging.getLogger(__name__)


class SkipLoadBuild(Exception):
    pass


@dataclass
class Identifier:
    name: str
    steam_id: Optional[str] = None

    @property
    def id(self) -> str:
        return self.steam_id if self.steam_id else self.name

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Identifier):
            return self.id == value.id
        elif isinstance(value, str):
            return self.id == value
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Identifier(name={self.name}, steam_id={self.steam_id})"


@dataclass
class Dependency(Identifier):
    type: Literal["patch", "requirement", "requiredAnyOrder", "conflict"] = "requirement"
    attributes: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None

    def __str__(self) -> str:
        attrs_str = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return (
            f"Dependency(type={self.type}, id={self.id}, "
            f"condition={self.condition}, attributes={{{attrs_str}}})"
        )

    @staticmethod
    def is_valid_type(value: str) -> bool:
        return value in {"patch", "requirement", "requiredAnyOrder", "conflict"}


@dataclass
class Metadata:
    mod_version: str = "base-not-set"
    game_version: str = "base-not-set"
    author_name: str = "base-unknown"
    license: str = "base-not-specified"
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Metadata(mod={self.mod_version}, game={self.game_version}, "
            f"author={self.author_name}, deps={len(self.dependencies)})"
        )


@dataclass
class ModUnit(Identifier):
    path: Path = field(default_factory=Path)
    local: bool = False
    corepackage: bool = False
    has_toggle_content: bool = False
    load_order: Optional[int] = None

    metadata: Metadata = field(default_factory=Metadata)

    use_lua: bool = False
    use_cs: bool = False

    settings: Dict[str, Any] = field(default_factory=dict)
    add_id: Set[str] = field(default_factory=set)
    override_id: Set[str] = field(default_factory=set)
    
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def str_path(self) -> str:
        if not self.local:
            return str(self.path)
        return f"LocalMods/{self.path.parts[-1]}"

    def get_bool_setting(self, key: str) -> bool:
        val = self.settings.get(key)
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() == "true"
        if isinstance(val, (int, float)):
            return val > 0
        return False

    @classmethod
    def build(cls, raw_path: Union[Path, str]) -> Optional["ModUnit"]:
        path = Path(raw_path)

        instance = cls(name="temp", path=path)

        if "LocalMods" in path.parts:
            instance.local = True

        try:
            instance._parse_filelist()

            if instance.corepackage:
                logging.warning(
                    f"Core packages not supported! Mod: '{instance.name}' | Steam ID: '{instance.steam_id}'"
                )
                return None

            instance.use_lua = instance._has_file(".[Ll][Uu][Aa]")
            instance.use_cs = instance._has_file_any([".[Cc][Ss]", ".[Dd][Ll][Ll]"])

            instance._parse_files_concurrently()
            instance._parse_metadata()

            return instance

        except (SkipLoadBuild, ValueError) as e:
            logger.error(f"Failed to build mod from {path}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error building mod from {path}: {e}")
            return None

    def _has_file(self, extension_pattern: str) -> bool:
        try:
            return any(True for _ in self.path.rglob(f"*{extension_pattern}"))
        except Exception:
            return False

    def _has_file_any(self, patterns: List[str]) -> bool:
        for pat in patterns:
            if self._has_file(pat):
                return True
        return False

    def _parse_filelist(self) -> None:
        file_list_path = self.path / "filelist.xml"
        if not file_list_path.exists():
            raise ValueError(f"{file_list_path} does not exist")

        xml_obj = XMLBuilder.load(file_list_path)
        if xml_obj is None:
            raise ValueError(f"{file_list_path} invalid xml struct")

        self.name = xml_obj.attributes.get("name", "Something went wrong")
        self.corepackage = xml_obj.attributes.get("corepackage", "false").lower() == "true"
        self.steam_id = xml_obj.attributes.get("steamworkshopid")

        self.metadata.game_version = xml_obj.attributes.get("gameversion", "base-not-specified")
        self.metadata.mod_version = xml_obj.attributes.get("modversion", "base-not-specified")

    def _parse_files_concurrently(self) -> None:
        """Сканирует XML файлы в многопоточном режиме."""
        xml_files = list(self.path.rglob("*.[Xx][Mm][Ll]"))

        if not xml_files:
            return

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self._process_single_xml, f_path): f_path
                for f_path in xml_files
            }

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    path = futures[future]
                    logger.error(f"Error processing XML {path}: {exc}")

    def _process_single_xml(self, xml_path: Path) -> None:
        try:
            f_name = xml_path.name.lower()

            if f_name == "modparts.xml":
                with self._lock:
                    self.has_toggle_content = True
                return

            if f_name in AppConfig.xml_system_dirs:
                return

            xml_obj = XMLBuilder.load(xml_path)
            if xml_obj is None:
                return

            id_parser_unit = extract_ids(xml_obj)

            if id_parser_unit.add_id or id_parser_unit.override_id:
                with self._lock:
                    self.add_id.update(id_parser_unit.add_id)
                    self.override_id.update(id_parser_unit.override_id)

            if not self.has_toggle_content:
                has_btm = any(True for _ in xml_obj.find_only_comments("BTM:*"))
                if has_btm:
                    with self._lock:
                        self.has_toggle_content = True

        except Exception as err:
            logger.error(f"Error parsing {xml_path}: {err}", exc_info=True)

    def _resolve_metadata_path(self) -> Optional[Path]:
        local_meta = self.path / "metadata.xml"
        if local_meta.exists():
            return local_meta

        search_pattern = f"{self.id}.xml"
        internal_lib = AppConfig.get_data_root_path() / "InternalLibrary"
        try:
            return next(internal_lib.rglob(search_pattern))
        except StopIteration:
            return None

    def _parse_metadata(self) -> None:
        meta_path = self._resolve_metadata_path()
        if not meta_path:
            return

        xml_obj = XMLBuilder.load(meta_path)
        if xml_obj is None:
            logger.warning(f"Empty metadata.xml for {self.id}")
            return

        self._apply_metadata_xml(xml_obj)

    def update_meta_errors(self) -> None:
        self.metadata.errors.clear()
        self.metadata.warnings.clear()

        meta_path = self._resolve_metadata_path()
        if not meta_path:
            return

        xml_obj = XMLBuilder.load(meta_path)
        if xml_obj is None:
            return

        for element in xml_obj.find_only_elements("meta"):
            self._extract_meta_info(element)

    def _apply_metadata_xml(self, xml_obj: Any) -> None:
        for element in xml_obj.iter_non_comment_childrens():
            tag = element.tag.lower()

            if tag == "settings":
                for ch in element.iter_non_comment_childrens():
                    name = ch.attributes.get("name")
                    if name:
                        self.settings[name] = ch.attributes.get("value")

            elif tag == "meta":
                self._extract_meta_info(element)

            elif tag == "dependencies":
                self._extract_dependencies(element)

    def _extract_meta_info(self, meta_element: Any) -> None:
        for ch in meta_element.iter_non_comment_childrens():
            tag = ch.tag.lower()
            content = ch.content.strip()

            if tag == "author":
                self.metadata.author_name = content
            elif tag == "license":
                self.metadata.license = content
            elif tag == "warning":
                self.metadata.warnings.extend(content.splitlines())
            elif tag == "error":
                self.metadata.errors.extend(content.splitlines())

    def _extract_dependencies(self, deps_element: Any) -> None:
        new_deps = []
        for ch in deps_element.iter_non_comment_childrens():
            dep_type = ch.tag

            if not Dependency.is_valid_type(dep_type):
                logger.warning(f"Ignoring unsupported dependency type '{dep_type}'")
                continue

            name = ch.attributes.get("name")
            steam_id = ch.attributes.get("steamID")

            if not name and not steam_id:
                continue

            attrs = ch.attributes.copy()
            attrs.pop("name", None)
            attrs.pop("steamID", None)
            condition = attrs.pop("condition", None)

            dep = Dependency(
                name=name or "",
                steam_id=steam_id,
                type=dep_type,
                attributes=attrs,
                condition=condition,
            )
            new_deps.append(dep)

        self.metadata.dependencies.extend(new_deps)

Dependencie = Dependency