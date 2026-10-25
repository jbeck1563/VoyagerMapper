# Track editing

On the map, the user draws tracks point by point, adds waypoints and areas, and extends an existing track from its last point. Cancel (Esc) must leave the original track untouched.

## Sub-features

- `track-draw` starts with `Draw track` or the ✎ map control. Left-click adds a point, right-click or Space pauses, Enter or a double right-click finishes, Esc cancels.
- `track-extend` selects a track, then uses `Extend track`. The track bar shows `Drawing N pts`, and new clicks append points.
- `track-extend-cancel` presses Esc during an extend and must restore the original track.
- `waypoint-add` uses `Add waypoint` and a click, which creates `WPT n`.
- `feature-style` edits the Selected feature box: name, color, width, label, include in export, min zoom.
- `feature-delete` uses the `Delete` button.

## How to get to it (user POV)

- Use the buttons in the "Tracks & waypoints" dock, the map toolbar on the left, and the keyboard while the map has focus.

## Driving it with vmctl

Preconditions:

- A GPX with a two-segment track has been imported (the `import-gpx` step of `$V gui`).

- **Select.** Click `— Loop` in the feature list. The Selected feature box becomes enabled.
- **Extend.** Click `Extend track`. The `#trackbar` display becomes `block`, and `#trackinfo` reads `Drawing 3 pts` (the last segment's points).
- **Add a point.** Click the map widget 40 px right and below the centre. `#trackinfo` changes to `Drawing 4 pts`. Screenshot: `gui-03-extending.png`.
- **Cancel.** Send `Esc` to `view.focusProxy()`. `#trackbar` hides and the list still shows `— Loop`. The `track_segments` value in `gui-report.json` should equal its value before the extend.
- **Current result.** `[3, 3] -> [3]`. The check `cancel restores original track` reports `known-bug` (vm-01 report #3, fork PR #3). After that fix merges, it must report `pass`.

## Gotchas

- Map keys reach the page only when the web view has focus. Clicking the map gives it focus, but during a draw or extend that click also adds a point.
- A click on the map during a draw adds a point. Use the trackbar `Cancel` button, or Esc, to leave without adding points.
- Double-click zoom is disabled while drawing. Two quick left-clicks add two points.
- The extend bug also shrinks the track used by "Area = tracks extent" and the export.
