# Запуск и пересборка

Версия приложения задаётся один раз в `version.py` (`__version__`).

## Запуск

```powershell
python main.py
```

## Пересборка

Скрипт читает версию из `version.py`, собирает exe и (если установлен Inno Setup) установщик:

```powershell
cd f:\Projects\Cursor\Work\4-ChatList
.\build.ps1
```

Результат:

- `dist\4-ChatList-<версия>.exe` — портативный exe
- `dist\ChatList-Setup-<версия>.exe` — установщик (Inno Setup 6)

### Установка и удаление

Установщик создаёт пункт в «Приложения и возможности» Windows и ярлык **«Удалить ChatList»** в меню «Пуск».

При удалении:

1. Завершается запущенный процесс `4-ChatList-<версия>.exe`.
2. Предлагается удалить пользовательские данные: `chatlist.db`, `logs`, `.env`.
3. Удаляются файлы программы из каталога установки.

Ручная сборка только exe:

```powershell
python -m pip install pyinstaller
python -m PyInstaller 4-ChatList.spec --noconfirm
```

Ручная сборка установщика:

```powershell
$version = python -c "from version import __version__; print(__version__)"
iscc "/DAppVersion=$version" installer.iss
```
