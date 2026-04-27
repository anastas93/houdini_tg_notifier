import hou
hou.appendSessionModuleSource('''hou.hscript("autosave on")''')

# ─── TG Notifier - автозапуск ────────────────────────────────────────────────
import sys, os
_plugin = os.path.join(os.path.expanduser("~"), "houdini_tg_notifier")
if _plugin not in sys.path:
    sys.path.insert(0, _plugin)

try:
    from tg_notifier import get_notifier
    _n = get_notifier()
    if _n.settings.get("monitor_enabled"):
        _n.start()
        print("[TG Notifier] Monitor started")
    else:
        print("[TG Notifier] Loaded (monitor off)")
except Exception as e:
    print("[TG Notifier] Load error:", e)


# ─── TG Notifier - Octane postRender hook ────────────────────────────────────
def _tgn_attach_octane_hooks():
    import sys, os
    _plugin = os.path.join(os.path.expanduser("~"), "houdini_tg_notifier")
    if _plugin not in sys.path:
        sys.path.insert(0, _plugin)

    def _make_post_render_cb(node_path):
        def _cb(node, event_type, **kwargs):
            if event_type != hou.ropEventType.postRender:
                return
            try:
                from tg_notifier import get_notifier, send_telegram
                from datetime import datetime
                n = get_notifier()
                s = n.settings
                if not s.get("send_render", True):
                    return
                ts = datetime.now().strftime("%H:%M:%S")
                scene = os.path.basename(hou.hipFile.name())
                text = "[OK] <b>OCTANE RENDER COMPLETE</b>\n<b>Time:</b> {}\n<b>Scene:</b> {}\n<b>ROP:</b> {}".format(
                    ts, scene, node_path
                )
                send_telegram(s["bot_token"], s["chat_id"], text)
            except Exception as e:
                print("[TG Notifier] Octane postRender error:", e)
        return _cb

    def _hook_all_octane_rops():
        for node in hou.node("/").allSubChildren():
            try:
                if "octane" in node.type().name().lower():
                    cb = _make_post_render_cb(node.path())
                    node.addEventCallback((hou.ropEventType.postRender,), cb)
                    print("[TG Notifier] postRender hooked:", node.path())
            except Exception:
                pass

    _hook_all_octane_rops()

    def _on_hip_event(event_type):
        if event_type in (hou.hipFileEventType.AfterLoad, hou.hipFileEventType.AfterMerge):
            _hook_all_octane_rops()

    try:
        hou.hipFile.addEventCallback(_on_hip_event)
    except Exception:
        pass

_tgn_attach_octane_hooks()


# ─── TG Notifier - Octane preRender hook (старт рендера) ─────────────────────
def _tgn_attach_octane_pre_hooks():
    import sys, os
    _plugin = os.path.join(os.path.expanduser("~"), "houdini_tg_notifier")
    if _plugin not in sys.path:
        sys.path.insert(0, _plugin)

    def _make_pre_render_cb(node_path):
        def _cb(node, event_type, **kwargs):
            if event_type != hou.ropEventType.preRender:
                return
            try:
                from tg_notifier import get_notifier, send_telegram
                from datetime import datetime
                n = get_notifier()
                s = n.settings
                if not s.get("send_render", True):
                    return

                ts = datetime.now().strftime("%H:%M:%S")
                scene = os.path.basename(hou.hipFile.name())

                try:
                    cam = node.parm("camera").eval()
                except Exception:
                    cam = "unknown"

                try:
                    f_start = int(node.parm("f1").eval())
                    f_end   = int(node.parm("f2").eval())
                    f_step  = node.parm("f3").eval()
                    total   = int((f_end - f_start) / f_step) + 1
                    frames  = "{} - {} ({} frames)".format(f_start, f_end, total)
                except Exception:
                    frames = "unknown"

                text = (
                    "[>>] <b>OCTANE RENDER STARTED</b>\n"
                    "<b>Time:</b> {}\n"
                    "<b>Scene:</b> {}\n"
                    "<b>ROP:</b> {}\n"
                    "<b>Camera:</b> {}\n"
                    "<b>Frames:</b> {}"
                ).format(ts, scene, node_path, cam, frames)

                send_telegram(s["bot_token"], s["chat_id"], text)
            except Exception as e:
                print("[TG Notifier] Octane preRender error:", e)
        return _cb

    def _hook_pre_all_octane_rops():
        for node in hou.node("/").allSubChildren():
            try:
                if "octane" in node.type().name().lower():
                    cb = _make_pre_render_cb(node.path())
                    node.addEventCallback((hou.ropEventType.preRender,), cb)
            except Exception:
                pass

    _hook_pre_all_octane_rops()

    def _on_hip_event_pre(event_type):
        if event_type in (hou.hipFileEventType.AfterLoad, hou.hipFileEventType.AfterMerge):
            _hook_pre_all_octane_rops()

    try:
        hou.hipFile.addEventCallback(_on_hip_event_pre)
    except Exception:
        pass

_tgn_attach_octane_pre_hooks()
