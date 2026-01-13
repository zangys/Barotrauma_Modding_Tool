"""
Модуль автообновления приложения.

Проверяет наличие новых версий через GitHub API,
скачивает и устанавливает обновления.
"""
import logging
import os
import platform
import shutil
import sys
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg
import requests

from Code.app_vars import AppConfig
from Code.loc import Localization as loc

logger = logging.getLogger(__name__)

# GitHub API URL
GITHUB_REPO = "zangys/Barotrauma_Modding_Tool_Enchanted"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class AutoUpdater:
    """Менеджер автообновления приложения."""

    _update_info: Optional[dict] = None
    _download_progress: float = 0.0
    _is_downloading: bool = False
    _is_standalone: bool = False

    @classmethod
    def init(cls) -> None:
        """Инициализирует модуль и определяет режим запуска."""
        # Определяем, запущено ли приложение как standalone (PyInstaller/Nuitka)
        cls._is_standalone = getattr(sys, 'frozen', False)
        logger.debug(f"AutoUpdater initialized. Standalone: {cls._is_standalone}")

    @classmethod
    def check_for_updates(cls) -> Optional[dict]:
        """Проверяет наличие обновлений через GitHub API.

        Returns:
            Словарь с информацией о релизе или None при ошибке.
        """
        try:
            response = requests.get(GITHUB_API_URL, timeout=15)
            if response.status_code == 200:
                release_data = response.json()
                latest_tag = release_data.get("tag_name", "")
                current_version = AppConfig.version

                if latest_tag and latest_tag != current_version:
                    cls._update_info = {
                        "tag_name": latest_tag,
                        "name": release_data.get("name", latest_tag),
                        "body": release_data.get("body", ""),
                        "html_url": release_data.get("html_url", ""),
                        "assets": release_data.get("assets", []),
                        "published_at": release_data.get("published_at", ""),
                    }
                    return cls._update_info
                else:
                    logger.info(f"Already on latest version: {current_version}")
                    return None
            else:
                logger.warning(f"GitHub API returned status {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to check for updates: {e}")
            return None

    @classmethod
    def get_download_url(cls) -> Optional[str]:
        """Возвращает URL для скачивания обновления под текущую платформу.

        Returns:
            URL ZIP-архива или None.
        """
        if not cls._update_info:
            return None

        system = platform.system().lower()
        arch = "64bit" if sys.maxsize > 2**32 else "32bit"

        # Ищем подходящий asset
        for asset in cls._update_info.get("assets", []):
            name = asset.get("name", "").lower()
            download_url = asset.get("browser_download_url", "")

            if system == "windows" and "windows" in name and arch in name:
                return download_url
            elif system == "linux" and "linux" in name and arch in name:
                return download_url
            elif system == "darwin" and ("macos" in name or "darwin" in name):
                return download_url

        # Если не нашли специфичный, возвращаем первый ZIP
        for asset in cls._update_info.get("assets", []):
            if asset.get("name", "").endswith(".zip"):
                return asset.get("browser_download_url")

        return None

    @classmethod
    def download_update(
        cls,
        download_url: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Optional[Path]:
        """Скачивает обновление во временную директорию.

        Args:
            download_url: URL файла для скачивания.
            progress_callback: Функция обратного вызова для прогресса (0.0-1.0).

        Returns:
            Путь к скачанному файлу или None при ошибке.
        """
        cls._is_downloading = True
        cls._download_progress = 0.0

        try:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            # Создаём временный файл
            temp_dir = Path(tempfile.gettempdir()) / "bmte_update"
            temp_dir.mkdir(parents=True, exist_ok=True)

            filename = download_url.split("/")[-1]
            file_path = temp_dir / filename

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            cls._download_progress = downloaded / total_size
                            if progress_callback:
                                progress_callback(cls._download_progress)

            cls._download_progress = 1.0
            logger.info(f"Update downloaded to: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Failed to download update: {e}")
            return None

        finally:
            cls._is_downloading = False

    @classmethod
    def extract_update(cls, zip_path: Path, target_dir: Optional[Path] = None) -> bool:
        """Распаковывает ZIP-архив с обновлением.

        Args:
            zip_path: Путь к ZIP-файлу.
            target_dir: Целевая директория (по умолчанию — temp).

        Returns:
            True при успехе, False при ошибке.
        """
        if target_dir is None:
            target_dir = zip_path.parent / "extracted"

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            logger.info(f"Update extracted to: {target_dir}")
            return True

        except zipfile.BadZipFile as e:
            logger.error(f"Failed to extract update: {e}")
            return False

    @classmethod
    def show_update_dialog(cls, parent: Optional[str] = None) -> None:
        """Показывает диалог обновления.

        Args:
            parent: Родительский элемент DPG (опционально).
        """
        if not cls._update_info:
            logger.warning("No update info available")
            return

        tag = "update_dialog"
        if dpg.does_item_exist(tag):
            dpg.focus_item(tag)
            return

        version = cls._update_info.get("tag_name", "")
        release_name = cls._update_info.get("name", version)
        release_notes = cls._update_info.get("body", "")[:500]  # Обрезаем заметки
        html_url = cls._update_info.get("html_url", "")

        with dpg.window(
            label=loc.get_string("update-available") if loc.has_string("update-available") else "Update Available",
            tag=tag,
            width=500,
            height=350,
            modal=True,
            no_collapse=True,
            on_close=lambda: dpg.delete_item(tag),
        ):
            dpg.add_text(
                f"{loc.get_string('update-new-version') if loc.has_string('update-new-version') else 'New version'}: {release_name}",
                color=(100, 255, 100),
            )
            dpg.add_separator()

            # Заметки о релизе
            with dpg.child_window(height=180, border=True):
                dpg.add_text(release_notes if release_notes else "No release notes.", wrap=460)

            dpg.add_spacer(height=10)

            # Кнопки
            with dpg.group(horizontal=True):
                if cls._is_standalone:
                    dpg.add_button(
                        label=loc.get_string("update-download-button") if loc.has_string("update-download-button") else "Download & Install",
                        width=150,
                        callback=lambda: cls._start_download_thread(),
                    )
                else:
                    # Для dev-версии — только ссылка
                    import webbrowser
                    dpg.add_button(
                        label=loc.get_string("update-open-github") if loc.has_string("update-open-github") else "Open GitHub",
                        width=150,
                        callback=lambda: webbrowser.open(html_url),
                    )

                dpg.add_button(
                    label=loc.get_string("update-later-button") if loc.has_string("update-later-button") else "Later",
                    width=100,
                    callback=lambda: dpg.delete_item(tag),
                )

            # Прогресс-бар (скрыт по умолчанию)
            dpg.add_spacer(height=5)
            dpg.add_progress_bar(
                tag="update_progress_bar",
                default_value=0.0,
                width=-1,
                show=False,
            )
            dpg.add_text(
                "",
                tag="update_status_text",
                color=(200, 200, 200),
            )

    @classmethod
    def _start_download_thread(cls) -> None:
        """Запускает скачивание в отдельном потоке."""
        download_url = cls.get_download_url()
        if not download_url:
            logger.error("No download URL available")
            if dpg.does_item_exist("update_status_text"):
                dpg.set_value(
                    "update_status_text",
                    loc.get_string("update-error-no-url") if loc.has_string("update-error-no-url") else "Error: No download available for your platform",
                )
            return

        # Показываем прогресс-бар
        if dpg.does_item_exist("update_progress_bar"):
            dpg.configure_item("update_progress_bar", show=True)
        if dpg.does_item_exist("update_status_text"):
            dpg.set_value(
                "update_status_text",
                loc.get_string("update-downloading") if loc.has_string("update-downloading") else "Downloading...",
            )

        def download_task():
            def update_progress(progress: float):
                if dpg.does_item_exist("update_progress_bar"):
                    dpg.set_value("update_progress_bar", progress)

            zip_path = cls.download_update(download_url, progress_callback=update_progress)

            if zip_path:
                if dpg.does_item_exist("update_status_text"):
                    dpg.set_value(
                        "update_status_text",
                        loc.get_string("update-download-complete") if loc.has_string("update-download-complete") else f"Downloaded: {zip_path}",
                    )
                # Открываем папку с загрузкой
                cls._open_download_folder(zip_path)
            else:
                if dpg.does_item_exist("update_status_text"):
                    dpg.set_value(
                        "update_status_text",
                        loc.get_string("update-download-failed") if loc.has_string("update-download-failed") else "Download failed!",
                    )

        thread = threading.Thread(target=download_task, daemon=True)
        thread.start()

    @staticmethod
    def _open_download_folder(file_path: Path) -> None:
        """Открывает папку с загруженным файлом в проводнике.

        Args:
            file_path: Путь к файлу.
        """
        folder = file_path.parent
        system = platform.system()

        try:
            if system == "Windows":
                os.startfile(folder)  # type: ignore
            elif system == "Darwin":
                import subprocess
                subprocess.run(["open", str(folder)])
            else:  # Linux
                import subprocess
                subprocess.run(["xdg-open", str(folder)])
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")

    @classmethod
    def get_update_info(cls) -> Optional[dict]:
        """Возвращает информацию о доступном обновлении."""
        return cls._update_info

    @classmethod
    def is_update_available(cls) -> bool:
        """Проверяет, доступно ли обновление."""
        return cls._update_info is not None
