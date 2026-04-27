"""
Houdini TG Notifier - скрипт установки
Запускать из обычного Python (не из Houdini):
    python install.py

Что делает:
  1. Копирует плагин в ~/houdini_tg_notifier/
  2. Определяет папку houdiniXX.X (последнюю версию)
  3. Создаёт/дополняет scripts/123.py
  4. Выводит инструкцию по настройке Python Panel
"""

import os
import sys
import shutil
import glob
import json

HERE = os.path.dirname(os.path.abspath(__file__))

# ─── Пути ────────────────────────────────────────────────────────────────────

HOME = os.path.expanduser("~")
PLUGIN_SRC  = os.path.join(HERE, "houdini_tg_notifier")
PLUGIN_DEST = os.path.join(HOME, "houdini_tg_notifier")

SETTINGS_FILE = os.path.join(HOME, ".houdini_tg_notifier.json")


def find_houdini_home():
    """Ищем Documents/houdiniXX.X — берём самую новую."""
    docs = os.path.join(HOME, "Documents")
    candidates = sorted(glob.glob(os.path.join(docs, "houdini*")), reverse=True)
    for c in candidates:
        if os.path.isdir(c) and os.path.basename(c).replace("houdini", "").replace(".", "").isdigit():
            return c

    # Fallback: ищем в HOME напрямую (Linux/Mac)
    candidates = sorted(glob.glob(os.path.join(HOME, "houdini*")), reverse=True)
    for c in candidates:
        if os.path.isdir(c):
            return c

    return None


def step(msg):
    print("\n[+] " + msg)


def ok(msg=""):
    print("    OK" + (" — " + msg if msg else ""))


def warn(msg):
    print("    WARN: " + msg)


# ─── Установка ────────────────────────────────────────────────────────────────

def install():
    print("=" * 55)
    print("  Houdini TG Notifier — Установка")
    print("=" * 55)

    # 1. Копируем плагин
    step("Копирование плагина в {}".format(PLUGIN_DEST))
    os.makedirs(PLUGIN_DEST, exist_ok=True)
    for fname in ("tg_notifier.py", "tg_notifier_panel.py"):
        src = os.path.join(PLUGIN_SRC, fname)
        dst = os.path.join(PLUGIN_DEST, fname)
        if not os.path.exists(src):
            warn("{} не найден, пропускаем".format(fname))
            continue
        shutil.copy2(src, dst)
        ok(fname)

    # 2. Находим houdini home
    step("Поиск директории Houdini")
    houdini_home = find_houdini_home()
    if not houdini_home:
        warn("Директория houdiniXX.X не найдена в Documents.")
        warn("После установки Houdini запусти install.py снова,")
        warn("или вручную скопируй 123.py в Documents/houdiniXX.X/scripts/")
    else:
        ok(houdini_home)

        # 3. Создаём/дополняем 123.py
        step("Настройка автозапуска (scripts/123.py)")
        scripts_dir = os.path.join(houdini_home, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        target_123 = os.path.join(scripts_dir, "123.py")
        src_123    = os.path.join(HERE, "123.py")

        if not os.path.exists(src_123):
            warn("123.py не найден рядом с install.py")
        else:
            with open(src_123, "r", encoding="utf-8") as f:
                new_content = f.read()

            if os.path.exists(target_123):
                with open(target_123, "r", encoding="utf-8") as f:
                    existing = f.read()
                if "tg_notifier" in existing:
                    ok("123.py уже содержит TG Notifier, пропускаем")
                else:
                    # Дописываем только наш блок (без строк autosave чтобы не дублировать)
                    tgn_block = new_content.split("# ─── TG Notifier", 1)
                    if len(tgn_block) > 1:
                        to_append = "\n# ─── TG Notifier" + tgn_block[1]
                    else:
                        to_append = "\n" + new_content
                    with open(target_123, "a", encoding="utf-8") as f:
                        f.write(to_append)
                    ok("Дописано в существующий 123.py")
            else:
                shutil.copy2(src_123, target_123)
                ok("123.py создан")

    # 4. Сохраняем настройки если их нет
    step("Проверка файла настроек")
    if not os.path.exists(SETTINGS_FILE):
        default = {
            "bot_token": "",
            "chat_id": "",
            "send_errors": True,
            "send_warnings": True,
            "send_messages": True,
            "send_render": True,
            "scene_name_in_msg": True,
            "monitor_enabled": False,
            "cooldown": 15,
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        ok("Создан {}".format(SETTINGS_FILE))
    else:
        ok("Уже существует, не трогаем")

    # 5. Инструкция по Python Panel
    print("\n" + "=" * 55)
    print("  Установка завершена!")
    print("=" * 55)
    print("""
Осталось добавить Python Panel в Houdini (один раз):

  1. Houdini → Windows → Python Panel Editor
  2. (+) New Panel
  3. Label:  TG Notifier
     Name:   tg_notifier
  4. Вкладка Interface → поле Script — вставить:

     exec(open(r"{panel}", encoding="utf-8").read())

  5. Apply → Accept
  6. Открыть: Windows → TG Notifier
  7. Ввести Bot Token + Chat ID → Test → Save → Start Monitor

Настройки хранятся в:
  {settings}
""".format(
        panel=os.path.join(PLUGIN_DEST, "tg_notifier_panel.py"),
        settings=SETTINGS_FILE,
    ))


if __name__ == "__main__":
    install()
