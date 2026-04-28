# Embedded Settings Page Design

Date: 2026-04-27

## Scope

Move system settings from a modal dialog into the main application page stack.

The left navigation keeps the existing `控 / 统 / 设` entries. Clicking `设` switches the main content area to settings instead of opening a separate dialog window.

## Current Behavior

`MainWindow._open_settings()` creates `SettingsDialog`, connects `settings_changed`, and calls `dialog.exec()`. This blocks the main window and overlays a modal on top of the device dashboard.

`SettingsDialog` contains all setting UI and behavior directly inside a `QDialog`.

## Design

Create a reusable `SettingsPanel(QWidget)` in `ui/settings_dialog.py`.

`SettingsPanel` owns:

- Header title and subtitle for the embedded page.
- Existing two tabs: device type management and device management.
- Existing add/delete workflows.
- Existing `settings_changed` signal.

Keep a small `SettingsDialog(QDialog)` wrapper for compatibility, but stop using it from `MainWindow`.

Update `MainWindow`:

- Import `SettingsPanel` instead of using the dialog as the primary settings UI.
- Add `self._settings_panel` to `self._stack` as page index `2`.
- Connect the sidebar `设` button to `_switch_page(2)`.
- Update nav active-state logic for all three pages.
- When entering settings, call `self._settings_panel.refresh()` so tables and type combos are current.
- Keep `_on_settings_changed()` refreshing device and stats panels.

## Visual Behavior

The settings page should match the existing full-page dashboard rhythm:

- Root margins around `34 x 30`.
- Title `系统设置`.
- Subtitle `管理包厢类型和包厢列表，变更会自动同步到控制台。`
- Main white panel containing the existing tabs and tables.
- No bottom `关闭` button in embedded mode.

## Verification

- Unit test that `MainWindow` has three stacked pages and switching to page `2` activates the settings page.
- Unit test that `MainWindow._open_settings` is no longer part of normal navigation.
- Compile edited files.
- Launch app and verify clicking `设` displays settings in the main content area without opening a dialog.

## Out Of Scope

- Redesigning the settings tables.
- Editing or renaming existing settings workflows.
- Changing database schema.
- Removing the `SettingsDialog` compatibility wrapper.
