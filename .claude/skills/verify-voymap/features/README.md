# voymap verification map

This directory is the maintained source for verifying the user-facing behavior of voymap. Read this index before you drive the app, then follow the matching feature file as the recipe. The harness is `vmctl` (`.claude/skills/verify-voymap/scripts/vmctl.py`). See `../SKILL.md` for launch, doctor, evidence and cleanup.

## Baseline preconditions

- Install the repo venv with the `gui` and `dev` extras.
- Set `VOYMAP_VERIFY_ROOT` to a new directory for this run.
- Set `V=".venv/bin/python .claude/skills/verify-voymap/scripts/vmctl.py"`.
- Run `$V seed` (offline) and require `$V doctor` to exit 0.
- `input/ride.gpx` holds a track `Loop` with two segments of 3 points each, and a waypoint `Camp`.
- The cache holds `usgs_topo` tiles for z8-14 around those features.
- Never drive a GUI that this root did not start. Never point a run at the real `~/.config/voymap` or `~/.cache/voymap`.

## Driving conventions

- Run CLI actions through `$V cli --tag <name> -- <voymap args>`. The working directory is `<root>/evidence`.
- Run GUI actions through `$V gui`. It runs the import, extend/cancel, area, export and inspect path in one call.
- For a GUI step that `$V gui` does not cover, extend `gui_inner()` with the same helpers: `button(text)`, `menu_action(text)`, `click()`, `with_dialogs()`, `pump()`.
- Find widgets by visible text: button labels, File-menu entries and dialog titles. Read page state from the DOM ids `#status`, `#trackbar`, `#trackinfo` and `#err`.
- Never call `window.vm.*` or `MainWindow._*` methods to perform an action. Those calls skip the user path.

## Proof and skip reporting

- CLI proof is the `cli-<tag>.txt` transcript: command, exit code, stdout and stderr.
- GUI proof is `gui-report.json`, with a step observation and a screenshot per action.
- Export proof also needs `$V check-mbtiles <file>` to exit 0.
- `known-bug` marks a check that fails on a defect already tracked in a fork PR. Report it as the known bug, not as verified.
- Report an entry point you could not drive with the attempted command. Never count it as verified through a different entry point.

## Feature entry contract

Each feature file starts with an H1 and one paragraph. It then has exactly four H2s, in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with vmctl` (starts with `Preconditions:`), and `Gotchas`.

## Features

- [Export MBTiles](./export-mbtiles.md): CLI and GUI export, themes, the day/night pair, offline cache behavior.
- [Inspect MBTiles](./inspect-mbtiles.md): CLI `inspect`, GUI File → Inspect MBTiles…, and the device-layout check.
- [GPX import and export](./gpx.md): File → Import GPX…, CLI `--gpx`, Export GPX for Voyager….
- [Track editing](./track-editing.md): draw a track, add a waypoint, extend a track, cancel.
- [Export area and estimate](./export-area.md): Area = tracks extent, Draw export rectangle, Clear, snap, CLI `estimate`.
- [Tile sources](./tile-sources.md): CLI `sources`, the layer list, Add/Edit/Remove source, Test sources.
