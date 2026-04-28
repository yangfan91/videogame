# UI Polish Design

Date: 2026-04-27

## Scope

Apply the selected A direction: keep the current PyQt desktop control-console structure and improve the visual hierarchy, spacing, and text layout. The work focuses on the main device control screen and its repeated device cards.

This change does not alter timer behavior, session persistence, billing, database schema, or device-management workflows.

## Current Problems

- Device cards use a fixed height that is too small for the timer panel, hint text, and two-row action area.
- The timer label dynamically changes height, which can push the hint text and buttons into each other.
- Button rows do not reserve enough vertical space, so the lower row can be clipped by the scroll viewport.
- Panel styling is mostly square and low-contrast, making the interface feel rigid.
- The right-side summary panels and top metrics use similar weight, so scanning priority is unclear.

## Design Direction

Keep the existing layout:

- Left navigation
- Header and action buttons
- Four status summary cards
- Device grid with card-based devices
- Right-side duty summary, pending events, and legend

Refine the interface with:

- Slightly softer card corners, consistent borders, and restrained shadows through color contrast rather than heavy decoration.
- More predictable vertical rhythm in the device cards.
- A fixed timer panel height so timer digits, runtime hint, and action buttons cannot overlap.
- Larger device card height to fit active, paused, expired, idle, and countdown states.
- Compact but readable status badges and metadata pills.
- More readable side panels with clearer title/body spacing.

## Component Changes

### DeviceCard

- Increase comfortable card size from `278 x 272` to a larger fixed size that can safely hold all active-state controls.
- Give the internal card frame a rounded 8 px border and clear white surface.
- Give the timer panel a fixed minimum height and a centered vertical layout.
- Keep timer digits in a monospace font, but cap the dynamic sizing to fit the available width without changing layout height.
- Add button border radius and fixed heights so rows remain visually stable.
- Ensure long device names and status badges do not crowd each other by using explicit spacing and reserved label heights.

### DevicePanel

- Keep two-column grid behavior for current desktop width.
- Add bottom padding inside the scroll content so the last card is not clipped at the bottom.
- Make summary cards and side panels visually consistent with the updated card style.
- Keep right column width stable so the device grid has predictable space.

### MainWindow

- Keep the sidebar structure and page switching.
- Make sidebar button styling visually consistent with the softened control surface without changing navigation behavior.

## Verification

- Run Python compile checks for edited files.
- Start the app from `python main.py`.
- Visually inspect the main device control screen at the existing 1360 x 860 window size.
- Confirm timer text, runtime hint text, and action buttons do not overlap in active sessions.
- Confirm the last visible card is not cut off by the scroll area.

## Out Of Scope

- Reworking the app into a list/table layout.
- Applying a dark theme.
- Rewriting dialogs, settings, statistics, billing, or database code.
- Changing Chinese copy or business terminology except where spacing requires shorter button labels.
