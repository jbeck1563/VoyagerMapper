# Tile sources

The user picks which public tile services make up the map, adjusts their opacity, and can add, edit or remove their own sources. A one-tile test separates network trouble from page trouble.

## Sub-features

- `sources-cli` runs `voymap sources` and lists ids, zoom ranges, base or overlay, `[UNVERIFIED URL]` and `[preview only]`.
- `layers-list` is the Layers dock: one checkbox and opacity slider per bulk-allowed source, with user sources marked ★.
- `source-add-edit-remove` uses `Add source…`, `Edit…` and `Remove`, plus the dialog's one-tile test.
- `sources-test` uses "Test sources (fetch one tile each)" and shows a box with the HTTP result per checked layer.
- `user-override` lets a `sources.json` entry with a built-in id replace that built-in.

## How to get to it (user POV)

- In a terminal: `voymap sources`.
- In the GUI: the Layers dock, and File → `Tile sources…`.

## Driving it with vmctl

Preconditions:

- The root is seeded. Offline mode puts a user override of `usgs_topo` in `<root>/home/.config/voymap/sources.json`.

- **CLI list.** Run `$V cli --tag sources -- sources`. Exit 0. The `usgs_topo` line reads `VERIFY offline fake (overrides usgs_topo)` offline, or `USGS Topo (The National Map)` live. `osm` shows `[preview only]`.
- **Layers dock.** In `gui-01-ready.png`, `★ VERIFY offline fake (overrides usgs_topo)` is the only checked row.
- **Add, edit, remove.** Not in `$V gui` yet. Click `Add source…`, fill the SourceDialog fields, and accept. The new ★ row appears, and `sources.json` gains the entry.

## Gotchas

- Editing a source's URL keeps serving cached tiles from the old URL, because the cache is keyed by id only (vm-01 report #4). Clear the cache before you verify an edited source.
- "Test sources" fetches on the UI thread (vm-01 report #7). Offline, the fake URL fails at once. Live, a slow USFS server freezes the window for up to 20 s per layer.
- Offline, the map preview shows `Tile load failures` for the fake source. That is expected.
