# Запуск и пересборка

## Запуск

Двойной щелчок по файлу `dist\4-ChatList.exe` или из PowerShell:

```powershell
.\dist\4-ChatList.exe
```

## Пересборка

```powershell
cd f:\Projects\Cursor\Work\4-ChatList
python -m pip install pyinstaller
python -m PyInstaller 4-ChatList.spec
```
