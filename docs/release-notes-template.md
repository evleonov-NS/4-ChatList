## ChatList X.Y.Z

Краткое описание релиза в одном-двух предложениях.

### Что нового

- пункт 1
- пункт 2
- пункт 3

### Установка (Windows)

1. Скачайте **ChatList-Setup-X.Y.Z.exe** из Assets.
2. Запустите установщик и следуйте шагам мастера.
3. В каталоге установки скопируйте `.env.example` → `.env`.
4. Укажите ключ OpenRouter:

   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   ```

   Ключ: [openrouter.ai/keys](https://openrouter.ai/keys)

5. Запустите ChatList из меню «Пуск».

**Портативная версия:** `4-ChatList-X.Y.Z.exe` — положите `.env` рядом с exe.

### Проверка целостности

```powershell
Get-FileHash ChatList-Setup-X.Y.Z.exe -Algorithm SHA256
```

Сравните с `SHA256SUMS.txt` в этом Release.

### Системные требования

- Windows 10/11 (64-bit)
- Интернет для запросов к OpenRouter
- Ключ API OpenRouter (бесплатные модели `:free` не требуют пополнения баланса)

### Известные ограничения

- Ключ API задаётся вручную через файл `.env` (рядом с программой).
- Сборка и установщик ориентированы на Windows.

### Полная установка из исходников

См. [README](https://github.com/evleonov-NS/4-ChatList#%D1%83%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B0).
