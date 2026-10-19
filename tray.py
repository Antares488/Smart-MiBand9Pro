"""System-tray companion for the Redmi Watch dashboard.

Separate process: talks to the service only over HTTP, so it can never
destabilize the watch connection. Run hidden with pythonw tray.py.

Icon color = status:  green connected · red disconnected · violet sleep recording.
Tooltip = live HR. Menu: open dashboard, sync, gentle cue, sleep toggle, exit.
"""
import json
import threading
import time
import urllib.request
import webbrowser
import os
from app_paths import data_dir

import pystray
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8765"

state = {"connected": False, "hr": 0, "sleep": False, "ok": False}


def _get(path, timeout=4):
    return json.load(urllib.request.urlopen(BASE + path, timeout=timeout))


def _post(path):
    try:
        req = urllib.request.Request(BASE + path, b"{}", {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=4)
    except Exception:
        pass


def fetch():
    try:
        d = _get("/state")
        state["connected"] = bool(d.get("connected"))
        state["hr"] = (d.get("stats") or {}).get("hr_cur") or 0
        state["sleep"] = bool((d.get("sleep_session") or {}).get("active"))
        state["ok"] = True
    except Exception:
        state.update(connected=False, hr=0, sleep=False, ok=False)


def icon_img():
    if state["sleep"]:
        col = (139, 92, 246)      # violet: sleep recording
    elif state["connected"]:
        col = (52, 199, 123)      # green: live
    else:
        col = (235, 87, 87)       # red: disconnected / service down
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18, 2, 46, 12], radius=4, fill=(70, 70, 78))    # strap top
    d.rounded_rectangle([18, 52, 46, 62], radius=4, fill=(70, 70, 78))   # strap bottom
    d.rounded_rectangle([10, 8, 54, 56], radius=14, fill=(38, 38, 44))   # case
    d.rounded_rectangle([16, 14, 48, 50], radius=10, fill=col)           # face = status
    return img


def tooltip():
    if not state["ok"]:
        return "Redmi Watch: сервис не отвечает"
    parts = []
    parts.append("пульс %d" % state["hr"] if state["hr"] else "нет пульса")
    if state["sleep"]:
        parts.append("запись сна")
    parts.append("на связи" if state["connected"] else "нет связи")
    return "Redmi Watch: " + " · ".join(parts)


def run(controller=None):
    global BASE
    from windows_app import dashboard_url, autostart
    if controller is not None:
        BASE = dashboard_url()
    icon = pystray.Icon("redmi_watch", icon_img(), tooltip())

    def do_open(_i, _m):
        webbrowser.open(BASE + "/")

    def do_sync(_i, _m):
        try:
            result = _get("/sync")
            icon.notify("Синхронизация поставлена в очередь" if result.get("queued") else "Запрос уже отправлен", "SmartMiBand")
        except Exception as e:
            icon.notify(str(e), "Ошибка синхронизации")

    def do_cue(_i, _m):
        _post("/cue")

    def do_sleep(_i, _m):
        _post("/sleep/stop" if state["sleep"] else "/sleep/start")
        fetch()

    def task(action):
        def worker():
            try:
                action()
            except Exception as e:
                icon.notify(str(e), "SmartMiBand: ошибка")
            finally:
                icon.update_menu()
        threading.Thread(target=worker, daemon=True).start()

    def start_service():
        global BASE
        controller.start()
        BASE = dashboard_url()

    def do_start(_i, _m):
        task(start_service)

    def do_stop(_i, _m):
        if state["sleep"]:
            icon.notify("Сначала завершите запись сна в дашборде", "Сервис продолжает работу")
            return
        task(controller.stop)

    def do_autostart(_i, _m):
        task(lambda: autostart(not autostart()))

    def do_config(_i, _m):
        os.startfile(str(data_dir() / "config.json"))

    def do_exit(_i, _m):
        if state["sleep"] and controller and controller.running():
            icon.notify("Сначала завершите запись сна в дашборде", "Сервис продолжает работу")
            return
        def finish():
            if controller:
                controller.stop()
            icon.stop()
        task(finish)


    items = [
        pystray.MenuItem("Открыть дашборд", do_open, default=True),
        pystray.MenuItem("Синхронизировать", do_sync),
        pystray.MenuItem("Мягкий сигнал на часы", do_cue),
        pystray.MenuItem(lambda _: "Остановить запись сна" if state["sleep"] else "Начать запись сна", do_sleep),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход (остановить сервис)", do_exit),
    ]
    if controller:
        items[1:1] = [
            pystray.MenuItem("Запустить сервис", do_start, enabled=lambda _: not controller.running() and not controller.stopping),
            pystray.MenuItem("Остановить сервис", do_stop, enabled=lambda _: controller.running() and not controller.stopping),
            pystray.MenuItem("Настройки (config.json)", do_config),
            pystray.MenuItem("Папка данных и логов", lambda _i, _m: os.startfile(str(data_dir()))),
            pystray.MenuItem("Автозапуск Windows", do_autostart, checked=lambda _: autostart()),
            pystray.Menu.SEPARATOR,
        ]
    icon.menu = pystray.Menu(*items)
    if controller:
        task(start_service)

    def poll():
        while True:
            if controller:
                try:
                    controller.recover()
                except Exception as e:
                    icon.notify(str(e), "Ошибка перезапуска сервиса")
            fetch()
            try:
                icon.icon = icon_img()
                icon.title = tooltip()
                icon.update_menu()
            except Exception:
                pass
            time.sleep(5)

    threading.Thread(target=poll, daemon=True).start()
    try:
        icon.run()
    finally:
        if controller:
            controller.stop()


if __name__ == "__main__":
    fetch()
    run()
