#!/usr/bin/python3
"""GNOME settings window for UViet."""

import gi
import json
from pathlib import Path
from xml.etree import ElementTree

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from applications import FOCUS_INTERFACE, FOCUS_PATH, PICKER_INTERFACE, PICKER_PATH, SHELL_NAME
from exclusions import load_excluded, set_application_excluded

SETTINGS_WINDOW_CLASSES = {"uviet-settings", "org.uviet.settings"}


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
        self.dragging = False
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
        title = Gtk.Label(label="Ứng dụng tắt Telex", xalign=0)
        title.get_style_context().add_class("title")
        content.pack_start(title, False, False, 0)

        self.picker = Gtk.Button()
        picker_content = Gtk.Box(spacing=8, margin=6)
        picker_content.pack_start(Gtk.Image.new_from_icon_name(
            "color-select-symbolic", Gtk.IconSize.BUTTON), False, False, 0)
        picker_content.pack_start(Gtk.Label(label="Kéo để chọn cửa sổ"), False, False, 0)
        self.picker.add(picker_content)
        self.picker.set_halign(Gtk.Align.START)
        self.picker.connect("clicked", self.start_pick)
        self.drag = Gtk.GestureDrag.new(self.picker)
        self.drag.connect("drag-update", self.on_drag_update)
        self.drag.connect("drag-end", self.on_drag_end)
        content.pack_start(self.picker, False, False, 0)

        self.status = Gtk.Label(xalign=0, wrap=True)
        content.pack_start(self.status, False, False, 0)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        placeholder = Gtk.Label(label="Chưa có ứng dụng nào được loại trừ", margin=18)
        placeholder.show()
        self.list.set_placeholder(placeholder)
        scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        scroll.add(self.list)
        content.pack_start(scroll, True, True, 0)

        self.render_list()
        self.status.set_text("Kéo biểu tượng lên cửa sổ cần chọn hoặc bấm rồi chọn cửa sổ.")
        self.show_all()

    def render_list(self):
        for child in self.list.get_children():
            child.destroy()
        for application in sorted(load_excluded()):
            row = Gtk.Box(spacing=12, margin=8)
            row.pack_start(Gtk.Label(label=application, xalign=0), True, True, 0)
            remove = Gtk.Button(label="Bật lại Telex")
            remove.connect("clicked", self.enable_application, application)
            row.pack_end(remove, False, False, 0)
            self.list.add(row)
        self.list.show_all()

    def on_drag_update(self, gesture, x, y):
        if not self.picking and not self.dragging and x * x + y * y >= 64:
            self.dragging = True
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.status.set_text("Thả chuột lên cửa sổ cần chọn.")

    def on_drag_end(self, _gesture, _x, _y):
        if not self.dragging:
            return
        self.dragging = False
        self.picking = True
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
            self.start_pick()
        else:
            self.select_application(application)

    def start_pick(self, *_args):
        if self.picking or self.dragging:
            return
        self.picking = True
        self.status.set_text("Bấm vào cửa sổ cần chọn. Nhấn Esc để hủy.")
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
        self.change_application(application, True)

    def enable_application(self, _button, application):
        self.change_application(application, False)

    def change_application(self, application, exclude):
        try:
            set_application_excluded(application, exclude)
        except OSError:
            self.status.set_text("Không lưu được danh sách ứng dụng.")
            return
        action = "Đã tắt" if exclude else "Đã bật"
        self.status.set_text(f"{action} Telex cho {application}.")
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
