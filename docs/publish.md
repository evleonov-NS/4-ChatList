# Публикация ChatList: GitHub Release и GitHub Pages

Пошаговая инструкция для выпуска версии **1.1.0** и следующих релизов.

Репозиторий: [github.com/evleonov-NS/4-ChatList](https://github.com/evleonov-NS/4-ChatList)  
Сайт (после настройки Pages): [evleonov-NS.github.io/4-ChatList](https://evleonov-NS.github.io/4-ChatList/)

---

## Что публикуется

| Артефакт | Файл | Назначение |
|----------|------|------------|
| Установщик | `ChatList-Setup-<версия>.exe` | Основной способ для пользователей Windows |
| Портативная версия | `4-ChatList-<версия>.exe` | Запуск без установки |
| Контрольные суммы | `SHA256SUMS.txt` | Проверка целостности файлов |
| Лендинг | `docs/index.html` | GitHub Pages |

---

## Шаг 0. Однократная настройка репозитория

### GitHub Pages

1. Откройте **Settings → Pages** в репозитории.
2. В **Build and deployment → Source** выберите **GitHub Actions**.
3. После первого push в `main` workflow `.github/workflows/pages.yml` опубликует каталог `docs/`.

### Права Actions

1. **Settings → Actions → General → Workflow permissions** → **Read and write permissions**.
2. Это нужно для автоматической публикации Release по тегу.

---

## Шаг 1. Подготовка версии

1. Обновите версию в `version.py`:

   ```python
   __version__ = "1.2.0"
   ```

2. Закоммитьте изменения кода и документации в `main`.

3. Убедитесь, что в `docs/index.html` актуален блок `<span class="version">` (или обновите вручную).

---

## Шаг 2. Локальная сборка артефактов

```powershell
cd f:\Projects\Cursor\Work\4-ChatList
.\build.ps1
```

Проверьте файлы в `dist\`:

- `4-ChatList-<версия>.exe`
- `ChatList-Setup-<версия>.exe`

Подготовка папки для Release (копии + SHA256):

```powershell
.\scripts\prepare-release.ps1
```

Результат: каталог `release\` с файлами и `SHA256SUMS.txt`.

---

## Шаг 3. Release notes

1. Скопируйте шаблон:

   ```powershell
   Copy-Item docs\release-notes-template.md release\notes-v1.1.0.md
   ```

2. Заполните разделы «Что нового», «Установка», «Известные ограничения».

3. Текст из `release\notes-v1.1.0.md` пойдёт в описание GitHub Release.

---

## Шаг 4. GitHub Release (вручную)

### 4.1. Тег

```powershell
git add .
git commit -m "Версия 1.1.0"
git push

git tag -a v1.1.0 -m "ChatList 1.1.0"
git push origin v1.1.0
```

Формат тега: **`v` + версия из `version.py`** (например `v1.1.0`).

### 4.2. Создание Release в интерфейсе GitHub

1. **Releases → Draft a new release**.
2. **Choose a tag:** `v1.1.0`.
3. **Release title:** `ChatList 1.1.0`.
4. **Description:** вставьте текст из `release\notes-v1.1.0.md`.
5. **Attach binaries:**
   - `release\ChatList-Setup-1.1.0.exe`
   - `release\4-ChatList-1.1.0.exe`
   - `release\SHA256SUMS.txt`
6. Отметьте **Set as the latest release** → **Publish release**.

### 4.3. Через GitHub CLI (альтернатива)

```powershell
gh release create v1.1.0 `
  --title "ChatList 1.1.0" `
  --notes-file release\notes-v1.1.0.md `
  release\ChatList-Setup-1.1.0.exe `
  release\4-ChatList-1.1.0.exe `
  release\SHA256SUMS.txt
```

---

## Шаг 5. GitHub Release (автоматически по тегу)

Если настроен workflow `.github/workflows/release.yml`:

1. Обновите `version.py` и закоммитьте в `main`.
2. Создайте и запушьте тег:

   ```powershell
   git tag -a v1.1.0 -m "ChatList 1.1.0"
   git push origin v1.1.0
   ```

3. Actions соберёт exe и установщик на `windows-latest` и создаст Release с артефактами.

Проверка: **Actions → Release** → статус **success** → **Releases** на GitHub.

---

## Шаг 6. GitHub Pages

Лендинг лежит в `docs/index.html`. Публикация при push в `main`:

```powershell
git add docs\index.html docs\publish.md
git commit -m "Обновлён лендинг"
git push
```

Workflow **Pages** задеплоит сайт за 1–2 минуты.

Проверка: **Actions → GitHub Pages** → URL в логе деплоя.

---

## Шаг 7. Проверка после публикации

- [ ] [Releases/latest](https://github.com/evleonov-NS/4-ChatList/releases/latest) открывается и содержит установщик.
- [ ] Установщик ставит программу на чистой Windows.
- [ ] После установки создаётся `.env.example`; пользователь копирует в `.env` и указывает `OPENROUTER_API_KEY`.
- [ ] [GitHub Pages](https://evleonov-NS.github.io/4-ChatList/) открывается, кнопка «Скачать» ведёт на latest release.
- [ ] `SHA256SUMS.txt` совпадает с локальной проверкой:

  ```powershell
  Get-FileHash release\ChatList-Setup-1.1.0.exe -Algorithm SHA256
  ```

---

## Чеклист каждого нового релиза

1. [ ] Обновить `version.py`
2. [ ] Обновить версию в `docs/index.html`
3. [ ] `.\build.ps1`
4. [ ] `.\scripts\prepare-release.ps1`
5. [ ] Заполнить release notes
6. [ ] Commit + push в `main`
7. [ ] `git tag -a vX.Y.Z` + `git push origin vX.Y.Z`
8. [ ] Проверить Release и Pages

---

## Что не публиковать

- `.env` с реальными ключами API
- `chatlist.db`, `logs/`, `dist/` (локальные артефакты)
- `.venv/`, `build/`

Все перечисленное уже в `.gitignore`.
