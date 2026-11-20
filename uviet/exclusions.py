"""User preferences shared by the engine and settings window."""

import fcntl
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from gi.repository import GLib

CONFIG_PATH = Path(GLib.get_user_config_dir()) / "uviet" / "excluded-apps.json"


def load_excluded():
    try:
        entries = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(entries, list):
        return set()
    return {value for value in entries if isinstance(value, str)}


def set_application_excluded(application, exclude):
    directory = CONFIG_PATH.parent
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "excluded-apps.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = load_excluded()
        if exclude:
            entries.add(application)
        else:
            entries.discard(application)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as output:
            temporary_path = Path(output.name)
            try:
                json.dump(sorted(entries), output, ensure_ascii=False)
                output.write("\n")
                output.close()
                os.replace(temporary_path, CONFIG_PATH)
            finally:
                temporary_path.unlink(missing_ok=True)
    return entries
