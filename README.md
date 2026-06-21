# ChatList

Приложение на Python + PyQt6 для отправки одного промта в несколько нейросетей, сравнения ответов и сохранения полезных результатов.

## Возможности

- ввод промта или выбор из сохранённых;
- параллельная отправка в активные модели;
- временная таблица результатов с чекбоксами;
- сохранение выбранных ответов в SQLite;
- управление моделями и настройками;
- история сохранённых результатов;
- экспорт в Markdown / JSON;
- логирование запросов в `logs/requests.log`.

## Требования

- Python 3.11+
- Windows / Linux / macOS

## Установка

```powershell
cd f:\Projects\Cursor\Work\4-ChatList
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Отредактируйте `.env` и укажите ключ OpenRouter:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

## Запуск

```powershell
python main.py
```

> **Важно:** файл `.env` должен лежать в папке проекта (рядом с `main.py`)  
> или рядом с `4-ChatList-<версия>.exe` при запуске собранной версии.

```powershell
Copy-Item .env.example .env
# для exe:
Copy-Item .env dist\.env
```

При первом запуске создаётся база `chatlist.db` и добавляются **бесплатные** модели OpenRouter:

- OpenRouter Free (авто) — `openrouter/free`
- Gemma 4 26B (free)
- GPT-OSS 20B (free)

Кредиты на OpenRouter для `:free`-моделей не нужны. Лимиты: ~20 запросов/мин, ~50 запросов/день (без пополнения).  
Каталог: [openrouter.ai/models](https://openrouter.ai/models?q=free)

## Структура проекта

```text
main.py          — главное окно
db.py            — SQLite
models.py        — конфигурация моделей и ключи из .env
network.py       — HTTP-запросы к API
dialogs.py       — диалоги моделей, настроек и истории
workers.py       — фоновая отправка промтов
export_utils.py  — экспорт MD / JSON
```

## Сборка exe

Версия задаётся в `version.py` (`__version__`). См. [docs/run-and-build.md](docs/run-and-build.md).

```powershell
.\build.ps1
```

## Публикация

- [docs/publish.md](docs/publish.md) — пошаговая инструкция GitHub Release и GitHub Pages
- [docs/release-notes-template.md](docs/release-notes-template.md) — шаблон описания релиза
- Сайт: [evleonov-NS.github.io/4-ChatList](https://evleonov-NS.github.io/4-ChatList/) (после включения Pages)

```powershell
.\scripts\prepare-release.ps1
git tag -a v1.1.0 -m "ChatList 1.1.0"
git push origin v1.1.0
```

## Документация

- [PROJECT.md](PROJECT.md) — спецификация
- [PLAN.md](PLAN.md) — план реализации
- [DATABASE.md](DATABASE.md) — схема БД
