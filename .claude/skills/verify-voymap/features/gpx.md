# GPX import and export

The user brings tracks, routes and waypoints in from GPX files to burn into the map. The GUI can also write them back out as GPX for the device's own GPX import.

## Sub-features

- `gpx-import-gui` uses File → Import GPX… (Ctrl+I). Features appear in the "Tracks & waypoints" list and on the map, and the map zooms to them.
- `gpx-import-cli` passes `voymap export --gpx F` (repeatable). With no `--bbox`, the area is the features' extent plus `--pad`.
- `gpx-export-gui` uses Export GPX for Voyager…, a save dialog, and writes waypoints first, then tracks.
- `gpx-names` shows names as map tooltips and list entries.

## How to get to it (user POV)

- In the GUI: File → `Import GPX…`, or `Export GPX for Voyager…` at the bottom of the Export dock.
- In a terminal: `voymap export --gpx ride.gpx ...`.

## Driving it with vmctl

Preconditions:

- The root is seeded. `input/ride.gpx` exists.

- **GUI import.** `$V gui`, step `import-gpx`: `feature_list` is `["● Camp", "— Loop"]`, `map_paths >= 2`, and `track_segments` is `[3, 3]`. `gui-02-imported.png` shows the red track and the `Camp` tooltip.
- **CLI import.** The CLI export recipe derives its area from the GPX. The `area (...)` line in `cli-export.txt` matches the GPX extent padded by 0.01°.
- **GUI GPX export.** Not in `$V gui` yet. Add a step: `with_dialogs(lambda: click(button("Export GPX for Voyager…")), [file_dialog(ev / "gui-out.gpx")], "save GPX")`. Then parse `gui-out.gpx` and require 1 `<wpt>` and 1 `<trk>`.

## Gotchas

- Feature names go into Leaflet tooltips as HTML (vm-01 report #6). A GPX name containing markup creates elements in the page. Use plain names in fixtures unless that is what you are testing.
- Importing the same file twice appends `_` to the duplicate ids. It does not replace the first import.
- GPX import goes through the native-style file dialog. Type the path into `fileNameEdit`, because `selectFile()` + `accept()` does not close it offscreen.
