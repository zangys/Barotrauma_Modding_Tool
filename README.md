<div align="right">

**[English](#barotrauma-modding-tool-enchanted-edition) | [Русский](#barotrauma-modding-tool-enchanted-edition-ru)**

</div>

---

## Barotrauma Modding Tool: Enchanted Edition

![GitHub release (latest by date)](https://img.shields.io/github/v/release/zangys/Barotrauma_modding_tool_enchanted?label=release)

This is an enhanced fork of the original [Barotrauma Modding Tool](https://github.com/themanyfaceddemon/Barotrauma_Modding_Tool) by **TheManyFacedDemon**. 

The goal of this version is to add new quality-of-life features, improve compatibility, and make the tool even more convenient for the community.

### New Features in This Fork

This version includes all the great features of the original, plus:

- **Workshop Sync Button**: No more launching the game just to get your new mods! A new "Sync Workshop" button allows you to copy newly subscribed mods directly from your Steam Workshop folder. *Note: You need to specify the path in the settings first.*

- **"Activate All" Button**: Tired of dragging dozens of mods one by one? Activate your entire mod collection with a single click.

- **Full Linux Support**: The issue where the game would fail to launch from the tool on Linux has been completely fixed. The app now uses Steam to launch the game, ensuring the correct environment and full compatibility.

### Installation

The easiest way to get started is to download a ready-to-use version.

1. Go to the [**Releases Page**](https://github.com/zangys/Barotrauma_modding_tool_enchanted/releases/latest).
2. Download the latest ZIP archive for your operating system (e.g., `BMTE-windows-64bit.zip`).
3. Extract the archive to a convenient location on your computer.
4. Run the executable file (`BMTE.exe` on Windows, `BMTE` on Linux).

### Building from Source

If you prefer to build the application yourself, follow these steps:

#### Requirements
- [Python 3.12 or higher](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

#### Steps
1. **Clone the Repository**
   ```bash
   git clone https://github.com/zangys/Barotrauma_modding_tool_enchanted.git
   ```

2. **Install Dependencies**
   ```bash
   cd Barotrauma_modding_tool_enchanted
   python -m venv venv
   # On Windows: venv\Scripts\activate
   # On Linux/macOS: source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

### Support and Contributions

If you encounter any issues with this fork or have ideas for new features, please [open an issue](https://github.com/zangys/Barotrauma_modding_tool_enchanted/issues) in this repository.

### License

This project is licensed under the GPL-3.0 License. See the [LICENSE](./LICENSE) file for details.

---

## Barotrauma Modding Tool: Enchanted Edition (ru)

![GitHub release (latest by date)](https://img.shields.io/github/v/release/zangys/Barotrauma_modding_tool_enchanted?label=release)

Это улучшенный форк оригинального инструмента [Barotrauma Modding Tool](https://github.com/themanyfaceddemon/Barotrauma_Modding_Tool) от автора **TheManyFacedDemon**.

Цель этой версии — добавить новые полезные функции, улучшить совместимость и сделать инструмент еще более удобным для сообщества.

### Новые функции в этом форке

Эта версия включает в себя все замечательные возможности оригинала, а также:

- **Кнопка "Синхронизировать Мастерскую"**: Больше не нужно запускать игру, чтобы получить новые моды! Новая кнопка позволяет копировать свежескачанные моды напрямую из вашей папки Мастерской Steam. *Примечание: для этого сначала нужно указать путь в настройках.*

- **Кнопка "Активировать все"**: Устали перетаскивать десятки модов по одному? Активируйте всю вашу коллекцию модов одним нажатием.

- **Полная поддержка Linux**: Проблема, из-за которой игра не запускалась из инструмента в Linux, была полностью исправлена. Приложение теперь использует Steam для запуска игры, обеспечивая правильное окружение и полную совместимость.

### Установка

Самый простой способ начать — скачать готовую к использованию версию.

1. Перейдите на [**страницу релизов**](https://github.com/zangys/Barotrauma_modding_tool_enchanted/releases/latest).
2. Скачайте последний ZIP-архив для вашей операционной системы (например, `BMTE-windows-64bit.zip`).
3. Распакуйте архив в удобное для вас место.
4. Запустите исполняемый файл (`BMTE.exe` в Windows, `BMTE` в Linux).

### Сборка из исходного кода

Если вы предпочитаете собрать приложение самостоятельно, следуйте этим шагам:

#### Требования
- [Python 3.12 или выше](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

#### Шаги
1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/zangys/Barotrauma_modding_tool_enchanted.git
   ```

2. **Установите зависимости**
   ```bash
   cd Barotrauma_modding_tool_enchanted
   python -m venv venv
   # В Windows: venv\Scripts\activate
   # В Linux/macOS: source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Запустите приложение**
   ```bash
   python main.py
   ```

### Поддержка и участие

Если вы столкнулись с какими-либо проблемами или у вас есть идеи для новых функций, пожалуйста, [создайте issue](https://github.com/zangys/Barotrauma_modding_tool_enchanted/issues) в этом репозитории.

### Лицензия

Этот проект лицензирован под лицензией GPL-3.0. Подробности смотрите в файле [LICENSE](./LICENSE).
