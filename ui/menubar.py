from pathlib import Path

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)


ICON = Path(__file__).resolve().parent.parent / "assets" / "AppIcon.icns"


class MenuBarItem:
    """Dock icon, Cmd+Q menu and menu-bar icon, so the app can always be quit
    when it was started without a terminal."""

    def __init__(self, hint: str):
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)  # visible in Dock / Force Quit
        if ICON.exists():
            app.setApplicationIconImage_(NSImage.alloc().initWithContentsOfFile_(str(ICON)))

        # minimal main menu: gives Cmd+Q and a Quit entry when the app is focused
        main_menu = NSMenu.alloc().init()
        app_item = NSMenuItem.alloc().init()
        main_menu.addItem_(app_item)
        app_menu = NSMenu.alloc().init()
        app_menu.addItemWithTitle_action_keyEquivalent_("Quit Voice Typer", "terminate:", "q")
        app_item.setSubmenu_(app_menu)
        app.setMainMenu_(main_menu)
        self.main_menu = main_menu

        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("mic.fill", "Voice Typer")
        if icon is not None:
            icon.setTemplate_(True)
            self.item.button().setImage_(icon)
        else:
            self.item.button().setTitle_("VT")

        self.menu = NSMenu.alloc().init()
        info = self.menu.addItemWithTitle_action_keyEquivalent_(hint, None, "")
        info.setEnabled_(False)
        self.menu.addItem_(NSMenuItem.separatorItem())
        quit_item = self.menu.addItemWithTitle_action_keyEquivalent_("Quit Voice Typer", "terminate:", "q")
        quit_item.setTarget_(app)
        self.item.setMenu_(self.menu)
