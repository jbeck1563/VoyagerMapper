# Export MBTiles

The user picks layers, an area and a zoom range. voymap writes one `.mbtiles` in the CalTopo layout the Voyager Pro imports, with tracks and waypoints burned into the tiles. The user can also write a day + night pair.

## Sub-features

- `export-cli` runs `voymap export` with `--gpx`, `--bbox` or `--geojson` and writes the file.
- `export-cli-dry` uses `--dry-run` to print the area, the snap and the estimate, and writes nothing.
- `export-cli-themes` covers `--theme night|dim` and `--both-themes` (`<out>_day.mbtiles` and `<out>_night.mbtiles`).
- `export-gui` uses Export MBTiles…, the save dialog, the progress bars and the "Export complete" box.
- `export-gui-cancel` uses Cancel during an export.
- `export-burn-in` draws the track and waypoint pixels into the tiles.

## How to get to it (user POV)

- Run `voymap export --zooms A-B -o FILE [--gpx F | --bbox W S E N] [--layers ...]` in a terminal.
- In the GUI: set an export area, then choose `Export MBTiles…` in the "Export to Voyager Pro" dock.

## Driving it with vmctl

Preconditions:

- The root is seeded offline, and `$V doctor` exits 0.

- **CLI export.** Run `$V cli --tag export -- export --gpx $VOYMAP_VERIFY_ROOT/input/ride.gpx --zooms 10-13 -o cli-export.mbtiles --name "Verify CLI"`. Expect exit 0, a last progress line `[done ...] wrote 86 tiles ... err=0 miss=0`, and an inspection printed to stdout.
- **Layout check.** Run `$V check-mbtiles $VOYMAP_VERIFY_ROOT/evidence/cli-export.mbtiles`. All 5 lines must read `ok`.
- **Dry run.** Run `$V cli --tag dry -- export --gpx $VOYMAP_VERIFY_ROOT/input/ride.gpx --zooms 10-13 -o dry.mbtiles --dry-run`. stderr shows `area`, `snapped to z11 tile grid` and `~86 tiles`, and `evidence/dry.mbtiles` does not exist.
- **Day/night pair.** Run `$V cli --tag pair -- export --gpx $VOYMAP_VERIFY_ROOT/input/ride.gpx --zooms 10-12 -o pair.mbtiles --both-themes`. `pair_day.mbtiles` and `pair_night.mbtiles` appear. The night inspection shows `name ... (night)`.
- **GUI export.** Run `$V gui`. In `gui-report.json`, step `export` has dialog title `Export complete` and the text `gui-export.mbtiles: N tiles ... (fetch errors 0, empty 0)`. Then run `$V check-mbtiles .../gui-export.mbtiles`. All lines must read `ok`.

## Gotchas

- Offline mode only covers layer `usgs_topo` inside the seeded area at z8-14. Anything else tries the network and shows up as `err>0`.
- `--refresh` and the GUI's "ignore tile cache" option bypass the seeded cache.
- A cancelled export still leaves a valid-looking file (vm-01 report #5, fork PR #2). Do not take "file exists" as proof of a complete export.
- The 20,000-tile confirmation box (`Large export`) appears only for big areas. The seeded area never triggers it.
- `@1.5` style opacities in `--layers` are parsed as percentages (vm-01 report #10). Use `@0.9` or `@90`.
