import hashlib
import logging
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

# Импортируем ModUnit, чтобы pickle знал этот класс при загрузке
from Code.package.dataclasses import ModUnit
from Code.app_vars import AppConfig

logger = logging.getLogger(__name__)

class CacheManager:
    _cache_file = Path("mod_cache.pkl")
    # Структура кэша: { "absolute_path_to_mod": ( "combined_hash", ModUnitObject ) }
    _cache_data: Dict[str, Tuple[str, ModUnit]] = {}
    _is_dirty = False

    @staticmethod
    def init():
        """Загружает кэш с диска при старте."""
        # Можно положить кэш в папку конфигов, чтобы не мусорить в корне
        cache_dir = AppConfig.get_data_root_path() # Или другая папка
        if cache_dir:
            CacheManager._cache_file = cache_dir / "mod_cache.pkl"

        if CacheManager._cache_file.exists():
            try:
                with open(CacheManager._cache_file, "rb") as f:
                    CacheManager._cache_data = pickle.load(f)
                logger.info(f"Loaded cache with {len(CacheManager._cache_data)} mods.")
            except Exception as e:
                logger.warning(f"Failed to load cache (it might be corrupt or outdated): {e}")
                CacheManager._cache_data = {}

    @staticmethod
    def save():
        """Сохраняет кэш на диск, если были изменения."""
        if not CacheManager._is_dirty:
            return

        try:
            with open(CacheManager._cache_file, "wb") as f:
                pickle.dump(CacheManager._cache_data, f)
            logger.info("Cache saved to disk.")
            CacheManager._is_dirty = False
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    @staticmethod
    def get_cached_mod(mod_path: Path) -> Optional[ModUnit]:
        """
        Возвращает ModUnit, если хеш файлов совпадает.
        Иначе возвращает None.
        """
        path_key = str(mod_path.resolve())
        cached_entry = CacheManager._cache_data.get(path_key)

        if not cached_entry:
            return None

        cached_hash, mod_unit = cached_entry
        current_hash = CacheManager._compute_mod_hash(mod_path)

        if current_hash == cached_hash:
            return mod_unit
        
        return None

    @staticmethod
    def update_cache(mod: ModUnit):
        """Обновляет запись в кэше для данного мода."""
        if not mod or not mod.path:
            return

        path_key = str(mod.path.resolve())
        current_hash = CacheManager._compute_mod_hash(mod.path)
        
        CacheManager._cache_data[path_key] = (current_hash, mod)
        CacheManager._is_dirty = True

    @staticmethod
    def _compute_mod_hash(mod_path: Path) -> str:
        """
        Считает MD5 от filelist.xml и metadata.xml.
        Чтение файлов намного быстрее парсинга XML и обхода директорий.
        """
        hasher = hashlib.md5()
        
        # Список критических файлов, влияющих на структуру мода
        files_to_check = ["filelist.xml", "metadata.xml"]
        
        for filename in files_to_check:
            f_path = mod_path / filename
            if f_path.exists():
                try:
                    # Читаем небольшими блоками, чтобы не забивать память
                    with open(f_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
                except OSError:
                    pass
        
        return hasher.hexdigest()

    @staticmethod
    def clear():
        CacheManager._cache_data = {}
        CacheManager._is_dirty = True
        if CacheManager._cache_file.exists():
            try:
                CacheManager._cache_file.unlink()
            except OSError:
                pass