# Export area and estimate

The user sets the rectangle to export. The app snaps it outward to a zoom's tile grid, shows the snapped outline, and estimates tiles, MB and requests for the chosen zoom range.

## Sub-features

- `area-from-tracks` uses `Area = tracks extent`, which takes the visible features' bbox plus Extent padding (0.01°).
- `area-draw` uses `Draw export rectangle`, then a drag on the map.
- `area-clear` uses `Clear`, and the label returns to `No export area set.`
- `area-snap` uses the checkbox "snap area to tile grid at zoom" with a spin box (default 11). A dotted outline marks the snapped area.
- `estimate-gui` shows the `≈ N tiles, ≈ M MB, K layer(s)` label and a per-zoom table.
- `estimate-cli` runs `voymap estimate --bbox W S E N --zooms A-B [--snap-zoom Z | --no-snap]`.

## How to get to it (user POV)

- In the GUI: the area buttons and labels in the "Export to Voyager Pro" dock.
- In a terminal: `voymap estimate ...`.

## Driving it with vmctl

Preconditions:

- Features have been imported in the GUI.

- **Tracks extent.** Click `Area = tracks extent`. `win.export_area` is set, and the area label reads `W ... S ... E ... N ...`.
- **Zooms.** Type `10` into the min spin box and `13` into the max spin box. The estimate label and the table `z10:1   z11:2   z12:8   z13:32` update. Screenshot: `gui-05-area.png`.
- **CLI estimate.** Run `$V cli --tag estimate -- estimate --bbox -111.70 35.15 -111.60 35.25 --zooms 10-13`. Expect `snapped area: (...)`, per-zoom lines, and `total 86 tiles`.

## Gotchas

- The page can only make a rectangle. The polygon-clip path in the exporter is unreachable (vm-01 report #8).
- The GUI's MB estimate uses `AVG_TILE_BYTES` and the CLI uses 30 KB/tile. Real USGS tiles are about twice that.
- Spin box values apply on Tab or Enter. Typing alone does not apply them.
