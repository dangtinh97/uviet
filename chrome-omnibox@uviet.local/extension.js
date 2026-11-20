import Gio from 'gi://Gio';
import IBus from 'gi://IBus';

import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {shouldBypass} from './policy.js';

export default class ChromeOmniboxExtension extends Extension {
    enable() {
        this._injections = new InjectionManager();
        const bypassed = new WeakSet();

        this._injections.overrideMethod(IBus.InputContext.prototype,
            'process_key_event_async', original => function (...args) {
                const input = Main.inputMethod;
                if (this !== input?._context || !input.currentFocus ||
                    !shouldBypass(input._currentSource, input._purpose,
                        IBus.InputPurpose.URL, global.display.focus_window))
                    return original.apply(this, args);

                // GNOME Shell handles an unconsumed key as normal input.
                const [, , , , cancellable, callback] = args;
                if (!callback)
                    return Promise.resolve(false);

                const task = Gio.Task.new(this, cancellable, (_context, result) => callback(this, result));
                bypassed.add(task);
                task.return_boolean(false);
            });

        this._injections.overrideMethod(IBus.InputContext.prototype,
            'process_key_event_async_finish', original => function (result) {
                if (bypassed.has(result))
                    return result.propagate_boolean();
                return original.call(this, result);
            });
    }

    disable() {
        this._injections.clear();
        this._injections = null;
    }
}
