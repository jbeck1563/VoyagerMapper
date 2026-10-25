---
name: verify-voymap
description: Launch and drive VoyagerMapper (voymap) like a user to prove a change works - the CLI (export, inspect, sources, estimate) and the PySide6/QtWebEngine desktop GUI run offscreen (import GPX, extend/cancel a track, set the export area, export MBTiles, inspect). Offline by default via a seeded tile cache. Use after touching voymap/ or voymap/gui/, or when asked to run, screenshot, or verify the app.
---

# Verify VoyagerMapper

voymap builds offline `.mbtiles` maps for the Trail Tech Voyager Pro. Users touch two surfaces that share one core: the CLI (`python -m voymap ...`) and the desktop GUI (`python -m voymap gui`: Qt docks around a Leaflet page in QtWebEngine, linked by QWebChannel). Everything runs through one helper, `scripts/vmctl.py`, against a disposable **run root**.

Feature recipes live in [`features/README.md`](features/README.md). Read the matching feature file before driving.

## Launch

Install once, from the repo root:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[gui,dev]"
```

Pick a run root outside the repo, then seed it. Every command below uses these two variables:

```bash
export VOYMAP_VERIFY_ROOT=/tmp/voymap-verify-$(date +%s)        # one root per run; never reuse another run's root
V=".venv/bin/python .claude/skills/verify-voymap/scripts/vmctl.py"
$V seed                # offline: fake `usgs_topo` source (127.0.0.1:9) + 1366 cached tiles z8-14 + input/ride.gpx
# $V seed --live       # optional: no fake source, empty cache; exports download from the real tile servers
```

`seed` creates `<root>/home` and points `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `XDG_DATA_HOME` at it for every app process. That isolates `sources.json`, the tile cache, QSettings (`voymap.conf`: last dir, map view) and the QtWebEngine profile. The real `~/.config/voymap` and `~/.cache/voymap` are never touched, so runs with different roots can work side by side. The GUI's map page binds a random loopback port.

`input/ride.gpx` holds a track `Loop` with **two** `<trkseg>`s (3 points each) and a waypoint `Camp`, near Flagstaff AZ.

- **CLI:** there is no server. Each `$V cli` call is one short-lived process. Ready means `doctor` passes.
- **GUI:** `$V gui` starts the real `MainWindow` offscreen (`QT_QPA_PLATFORM=offscreen`, `QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu"`) in a child process. The child records its pid in `<root>/gui.pid`. Ready means the page called `bridge.ready()` and `#status` reads `ready`. The driver waits up to 60 s for this. The driver closes the window itself. `--timeout` (default 300 s) kills only that pid.

## Doctor

```bash
$V doctor              # read-only; exit 0 = worth driving
```

It checks that the venv imports voymap **from this checkout** with PySide6/QtWebEngine, that the root is seeded, that the offline override is active and the cache has tiles, and that `voymap sources` runs in the isolated env. Offline mode shows `usgs_topo ... VERIFY offline fake (overrides usgs_topo)`. It also checks that no GUI from this root is still alive. Run it first, and again whenever something looks off.

## Drive

CLI. The working directory is `<root>/evidence`, so relative `-o` paths land there. Each call saves the command, the exit code, stdout and stderr to `evidence/cli-<tag>.txt`:

```bash
$V cli --tag export  -- export --gpx $VOYMAP_VERIFY_ROOT/input/ride.gpx --zooms 10-13 -o cli-export.mbtiles --name "Verify CLI"
$V cli --tag inspect -- inspect cli-export.mbtiles
$V cli --tag sources -- sources
$V cli --tag estimate -- estimate --bbox -111.70 35.15 -111.60 35.25 --zooms 10-13
$V check-mbtiles $VOYMAP_VERIFY_ROOT/evidence/cli-export.mbtiles     # device-layout assertions (no env needed)
```

GUI, the full user path in one call:

```bash
$V gui                 # exit 0 = no FAIL check; 1 = a check failed; 2 = driver error; 124 = timeout
$V check-mbtiles $VOYMAP_VERIFY_ROOT/evidence/gui-export.mbtiles
```

The GUI driver uses only real user input:

- `QTest` mouse clicks on buttons found by their visible text, such as `Extend track`, `Area = tracks extent` and `Export MBTiles…`.
- File-menu actions found by text: `Import GPX…` and `Inspect MBTiles…`.
- A click on the map widget (`view.focusProxy()`), and `Esc` sent to the map.
- Typed values for the zoom spin boxes.
- Modal dialogs answered like a user. File dialogs get the full path typed into `fileNameEdit`, then Enter. Message boxes get their text recorded, then OK.

The driver reads state only from what a user sees, or from what the export consumes: the feature list, the area and estimate labels, `#trackbar`/`#trackinfo`/`#status` in the page DOM, `MainWindow.features` (the model the export burns in), the export dialog and the written file. It never calls `window.vm.*` or the `_private` slots directly. To drive one more step by hand, copy the pattern in `gui_inner()`: find the widget by its text, `click()` it, then `pump()` until a visible state changes.

## Evidence

Everything goes to `<root>/evidence/`, and cleanup keeps it:

| file | proves |
|---|---|
| `cli-<tag>.txt` | the CLI command, exit code, stdout and stderr (progress lines with `err=`/`miss=`) |
| `cli-export.mbtiles`, `gui-export.mbtiles` | the side effect itself; `check-mbtiles` verifies the 7 metadata keys in CalTopo order, `idx_x/idx_y/idx_z`, 256×256 palette PNG tiles, and red track pixels in the z13 tile under its TMS row |
| `gui-report.json` | every step's observations, plus `checks` with `pass` / `FAIL` / `known-bug` |
| `gui-01-ready.png` … `gui-06-exported.png` | a window grab (docks and the rendered Leaflet map) after each action |
| `gui-inspect.txt`, `gui-stderr.txt` | the text of the File → Inspect MBTiles box; Qt/Chromium stderr |

Proof standards:

- Drive the real path: menus, buttons, dialogs and the map widget. Do not use internal setters or `window.vm` calls.
- Pair each action with the state it produced: the step observation plus a screenshot, not only the final screen.
- Verify the side effect. Check that the `.mbtiles` exists and passes `check-mbtiles`. A success dialog alone is not proof.
- Offline mode replaces exactly one boundary: tile HTTP downloads. `fetch_many` still runs and reads from the cache, as in `tests/test_export_offline.py`. Before you claim the run made no network calls, confirm `err=0` in the transcript. A cache miss would try `127.0.0.1:9` and count as an error, never reach the internet.
- A `known-bug` check is an open defect with a fork PR, recorded so it is not mistaken for a new regression. When the fix lands, the check turns `pass`.

## Cleanup

```bash
$V cleanup             # kills <root>/gui.pid if still alive (never by process name), deletes home/ and input/, lists evidence/
```

Run it after every attempt, failed ones too. Copy `evidence/` elsewhere if the root is under `/tmp` and the proof must outlive a reboot.

## Gotchas

- The map shows the banner `Tile load failures: N (last: usgs_topo)` in offline mode. That is expected: the preview tries the fake URL. Exports read the seeded cache and are unaffected.
- The seeded cache covers only the GPX neighbourhood, the z9 tile grid around it: about W -111.80, S 34.89, E -111.09, N 35.46, at z8-14. An export outside that area, above z14, with `--refresh` or "ignore tile cache", or with any layer other than `usgs_topo` will try the network and report `err>0`. Add tiles in `cmd_seed` instead.
- `QFileDialog.selectFile()` + `accept()` does not close the offscreen dialog. Type the path into `fileNameEdit` and press Enter, as `file_dialog()` does.
- Blocking calls such as `getSaveFileName` and `QMessageBox.information` run nested event loops. Queue the handlers before the trigger (`with_dialogs(trigger, [h1, h2])`), or the driver deadlocks.
- `win.grab()` can show a stale web frame. `shot()` pumps events for 0.5 s first.
- The extend-track bug (vm-01 report #3, fork PR #3) also shrinks "Area = tracks extent" to the surviving segment, so the GUI export is smaller than the CLI one (43 vs 86 tiles at z10-13). That is expected until the fix lands.
- `Vulkan`, `GLX: No XCB Connection` and `propagateSizeHints` lines in `gui-stderr.txt` are harmless offscreen noise.
- To see a visible window instead, run `.venv/bin/python -m voymap gui` under WSLg with the same `HOME`/`XDG_*` values. That mode is interactive only; the driver is offscreen.
