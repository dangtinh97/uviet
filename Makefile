.PHONY: install uninstall deb

VERSION := $(shell sed -n 's/.*<version>\(.*\)<\/version>.*/\1/p' uviet.xml)
DEB := dist/uviet_$(VERSION)_all.deb

install:
	install -Dm644 uviet/engine.py "$(DESTDIR)/usr/lib/uviet/engine.py"
	install -Dm644 uviet/telex.py "$(DESTDIR)/usr/lib/uviet/telex.py"
	install -Dm644 uviet/applications.py "$(DESTDIR)/usr/lib/uviet/applications.py"
	install -Dm644 uviet/exclusions.py "$(DESTDIR)/usr/lib/uviet/exclusions.py"
	install -Dm755 uviet/settings.py "$(DESTDIR)/usr/lib/uviet/settings.py"
	printf '%s\n' "$(VERSION)" > "$(DESTDIR)/usr/lib/uviet/VERSION"
	install -Dm644 uviet.xml "$(DESTDIR)/usr/share/ibus/component/uviet.xml"
	install -Dm644 org.uviet.Settings.desktop "$(DESTDIR)/usr/share/applications/org.uviet.Settings.desktop"
	rm -f "$(DESTDIR)/usr/share/applications/uviet-settings.desktop"
	install -Dm644 app-picker@uviet.local/metadata.json "$(DESTDIR)/usr/share/gnome-shell/extensions/app-picker@uviet.local/metadata.json"
	install -Dm644 app-picker@uviet.local/extension.js "$(DESTDIR)/usr/share/gnome-shell/extensions/app-picker@uviet.local/extension.js"

uninstall:
	rm -f "$(DESTDIR)/usr/lib/uviet/engine.py" "$(DESTDIR)/usr/lib/uviet/telex.py"
	rm -f "$(DESTDIR)/usr/lib/uviet/applications.py"
	rm -f "$(DESTDIR)/usr/lib/uviet/exclusions.py" "$(DESTDIR)/usr/lib/uviet/settings.py"
	rm -f "$(DESTDIR)/usr/lib/uviet/VERSION"
	rm -f "$(DESTDIR)/usr/share/ibus/component/uviet.xml"
	rm -f "$(DESTDIR)/usr/share/applications/uviet-settings.desktop"
	rm -f "$(DESTDIR)/usr/share/applications/org.uviet.Settings.desktop"
	rm -f "$(DESTDIR)/usr/share/gnome-shell/extensions/app-picker@uviet.local/metadata.json"
	rm -f "$(DESTDIR)/usr/share/gnome-shell/extensions/app-picker@uviet.local/extension.js"

deb:
	@set -eu; \
	stage=$$(mktemp -d); \
	trap 'rm -rf -- "$$stage"' EXIT; \
	$(MAKE) install DESTDIR="$$stage"; \
	mkdir -p "$$stage/DEBIAN" dist; \
	sed 's/@VERSION@/$(VERSION)/g' packaging/control > "$$stage/DEBIAN/control"; \
	install -Dm644 README.md "$$stage/usr/share/doc/uviet/README.md"; \
	dpkg-deb --root-owner-group --build "$$stage" "$(DEB)"
