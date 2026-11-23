"""User preferences shared by the engine and settings window."""

import fcntl
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from gi.repository import GLib

CONFIG_PATH = Path(GLib.get_user_config_dir()) / "uviet" / "excluded-apps.json"


MODE_PREEDIT = "preedit"
MODE_DIRECT = "direct"
MODE_OFF = "off"
MODE_LABELS = {
    MODE_PREEDIT: "Ưu tiên tương thích (preedit)",
    MODE_DIRECT: "Gõ trực tiếp",
    MODE_OFF: "Tắt Telex",
}


def load_application_modes():
    try:
        entries = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(entries, list):
        return {app: MODE_OFF for app in entries if isinstance(app, str)}
    if isinstance(entries, dict):
        return {app: mode for app, mode in entries.items()
                if isinstance(mode, str) and mode in MODE_LABELS}
    return {}


def set_application_mode(application, mode):
    directory = CONFIG_PATH.parent
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "excluded-apps.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = load_application_modes()
        if mode is None:
            entries.pop(application, None)
        else:
            entries[application] = mode
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as output:
            temporary_path = Path(output.name)
            try:
                json.dump(entries, output, ensure_ascii=False, sort_keys=True)
                output.write("\n")
                output.close()
                os.replace(temporary_path, CONFIG_PATH)
            finally:
                temporary_path.unlink(missing_ok=True)
    return entries
