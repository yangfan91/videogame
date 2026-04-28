# Embedded Settings Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show system settings as the third main page instead of opening a modal dialog.

**Architecture:** Extract the existing settings UI and behavior into `SettingsPanel(QWidget)`, keep `SettingsDialog` as a thin compatibility wrapper, and add `SettingsPanel` to `MainWindow`'s `QStackedWidget` at index `2`.

**Tech Stack:** Python 3.13, PyQt6, existing `ui.main_window`, `ui.settings_dialog`, and database APIs.

---

## File Structure

- Modify `ui/settings_dialog.py`: introduce `SettingsPanel`, move existing settings UI and behavior into it, keep a wrapper dialog.
- Modify `ui/main_window.py`: instantiate `SettingsPanel`, add it to the page stack, route `设` to `_switch_page(2)`.
- Add `tests/test_main_window_navigation.py`: focused navigation test.

## Task 1: Navigation Test

**Files:**
- Add: `tests/test_main_window_navigation.py`

- [ ] **Step 1: Write failing test**

Create a PyQt offscreen test that constructs `MainWindow`, asserts `_stack.count() == 3`, calls `_switch_page(2)`, and asserts the current widget is `_settings_panel`.

- [ ] **Step 2: Run and confirm failure**

Run:

```powershell
python -m unittest tests/test_main_window_navigation.py -v
```

Expected before implementation: failure because the main window has only two stacked pages and no `_settings_panel`.

## Task 2: Extract SettingsPanel

**Files:**
- Modify: `ui/settings_dialog.py`

- [ ] **Step 1: Add SettingsPanel**

Convert the current dialog body into `class SettingsPanel(QWidget)` with the same `settings_changed` signal and add a public `refresh()` method that calls `_load_data()`.

- [ ] **Step 2: Add embedded header and remove close button in panel**

For embedded mode, include the full-page title/subtitle and no close button.

- [ ] **Step 3: Keep SettingsDialog wrapper**

Keep `class SettingsDialog(QDialog)` as a small wrapper that hosts `SettingsPanel(show_header=False)` and a close button.

- [ ] **Step 4: Compile settings file**

Run:

```powershell
python -m py_compile ui\settings_dialog.py
```

Expected: no output and exit code 0.

## Task 3: Wire MainWindow

**Files:**
- Modify: `ui/main_window.py`

- [ ] **Step 1: Use SettingsPanel**

Import `SettingsPanel`, create `self._settings_panel`, connect `settings_changed`, and add it to `_stack`.

- [ ] **Step 2: Route sidebar settings button to stack page**

Connect `self._nav_settings_btn.clicked` to `lambda: self._switch_page(2)` and remove modal settings navigation.

- [ ] **Step 3: Update active nav state**

Make `_switch_page()` set the active state for device, stats, and settings based on indexes `0`, `1`, and `2`. Refresh the settings page when selected.

- [ ] **Step 4: Run navigation test**

Run:

```powershell
python -m unittest tests/test_main_window_navigation.py -v
```

Expected: test passes.

## Task 4: Full Verification

**Files:**
- Verify edited Python files and focused tests.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m unittest tests/test_main_window_navigation.py tests/test_ui_layout.py tests/test_device_ordering.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Compile edited files**

Run:

```powershell
python -m py_compile main.py ui\main_window.py ui\settings_dialog.py ui\device_panel.py ui\device_card.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Launch app**

Run:

```powershell
python main.py
```

Expected: clicking `设` switches to the embedded settings page and no modal appears.

## Self-Review

- Spec coverage: embedded page, compatibility wrapper, navigation routing, refresh behavior, and verification are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders.
- Type consistency: planned class and method names match the existing files.
