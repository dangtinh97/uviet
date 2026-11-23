#!/usr/bin/python3
"""GNOME settings window for UViet."""

import gi
import json
import re
from pathlib import Path
from xml.etree import ElementTree

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from applications import FOCUS_INTERFACE, FOCUS_PATH, PICKER_INTERFACE, PICKER_PATH, SHELL_NAME
from exclusions import (
    MODE_DIRECT, MODE_LABELS, MODE_OFF, MODE_PREEDIT, load_application_modes, set_application_mode,
)

SETTINGS_WINDOW_CLASSES = {"uviet-settings", "org.uviet.settings"}
CHATGPT_DESKTOP_ID = "chatgpt.desktop"
CHATGPT_SYSTEM_ENTRY = Path("/usr/share/applications") / CHATGPT_DESKTOP_ID
CHATGPT_WAYLAND_EXEC = (
    "Exec=/usr/bin/chatgpt --ozone-platform=wayland "
    "--enable-wayland-ime --wayland-text-input-version=3 %U"
)


def configure_chatgpt_wayland(source, destination):
    entry = source.read_text(encoding="utf-8")
    if CHATGPT_WAYLAND_EXEC in entry.splitlines():
        return
    entry, changed = re.subn(r"^Exec=(?:/usr/bin/)?chatgpt %U$", CHATGPT_WAYLAND_EXEC,
                             entry, count=1, flags=re.MULTILINE)
    if not changed:
        raise ValueError("Lối mở ChatGPT có lệnh riêng. UViet giữ nguyên lối mở đó.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    GLib.file_set_contents(str(destination), entry.encode("utf-8"))


def get_version():
    directory = Path(__file__).resolve().parent
    try:
        return (directory / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ElementTree.parse(directory.parent / "uviet.xml").getroot().findtext("version")


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Cài đặt UViet")
        self.set_default_size(460, 360)
        self.picking = False
        self.dragging = None
        self.pending_mode = None
        self.focus_signals = []
        self.focus_timeout = 0
        self.bus = application.get_dbus_connection()
        self.connect("destroy", self.stop_focus_pick)
        self.connect("key-press-event", self.on_key_press)
        self.set_titlebar(Gtk.HeaderBar(
            title="Cài đặt UViet", subtitle=f"Phiên bản {get_version()}", show_close_button=True,
        ))

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=18)
        self.add(content)
        info = Gtk.Label(label="Ứng dụng ngoài hai danh sách dùng chế độ tương thích.", xalign=0, wrap=True)
        content.pack_start(info, False, False, 0)

        self.lists = {}
        self.gestures = []
        notebook = Gtk.Notebook()
        for mode, description in (
            (MODE_DIRECT, "Gõ trong dòng ở ứng dụng hỗ trợ sửa chữ quanh con trỏ."),
            (MODE_OFF, "Chuyển nguyên phím cho ứng dụng, không xử lý dấu Telex."),
        ):
            notebook.append_page(self.mode_page(mode, description), Gtk.Label(label=MODE_LABELS[mode]))
        content.pack_start(notebook, True, True, 0)

        self.status = Gtk.Label(xalign=0, wrap=True)
        content.pack_start(self.status, False, False, 0)

        if GLib.getenv("WAYLAND_DISPLAY") and CHATGPT_SYSTEM_ENTRY.is_file():
            chatgpt = Gtk.Button(label="Dùng Wayland cho ChatGPT")
            chatgpt.set_halign(Gtk.Align.START)
            chatgpt.connect("clicked", self.enable_chatgpt_wayland)
            content.pack_start(chatgpt, False, False, 0)

        self.render_list()
        self.show_all()

    def enable_chatgpt_wayland(self, _button):
        destination = Path(GLib.get_user_data_dir()) / "applications" / CHATGPT_DESKTOP_ID
        source = destination if destination.exists() else CHATGPT_SYSTEM_ENTRY
        try:
            configure_chatgpt_wayland(source, destination)
        except ValueError as error:
            self.status.set_text(str(error))
        except (OSError, GLib.Error):
            self.status.set_text("Không cập nhật được lối mở ChatGPT.")
        else:
            self.status.set_text("Hãy thoát hẳn ChatGPT rồi mở lại từ menu ứng dụng.")

    def mode_page(self, mode, description):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=12)
        page.pack_start(Gtk.Label(label=description, xalign=0, wrap=True), False, False, 0)

        picker = Gtk.Button(label="Chọn cửa sổ")
        picker.set_image(Gtk.Image.new_from_icon_name("color-select-symbolic", Gtk.IconSize.BUTTON))
        picker.set_always_show_image(True)
        picker.set_halign(Gtk.Align.START)
        picker.connect("clicked", self.on_picker_clicked, mode)
        drag = Gtk.GestureDrag.new(picker)
        drag.connect("drag-update", self.on_drag_update, mode)
        drag.connect("drag-end", self.on_drag_end, mode)
        self.gestures.append(drag)
        page.pack_start(picker, False, False, 0)

        applications = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        placeholder = Gtk.Label(label="Chưa có ứng dụng", margin=18)
        placeholder.show()
        applications.set_placeholder(placeholder)
        scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        scroll.add(applications)
        page.pack_start(scroll, True, True, 0)
        self.lists[mode] = applications
        return page

    def render_list(self):
        for applications in self.lists.values():
            for child in applications.get_children():
                child.destroy()
        for application, mode in sorted(load_application_modes().items()):
            if mode not in self.lists:
                continue
            row = Gtk.Box(spacing=8, margin=8)
            row.pack_start(Gtk.Label(label=application, xalign=0), True, True, 0)
            remove = Gtk.Button(label="Bỏ khỏi danh sách")
            remove.connect("clicked", self.reset_application, application)
            row.pack_end(remove, False, False, 0)
            self.lists[mode].add(row)
        for applications in self.lists.values():
            applications.show_all()

    def on_picker_clicked(self, _button, mode):
        self.start_pick(mode)

    def on_drag_update(self, gesture, x, y, mode):
        if not self.picking and self.dragging is None and x * x + y * y >= 64:
            self.dragging = mode
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.status.set_text(f"{MODE_LABELS[mode]}: thả chuột lên cửa sổ cần chọn.")

    def on_drag_end(self, _gesture, _x, _y, mode):
        if self.dragging != mode:
            return
        self.dragging = None
        self.picking = True
        self.pending_mode = mode
        self.bus.call(
            SHELL_NAME, PICKER_PATH, PICKER_INTERFACE, "PickAtPointer", None,
            GLib.VariantType.new("(s)"), Gio.DBusCallFlags.NO_AUTO_START, 1_000,
            None, self.finish_drag,
        )

    def finish_drag(self, connection, result):
        self.picking = False
        try:
            (application,) = connection.call_finish(result).unpack()
        except GLib.Error:
            self.start_pick(self.pending_mode)
        else:
            self.select_application(application)

    def start_pick(self, mode):
        if self.picking or self.dragging:
            return
        self.picking = True
        self.pending_mode = mode
        self.status.set_text(f"{MODE_LABELS[mode]}: bấm vào cửa sổ cần chọn. Nhấn Esc để hủy.")
        for interface, path in ((PICKER_INTERFACE, PICKER_PATH), (FOCUS_INTERFACE, FOCUS_PATH)):
            self.focus_signals.append(self.bus.signal_subscribe(
                SHELL_NAME, interface, "FocusChanged", path, None,
                Gio.DBusSignalFlags.NONE, self.on_window_focused,
            ))
        self.focus_timeout = GLib.timeout_add_seconds(20, self.on_focus_timeout)

    def on_window_focused(self, _bus, _sender, _path, interface, _signal, parameters):
        if not self.focus_signals:
            return
        (application,) = parameters.unpack()
        if interface == FOCUS_INTERFACE:
            try:
                application = json.loads(application).get("wm_class") or ""
            except (ValueError, AttributeError):
                return
        if application and application.strip().casefold() not in SETTINGS_WINDOW_CLASSES:
            self.stop_focus_pick()
            self.select_application(application)

    def stop_focus_pick(self, *_args):
        if self.focus_timeout:
            GLib.source_remove(self.focus_timeout)
            self.focus_timeout = 0
        for subscription in self.focus_signals:
            self.bus.signal_unsubscribe(subscription)
        self.focus_signals.clear()
        self.picking = False

    def on_focus_timeout(self):
        self.focus_timeout = 0
        self.stop_focus_pick()
        self.status.set_text("Chưa chọn cửa sổ. Hãy bấm nút và thử lại.")
        return GLib.SOURCE_REMOVE

    def on_key_press(self, _window, event):
        if self.focus_signals and event.keyval == Gdk.KEY_Escape:
            self.stop_focus_pick()
            self.status.set_text("Đã hủy chọn cửa sổ.")
            return True
        return False

    def select_application(self, application):
        application = application.strip().casefold()
        if not application or application in SETTINGS_WINDOW_CLASSES:
            self.status.set_text("Chưa chọn ứng dụng. Hãy thử lại trên cửa sổ khác.")
            return
        self.change_application(application, self.pending_mode)

    def reset_application(self, _button, application):
        self.change_application(application, None)

    def change_application(self, application, mode):
        try:
            set_application_mode(application, mode)
        except OSError:
            self.status.set_text("Không lưu được chế độ gõ.")
        else:
            self.status.set_text(f"{application} • {MODE_LABELS[mode or MODE_PREEDIT]}")
        self.render_list()


class UVietSettings(Gtk.Application):
    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = SettingsWindow(self)
        window.present()


if __name__ == "__main__":
    GLib.set_prgname("uviet-settings")
    raise SystemExit(UVietSettings(application_id="org.uviet.Settings").run())
