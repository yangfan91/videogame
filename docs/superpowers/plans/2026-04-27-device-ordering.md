# Device Ordering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the device grid use available width and persist operator-controlled card order through drag and drop.

**Architecture:** Add a persisted `devices.sort_order` column and database API for saving order. Make `DeviceCard` a Qt drag source and `DevicePanel` a drop target that updates its ordered card list, recalculates adaptive columns, and saves the new order.

**Tech Stack:** Python 3.13, PyQt6, SQLite, existing `database.db_manager`, `ui.device_card`, and `ui.device_panel`.

---

## File Structure

- Modify `database/db_manager.py`: schema migration, order-aware queries, default order for new devices, order update API.
- Modify `ui/device_card.py`: drag source support with a stable mime payload.
- Modify `ui/device_panel.py`: adaptive column calculation, drag/drop target logic, order persistence.
- Add/modify tests under `tests/`: database ordering and device-card drag payload tests.

## Task 1: Database Ordering

**Files:**
- Modify: `database/db_manager.py`
- Test: `tests/test_device_ordering.py`

- [ ] **Step 1: Write failing database tests**

Create isolated SQLite tests that monkeypatch `database.db_manager.DB_PATH`, create an old-schema database, run `migrate_db()`, verify `sort_order` exists, verify `get_all_devices()` orders by it, verify `update_device_sort_order([ids])` persists a new order, and verify `add_device()` assigns the next order.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
python -m unittest tests/test_device_ordering.py -v
```

Expected before implementation: failure because `sort_order` and `update_device_sort_order` do not exist.

- [ ] **Step 3: Implement database changes**

Update `devices` table creation, `migrate_db()`, `get_all_devices()`, `add_device()`, and add `update_device_sort_order(device_ids: list[int]) -> bool`.

- [ ] **Step 4: Run tests and confirm pass**

Run:

```powershell
python -m unittest tests/test_device_ordering.py -v
```

Expected: all tests pass.

## Task 2: Drag Source

**Files:**
- Modify: `ui/device_card.py`
- Test: `tests/test_ui_layout.py`

- [ ] **Step 1: Write failing drag payload test**

Add a test asserting `DeviceCard._drag_mime_data().data("application/x-videogame-device-id")` contains the card's device ID.

- [ ] **Step 2: Run test and confirm failure**

Run:

```powershell
python -m unittest tests/test_ui_layout.py -v
```

Expected before implementation: failure because `_drag_mime_data` does not exist.

- [ ] **Step 3: Implement drag source**

Add Qt mouse tracking fields, `_drag_mime_data()`, `mousePressEvent()`, and `mouseMoveEvent()` to `DeviceCard`. Start a `QDrag` only after movement exceeds `QApplication.startDragDistance()`.

- [ ] **Step 4: Run UI tests**

Run:

```powershell
python -m unittest tests/test_ui_layout.py -v
```

Expected: all UI layout tests pass.

## Task 3: Adaptive Grid And Drop Target

**Files:**
- Modify: `ui/device_panel.py`

- [ ] **Step 1: Replace fixed column behavior**

Add `_card_width`, `_grid_spacing`, `_ordered_device_ids`, and `_calculate_columns()`. Recalculate columns from the scroll viewport width and re-layout cards on resize.

- [ ] **Step 2: Add drop target behavior**

Enable drops on the grid widget and device cards. Implement `dragEnterEvent`, `dragMoveEvent`, and `dropEvent` on `DevicePanel` so the dragged device can move before the target card or to the end.

- [ ] **Step 3: Save order after drop**

After reordering `_ordered_device_ids`, call `db.update_device_sort_order(self._ordered_device_ids)` and refresh the grid without reloading sessions.

- [ ] **Step 4: Compile edited files**

Run:

```powershell
python -m py_compile ui\device_panel.py ui\device_card.py database\db_manager.py
```

Expected: no output and exit code 0.

## Task 4: Full Verification

**Files:**
- Verify: `main.py`, edited UI and database files

- [ ] **Step 1: Run all focused tests**

Run:

```powershell
python -m unittest tests/test_ui_layout.py tests/test_device_ordering.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Run compile check**

Run:

```powershell
python -m py_compile main.py database\db_manager.py ui\main_window.py ui\device_panel.py ui\device_card.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Launch app**

Run:

```powershell
python main.py
```

Expected: the desktop app opens.

- [ ] **Step 4: Manual UI verification**

At the wide desktop size:

- First row contains as many device cards as fit, not a hard-coded two.
- Dragging `小包2` before or after another card changes its position.
- Refreshing status keeps the dragged order.
- Restarting the app keeps the dragged order.

## Self-Review

- Spec coverage: adaptive columns, persisted order, migration, drag/drop, and verification are covered.
- Placeholder scan: no TBD/TODO/fill-in placeholders.
- Type consistency: planned function and method names are consistent with the existing files.
