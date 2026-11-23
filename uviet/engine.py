"""Ubuntu IBus adapter for UViet."""

import string
import sys
from pathlib import Path

import gi

gi.require_version("IBus", "1.0")
from gi.repository import Gio, GLib, IBus

from applications import ApplicationRules
from exclusions import MODE_DIRECT, MODE_OFF
from telex import Telex

BUS_NAME = "org.freedesktop.IBus.UViet"
PANEL_ENGINE = "uviet-panel"
APP_EXCLUSION = "exclude-current-app"
OPEN_SETTINGS = "open-uviet-settings"

MODIFIER_KEYS = {
    IBus.KEY_Shift_L, IBus.KEY_Shift_R, IBus.KEY_Control_L, IBus.KEY_Control_R,
    IBus.KEY_Alt_L, IBus.KEY_Alt_R, IBus.KEY_Super_L, IBus.KEY_Super_R,
    IBus.KEY_Meta_L, IBus.KEY_Meta_R, IBus.KEY_Caps_Lock, IBus.KEY_Num_Lock,
    IBus.KEY_ISO_Level3_Shift,
}
SHORTCUT_MASK = (
    IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK
    | IBus.ModifierType.MOD4_MASK | IBus.ModifierType.SUPER_MASK
    | IBus.ModifierType.HYPER_MASK | IBus.ModifierType.META_MASK
)
DIRECT_PURPOSES = {
    IBus.InputPurpose.PASSWORD, IBus.InputPurpose.PIN,
    IBus.InputPurpose.EMAIL,
}


class UVietEngine(IBus.Engine):
    def __init__(self, engine_name, app_rules, **kwargs):
        super().__init__(engine_name=engine_name, **kwargs)
        self.app_rules = app_rules
        self.application = ""
        self.word = Telex()
        self.panel_preview = engine_name == PANEL_ENGINE
        self.direct_input = False
        self.url_field = False
        self.plain_field = True
        self.has_surrounding = False
        self.plain_live_supported = False
        self.live_visible_word = ""

    def app_property(self):
        application = self.application
        label = f"Tắt Telex trong {application}" if application else "Tắt Telex trong ứng dụng"
        state = IBus.PropState.CHECKED if self.app_rules.mode_for(application) == MODE_OFF else IBus.PropState.UNCHECKED
        return IBus.Property.new(
            APP_EXCLUSION, IBus.PropType.TOGGLE, IBus.Text.new_from_string(label),
            None, IBus.Text.new_from_string("Ghi nhớ theo ứng dụng"), bool(application), True,
            state, None,
        )

    def sync_application(self):
        application = self.app_rules.current
        if application and application != self.application:
            self.do_reset()
            if self.application:
                self.plain_live_supported = False
            self.application = application
            self.update_property(self.app_property())
        return application

    def do_focus_in(self):
        self.application = self.app_rules.current
        self.get_surrounding_text()
        properties = IBus.PropList.new()
        properties.append(self.app_property())
        properties.append(IBus.Property.new(
            OPEN_SETTINGS, IBus.PropType.NORMAL, IBus.Text.new_from_string("Mở Cài đặt UViet…"),
            "preferences-desktop-keyboard", IBus.Text.new_from_string("Quản lý ứng dụng loại trừ"),
            True, True, IBus.PropState.UNCHECKED, None,
        ))
        self.register_properties(properties)

    def do_property_activate(self, prop_name, prop_state):
        if prop_name == OPEN_SETTINGS:
            try:
                Gio.Subprocess.new(
                    [sys.executable, str(Path(__file__).with_name("settings.py"))],
                    Gio.SubprocessFlags.NONE,
                )
            except GLib.Error:
                print("UViet: không mở được cửa sổ cài đặt.", flush=True)
            return
        if prop_name != APP_EXCLUSION or not self.application:
            return
        if self.app_rules.current and self.app_rules.current != self.application:
            self.sync_application()
            return
        exclude = prop_state == IBus.PropState.CHECKED
        try:
            self.app_rules.set_mode(self.application, MODE_OFF if exclude else None)
        except OSError:
            print("UViet: không lưu được danh sách ứng dụng.", flush=True)
        else:
            if exclude and self.live_visible_word:
                self.do_reset()
            elif exclude:
                self.commit_word()
        self.update_property(self.app_property())

    def update_word(self):
        word = self.word.text
        text = IBus.Text.new_from_string(word)
        if self.panel_preview:
            self.update_auxiliary_text(text, bool(word))
            return
        if word:
            text.append_attribute(IBus.AttrType.UNDERLINE, IBus.AttrUnderline.NONE, 0, len(word))
        self.update_preedit_text_with_mode(text, len(word), bool(word), IBus.PreeditFocusMode.COMMIT)

    def commit_word(self, suffix=""):
        word = self.word.text
        if word:
            self.do_reset()
            self.commit_text(IBus.Text.new_from_string(word + suffix))

    def process_live_key(self, keyval, state):
        character = IBus.keyval_to_unicode(keyval)
        if not state & SHORTCUT_MASK:
            if character and character in string.ascii_letters:
                self.word.push(character)
                literal = self.live_visible_word + character
                corrected = self.word.text
                if corrected != literal and self.replace_live_word(corrected):
                    self.live_visible_word = corrected
                    return True
                self.live_visible_word = literal
                return False
            if character == " " and self.word.text != self.live_visible_word:
                replaced = self.replace_live_word(self.word.text + character)
                self.do_reset()
                return replaced

        # Pass Enter and other navigation keys to the application.
        self.word.clear()
        self.live_visible_word = ""
        return False

    def replace_live_word(self, after, snapshot=None):
        before = self.live_visible_word
        if not before or not self.has_surrounding:
            return False
        text, cursor, anchor = self.get_surrounding_text() if snapshot is None else snapshot
        if text is None or cursor != anchor:
            return False
        surrounding = text.get_text()
        start = cursor - len(before)
        if not 0 <= start < cursor <= len(surrounding) or surrounding[start:cursor] != before:
            return False

        common = 0
        for previous, replacement in zip(before, after):
            if previous != replacement:
                break
            common += 1
        if common < len(before):
            self.delete_surrounding_text(common - len(before), len(before) - common)
        if common < len(after):
            self.commit_text(IBus.Text.new_from_string(after[common:]))
        return True

    def do_process_key_event(self, keyval, keycode, state):
        application = self.sync_application()
        mode = self.app_rules.mode_for(application)
        if mode == MODE_OFF:
            if self.word.letters:
                self.do_reset()
            return False
        if self.direct_input or state & IBus.ModifierType.RELEASE_MASK or keyval in MODIFIER_KEYS:
            return False
        if self.live_visible_word or (
            mode == MODE_DIRECT and not self.word.letters
            and (self.url_field or (
                self.plain_field and self.plain_live_supported and not self.panel_preview
            ))
        ):
            return self.process_live_key(keyval, state)
        if not state & SHORTCUT_MASK:
            if keyval == IBus.KEY_BackSpace and self.word.letters:
                self.word.backspace()
                self.update_word()
                return True
            if keyval == IBus.KEY_Escape and self.word.letters:
                self.do_reset()
                return True
            character = IBus.keyval_to_unicode(keyval)
            if character and character in string.ascii_letters:
                self.word.push(character)
                self.update_word()
                return True
            if self.panel_preview and self.word.letters and (
                character == " " or (character and character in string.punctuation)
            ):
                self.commit_word(character)
                return True

        self.commit_word()
        return False

    def do_set_content_type(self, purpose, hints):
        direct_input = purpose in DIRECT_PURPOSES or bool(hints & IBus.InputHints.HIDDEN_TEXT)
        url_field = purpose == IBus.InputPurpose.URL
        plain_field = purpose == IBus.InputPurpose.FREE_FORM
        if (direct_input or url_field != self.url_field or plain_field != self.plain_field) and self.word.letters:
            self.do_reset()
        if plain_field != self.plain_field or direct_input:
            self.plain_live_supported = False
        self.url_field = url_field
        self.plain_field = plain_field
        self.direct_input = direct_input

    def do_set_capabilities(self, capabilities):
        self.has_surrounding = bool(capabilities & IBus.Capabilite.SURROUNDING_TEXT)

    def do_set_surrounding_text(self, text, cursor, anchor):
        IBus.Engine.do_set_surrounding_text(self, text, cursor, anchor)
        mode = self.app_rules.mode_for(self.sync_application())
        excluded = mode == MODE_OFF
        if self.plain_field and self.has_surrounding and not self.direct_input and not excluded:
            self.plain_live_supported = True
        if self.live_visible_word and not self.direct_input and mode == MODE_DIRECT:
            corrected = self.word.text
            if corrected != self.live_visible_word and self.replace_live_word(
                    corrected, (text, cursor, anchor)):
                self.live_visible_word = corrected

    def do_enable(self):
        self.get_surrounding_text()

    def do_reset(self):
        had_preedit = bool(self.word.letters) and not self.live_visible_word
        self.word.clear()
        self.live_visible_word = ""
        if had_preedit:
            self.update_word()

    def do_focus_out(self):
        if self.panel_preview or self.live_visible_word:
            # An auxiliary preview cannot be committed by IBus on focus loss.
            self.do_reset()
        else:
            # IBus commits the visible preedit to the old input context.
            self.word.clear()
        self.plain_live_supported = False

    def do_disable(self):
        self.do_reset()


class UVietFactory(IBus.Factory):
    def __init__(self, connection):
        super().__init__(connection=connection, object_path=IBus.PATH_FACTORY)
        self.connection = connection
        self.engine_id = 0
        self.app_rules = ApplicationRules()

    def do_create_engine(self, engine_name):
        self.engine_id += 1
        return UVietEngine(
            connection=self.connection,
            object_path=f"/org/freedesktop/IBus/UViet/Engine/{self.engine_id}",
            engine_name=engine_name,
            app_rules=self.app_rules,
        )


def main():
    IBus.init()
    bus = IBus.Bus.new()
    if not bus.is_connected():
        raise SystemExit("UViet: không kết nối được với IBus.")
    bus.connect("disconnected", lambda *_: IBus.quit())
    factory = UVietFactory(bus.get_connection())
    if not bus.request_name(BUS_NAME, 0):
        raise SystemExit("UViet: không đăng ký được dịch vụ IBus.")
    IBus.main()


if __name__ == "__main__":
    main()
