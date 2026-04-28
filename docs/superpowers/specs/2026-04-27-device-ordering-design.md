# Device Ordering Design

Date: 2026-04-27

## Scope

Add two related improvements to the device control console:

- Device cards should fill the first row according to available width instead of being locked to two columns.
- Operators should be able to drag a card to another position and have that order persist after refresh or restart.

The change applies to the PyQt desktop app. It does not change timer behavior, active-session recovery, checkout, statistics, or settings workflows except that settings-created devices receive a default order.

## Current Behavior

`DevicePanel` stores `self._columns = 2`, and `_apply_filters()` uses `divmod(idx, columns)`. This forces a maximum of two cards per row even when the device list area has room for more.

`database.db_manager.get_all_devices()` orders devices by type name and device name. There is no field for user-defined ordering, so drag/drop order cannot survive reloads.

## Design

### Adaptive Grid

The device panel computes the number of columns from the left-list viewport width:

- Use the existing comfortable card width plus horizontal spacing as the base.
- Clamp to at least one column.
- Re-layout cards when the panel resizes.

On the current 1920-wide window, this allows the first row to contain more than two cards when space is available.

### Persistent Ordering

Add `devices.sort_order INTEGER NOT NULL DEFAULT 0`.

Migration behavior:

- New databases create the column with the `devices` table.
- Existing databases add the column if missing.
- Existing devices are initialized to their current display order, so a migration does not randomly reshuffle the store.

Data access behavior:

- `get_all_devices()` orders by `sort_order`, then `id`.
- New devices receive `max(sort_order) + 1`.
- A new `update_device_sort_order(device_ids)` function writes contiguous order values based on the given list of IDs.

### Drag And Drop

`DeviceCard` becomes a drag source by storing its `device_id` in Qt mime data. `DevicePanel` becomes a drop target:

- Drag starts only after the mouse moves beyond Qt's drag threshold, so normal button clicks still work.
- Dropping a card on another card moves the dragged card before the target card.
- Dropping in empty grid space moves the dragged card to the end.
- After each drop, the panel updates the in-memory card order, re-lays out the grid, and saves the new order to the database.

## Error Handling

If a drag event contains an unknown device ID, the panel ignores it.

If saving order fails, the UI keeps the current in-memory order for this session and future refreshes will fall back to database order. The save function returns a boolean so callers can detect failure if needed.

## Verification

- Unit test migration and ordering API with an isolated temporary SQLite database.
- Unit test device cards expose the expected drag mime payload.
- Compile edited files.
- Launch the app and inspect that the first row fills available width and drag/drop works.

## Out Of Scope

- Drag handles or edit-mode toggles.
- Reordering from the settings dialog.
- Sorting by status after the user creates a manual order.
- Cross-window or multi-user ordering.
