"""Per-application input rules for GNOME."""

import json

from gi.repository import Gio, GLib

from exclusions import CONFIG_PATH, MODE_PREEDIT, load_application_modes, set_application_mode

SHELL_NAME = "org.gnome.Shell"
FOCUS_INTERFACE = "org.gnome.shell.extensions.FocusedWindow"
FOCUS_PATH = "/org/gnome/shell/extensions/FocusedWindow"
PICKER_INTERFACE = "org.gnome.Shell.Extensions.UVietPicker"
PICKER_PATH = "/org/gnome/Shell/Extensions/UVietPicker"


class ApplicationRules:
    def __init__(self):
        self.modes = load_application_modes()
        self.monitor = None
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.monitor = Gio.File.new_for_path(str(CONFIG_PATH.parent)).monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, None,
            )
            self.monitor.connect("changed", self.on_config_changed)
        except (OSError, GLib.Error):
            pass
        self.current = ""
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            return
        self.bus.signal_subscribe(
            SHELL_NAME, PICKER_INTERFACE, "FocusChanged", PICKER_PATH, None,
            Gio.DBusSignalFlags.NONE, self.on_picker_focus_changed,
        )
        self.bus.signal_subscribe(
            SHELL_NAME, FOCUS_INTERFACE, "FocusChanged", FOCUS_PATH, None,
            Gio.DBusSignalFlags.NONE, self.on_focus_changed,
        )
        self.bus.signal_subscribe(
            "org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged",
            "/org/freedesktop/DBus", SHELL_NAME, Gio.DBusSignalFlags.NONE,
            self.on_shell_changed,
        )
        self.refresh()

    def on_config_changed(self, monitor, file, other_file, event):
        if any(item and item.get_path() == str(CONFIG_PATH) for item in (file, other_file)):
            self.modes = load_application_modes()

    def read_focus(self, response):
        self.current = ""
        try:
            data = json.loads(response.unpack()[0])
        except ValueError:
            return
        if isinstance(data, dict) and isinstance(data.get("wm_class"), str):
            self.current = data["wm_class"].strip().casefold()

    def on_focus_changed(self, connection, sender, path, interface, signal, parameters):
        self.read_focus(parameters)

    def on_picker_focus_changed(self, connection, sender, path, interface, signal, parameters):
        self.current = parameters.unpack()[0].strip().casefold()

    def on_shell_changed(self, connection, sender, path, interface, signal, parameters):
        self.current = ""
        if parameters.unpack()[2]:
            self.refresh()

    def refresh(self):
        try:
            response = self.bus.call_sync(
                SHELL_NAME, PICKER_PATH, PICKER_INTERFACE, "GetFocused", None,
                GLib.VariantType.new("(s)"), Gio.DBusCallFlags.NO_AUTO_START, 250, None,
            )
        except GLib.Error:
            pass
        else:
            self.current = response.unpack()[0].strip().casefold()
            return
        try:
            response = self.bus.call_sync(
                SHELL_NAME, FOCUS_PATH, FOCUS_INTERFACE, "Get", None,
                GLib.VariantType.new("(s)"), Gio.DBusCallFlags.NO_AUTO_START, 250, None,
            )
        except GLib.Error:
            self.current = ""
        else:
            self.read_focus(response)

    def mode_for(self, application):
        return self.modes.get(application, MODE_PREEDIT)

    def set_mode(self, application, mode):
        self.modes = set_application_mode(application, mode)
