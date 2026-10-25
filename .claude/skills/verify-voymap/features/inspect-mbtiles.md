# Inspect MBTiles

The user checks an exported file before copying it to the device. The inspection shows the schema, the metadata, a sample tile's format, and per-zoom tile counts with row and column ranges.

## Sub-features

- `inspect-cli` runs `voymap inspect FILE` and prints the inspection.
- `inspect-gui` uses File → Inspect MBTiles…, a file dialog, then a message box with the same text.
- `inspect-layout` is the device contract: 7 metadata keys in order, `idx_x/idx_y/idx_z`, 256×256 palette PNG, TMS rows.

## How to get to it (user POV)

- Run `voymap inspect ride.mbtiles` in a terminal.
- In the GUI: File menu → `Inspect MBTiles…`.

## Driving it with vmctl

Preconditions:

- An export exists in `evidence/` (see export-mbtiles.md).

- **CLI.** Run `$V cli --tag inspect -- inspect cli-export.mbtiles`. Expect exit 0, `schema: index:idx_x, index:idx_y, index:idx_z, table:metadata, table:tiles`, `tile sample  PNG 256x256 mode=P`, and z10-z13 rows.
- **GUI.** `$V gui` ends with File → Inspect MBTiles… on `gui-export.mbtiles`. `evidence/gui-inspect.txt` holds the box text, and the check `GUI inspection lists the tiles table` passes.
- **Layout assertions.** Run `$V check-mbtiles <file>`. Expect exit 0.

## Gotchas

- `inspect` reads any SQLite file, so a truncated export from a cancel still inspects cleanly (fork PR #2).
- The `created` value is milliseconds since the epoch, as CalTopo writes it, not seconds.
