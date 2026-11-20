import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const PATH = '/org/gnome/Shell/Extensions/UVietPicker';
const IFACE = `<node><interface name="org.gnome.Shell.Extensions.UVietPicker">
    <method name="PickAtPointer"><arg type="s" direction="out"/></method>
    <method name="GetFocused"><arg type="s" direction="out"/></method>
    <signal name="FocusChanged"><arg type="s"/></signal>
</interface></node>`;

export default class UVietPicker extends Extension {
    enable() {
        this._dbus = Gio.DBusExportedObject.wrapJSObject(IFACE, this);
        this._dbus.export(Gio.DBus.session, PATH);
        this._focusId = global.display.connect('notify::focus-window', () => {
            this._dbus.emit_signal('FocusChanged', new GLib.Variant('(s)', [this.GetFocused()]));
        });
    }

    disable() {
        global.display.disconnect(this._focusId);
        this._dbus.unexport();
        this._dbus = null;
    }

    GetFocused() {
        return global.display.focus_window?.get_wm_class() || '';
    }

    PickAtPointerAsync(_parameters, invocation) {
        let owner;
        try {
            [owner] = Gio.DBus.session.call_sync(
                'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                'GetNameOwner', new GLib.Variant('(s)', ['org.uviet.Settings']),
                new GLib.VariantType('(s)'), Gio.DBusCallFlags.NONE, 250, null).deepUnpack();
        } catch {
            owner = null;
        }
        if (owner !== invocation.get_sender()) {
            invocation.return_dbus_error('org.freedesktop.DBus.Error.AccessDenied',
                'The picker must be opened from UViet Settings');
            return;
        }

        const [x, y] = global.get_pointer();
        let actor = global.stage.get_actor_at_pos(Clutter.PickMode.ALL, x, y);
        while (actor && !(actor instanceof Meta.WindowActor))
            actor = actor.get_parent();

        invocation.return_value(new GLib.Variant('(s)', [actor?.meta_window.get_wm_class() || '']));
    }
}
