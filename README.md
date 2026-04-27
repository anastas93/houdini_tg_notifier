# Houdini → Telegram Notifier

Плагин для Houdini 19.5+ который отправляет уведомления в Telegram:
- ошибки и предупреждения из консоли в реальном времени
- старт и завершение рендера Octane (камера, ROP, диапазон кадров)

---

## Файлы в архиве

```
houdini_tg_notifier/
  tg_notifier.py          — ядро плагина (мониторинг, Telegram API)
  tg_notifier_panel.py    — UI панель для Houdini (Python Panel)
123.py                    — скрипт автозапуска при старте Houdini
install.py                — скрипт автоустановки
README.md                 — эта документация
```

---

## Быстрая установка

```
python install.py
```

Скрипт:
- скопирует плагин в `~/houdini_tg_notifier/`
- пропишет автозапуск в `Documents/houdiniXX.X/scripts/123.py`
- создаст файл настроек `~/.houdini_tg_notifier.json`
- выведет инструкцию по добавлению Python Panel

---

## Ручная установка (если install.py не нужен)

**Шаг 1** — Скопировать папку `houdini_tg_notifier/` в домашний каталог:
```
C:\Users\<имя>\houdini_tg_notifier\
```

**Шаг 2** — Скопировать `123.py` в:
```
C:\Users\<имя>\Documents\houdini21.0\scripts\123.py
```
Если `123.py` уже существует — дописать содержимое в конец файла (блоки начиная с `# ─── TG Notifier`).

**Шаг 3** — Добавить Python Panel в Houdini (см. ниже).

---

## Настройка Python Panel

1. **Windows → Python Panel Editor → (+) New Panel**
2. Заполнить:
   - **Label:** `TG Notifier`
   - **Name:** `tg_notifier`
3. Вкладка **Interface** → поле **Script**, вставить одну строку:
   ```python
   exec(open(r"C:\Users\<имя>\houdini_tg_notifier\tg_notifier_panel.py", encoding="utf-8").read())
   ```
4. **Apply → Accept**
5. Открыть: **Windows → TG Notifier**

---

## Создание Telegram бота

1. Написать @BotFather → `/newbot` → получить **Token**
2. Написать боту любое сообщение
3. Открыть в браузере:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   Найти `"chat":{"id": ЧИСЛО}` — это **Chat ID**

Либо просто написать @userinfobot — он ответит твоим ID.

---

## Первый запуск

1. Открыть панель **TG Notifier** в Houdini
2. Вставить **Bot Token** и **Chat ID**
3. Нажать **Test** — должно прийти тестовое сообщение
4. Нажать **Save**
5. Нажать **Start Monitor**

После этого мониторинг будет запускаться автоматически при каждом старте Houdini.

---

## Что отправляется

| Событие | Пример |
|---|---|
| Старт Octane рендера | `[>>] OCTANE RENDER STARTED` + камера, ROP, кадры |
| Завершение рендера | `[OK] OCTANE RENDER COMPLETE` + время, сцена, ROP |
| Ошибка | `[X] ERROR` + текст ошибки |
| Предупреждение | `[!] WARNING` |
| Сообщение | `[i] MESSAGE` |

---

## Файл настроек

`~/.houdini_tg_notifier.json` — редактируется через UI панели или вручную:

```json
{
  "bot_token": "123456:ABC-DEF...",
  "chat_id": "-100123456789",
  "send_errors": true,
  "send_warnings": true,
  "send_messages": true,
  "send_render": true,
  "scene_name_in_msg": true,
  "monitor_enabled": true,
  "cooldown": 15
}
```

`cooldown` — минимальная пауза в секундах между повторными отправками одного и того же сообщения (защита от спама).

---

## Повторная установка после переустановки Houdini

```
python install.py
```

Настройки (`bot_token`, `chat_id`) сохраняются в `~/.houdini_tg_notifier.json` и не удаляются при переустановке Houdini. После запуска `install.py` нужно только заново добавить Python Panel (Шаг 3 выше).

---

## Совместимость

| Компонент | Версия |
|---|---|
| Houdini | 19.5+ (LogSink API) / 18.x fallback через лог-файл |
| Octane for Houdini | любая (через ROP event callback) |
| Python | 3.9+ |
| ОС | Windows, Linux, macOS |
