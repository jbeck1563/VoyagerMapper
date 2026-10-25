#!/usr/bin/env python3
"""Verification harness for VoyagerMapper (voymap).

Every command works inside one disposable run root (--root or $VOYMAP_VERIFY_ROOT):

  <root>/home        HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME, XDG_DATA_HOME for the app
  <root>/input       ride.gpx (two-segment track + waypoint)
  <root>/evidence    transcripts, screenshots, .mbtiles, gui-report.json  (cleanup keeps it)

Offline by default: `seed` writes a user sources.json whose `usgs_topo` entry overrides the
built-in one with an unreachable URL (127.0.0.1:9) and pre-fills its tile cache, the same
seeded-cache approach as tests/test_export_offline.py. `seed --live` skips both.

Run with the repo venv:  .venv/bin/python .claude/skills/verify-voymap/scripts/vmctl.py --root R <cmd>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PY = REPO / ".venv" / "bin" / "python"
FAKE_URL = "http://127.0.0.1:9/{z}/{x}/{y}"     # discard port: any cache miss fails fast, never the internet
SEED_ZOOMS = (8, 14)
TRACK_SEGS = [[(-111.69, 35.16), (-111.68, 35.17), (-111.67, 35.18)],
              [(-111.65, 35.20), (-111.63, 35.22), (-111.61, 35.24)]]
WAYPOINT = (-111.65, 35.20)


def paths(root: Path) -> dict[str, Path]:
    return {"home": root / "home", "input": root / "input", "evidence": root / "evidence",
            "gpx": root / "input" / "ride.gpx", "pid": root / "gui.pid"}


def app_env(root: Path) -> dict[str, str]:
    h = paths(root)["home"]
    env = dict(os.environ, HOME=str(h), XDG_CONFIG_HOME=str(h / ".config"), XDG_CACHE_HOME=str(h / ".cache"),
               XDG_DATA_HOME=str(h / ".local/share"), QT_QPA_PLATFORM="offscreen",
               QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu", PYTHONPATH=str(REPO))
    return env


# --------------------------------------------------------------------------- seed
def cmd_seed(root: Path, live: bool):
    p = paths(root)
    for k in ("home", "input", "evidence"):
        p[k].mkdir(parents=True, exist_ok=True)
    os.environ.update(app_env(root))            # voymap reads XDG_* at call time
    sys.path.insert(0, str(REPO))
    from PIL import Image
    from voymap.features import Feature, features_bbox, write_gpx
    from voymap.fetch import STATUS_OK, TileCache, default_cache_dir
    from voymap.sources import TileSource, save_user_sources

    feats = [Feature("t1", "line", "Loop", [list(s) for s in TRACK_SEGS], style={"color": "#ff0000", "width": 4}),
             Feature("w1", "point", "Camp", [[WAYPOINT]])]
    write_gpx(feats, p["gpx"])
    if live:
        print(f"seeded LIVE run at {root} (real tile servers, empty cache)")
        return
    save_user_sources([TileSource(id="usgs_topo", name="VERIFY offline fake (overrides usgs_topo)", kind="xyz",
                                  url=FAKE_URL, min_zoom=0, max_zoom=16, opaque=True,
                                  notes="written by verify-voymap; cache is pre-seeded")])
    # cover the GPX extent + padding, snapped to the z9 grid: a superset of what any z11-snapped export needs
    area = features_bbox(feats).buffered_deg(0.02, 0.02).snapped(9)
    buf = io.BytesIO()
    Image.new("RGBA", (256, 256), (200, 225, 200, 255)).save(buf, "PNG")
    cache = TileCache(default_cache_dir() / "usgs_topo.sqlite")
    n = 0
    for z in range(SEED_ZOOMS[0], SEED_ZOOMS[1] + 1):
        for x, y, _ in area.tiles(z):
            cache.put(z, x, y, STATUS_OK, buf.getvalue())
            n += 1
    print(f"seeded OFFLINE run at {root}: {n} cached tiles z{SEED_ZOOMS[0]}-{SEED_ZOOMS[1]}, "
          f"area {tuple(round(v, 4) for v in area.as_tuple())}, gpx {p['gpx']}")


# --------------------------------------------------------------------------- doctor
def cmd_doctor(root: Path) -> int:
    p = paths(root)
    env = app_env(root)
    ok = True

    def check(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"{'ok  ' if good else 'FAIL'} {name}{': ' + str(detail) if detail else ''}")

    check("repo venv python", PY.exists(), PY)
    r = subprocess.run([str(PY), "-c", "import voymap, PySide6; from PySide6 import QtWebEngineWidgets; "
                        "print(voymap.__version__, PySide6.__version__, voymap.__file__)"],
                       env=env, capture_output=True, text=True)
    check("voymap + PySide6/QtWebEngine import", r.returncode == 0, (r.stdout or r.stderr).strip()[-200:])
    check("voymap imported from this checkout", str(REPO) in r.stdout, REPO)
    check("run root seeded", p["gpx"].exists(), p["gpx"])
    sj = p["home"] / ".config/voymap/sources.json"
    cache = p["home"] / ".cache/voymap/tiles/usgs_topo.sqlite"
    if sj.exists():
        check("offline override active", FAKE_URL in sj.read_text(), sj)
        n = sqlite3.connect(f"file:{cache}?mode=ro", uri=True).execute("select count(*) from tiles").fetchone()[0] \
            if cache.exists() else 0
        check("seeded cache tiles", n > 0, f"{n} in {cache}")
    else:
        print(f"info LIVE mode (no {sj}): exports download from the real tile servers")
    r = subprocess.run([str(PY), "-m", "voymap", "sources"], env=env, capture_output=True, text=True)
    first = next((l for l in r.stdout.splitlines() if l.startswith("usgs_topo")), "")
    check("`voymap sources` runs in isolated env", r.returncode == 0, first.strip())
    if p["pid"].exists():
        pid = int(p["pid"].read_text())
        alive = Path(f"/proc/{pid}").exists()
        check("no GUI left running from this root", not alive, f"pid {pid} {'ALIVE' if alive else 'gone'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------- cli
def cmd_cli(root: Path, args: list[str], tag: str) -> int:
    ev = paths(root)["evidence"]
    ev.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), "-m", "voymap", *args]
    t0 = time.time()
    r = subprocess.run(cmd, env=app_env(root), cwd=ev, capture_output=True, text=True)
    out = ev / f"cli-{tag}.txt"
    out.write_text(f"$ cd {ev} && voymap {' '.join(args)}\nexit={r.returncode}  ({time.time() - t0:.1f}s)\n"
                   f"--- stdout\n{r.stdout}--- stderr\n{r.stderr.replace(chr(13), chr(10))}")
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr[-2000:])
    print(f"[exit {r.returncode}] transcript: {out}")
    return r.returncode


# --------------------------------------------------------------------------- gui (outer)
def cmd_gui(root: Path, timeout: int) -> int:
    p = paths(root)
    p["evidence"].mkdir(parents=True, exist_ok=True)
    log = open(p["evidence"] / "gui-stderr.txt", "w")
    proc = subprocess.Popen([str(PY), "-u", __file__, "--root", str(root), "_gui-inner"], env=app_env(root),
                            stdout=sys.stdout, stderr=log)
    p["pid"].write_text(str(proc.pid))
    try:
        rc = proc.wait(timeout)
    except subprocess.TimeoutExpired:
        proc.kill()                                  # only the process this run started
        proc.wait()
        print(f"GUI driver timed out after {timeout}s; killed pid {proc.pid}", file=sys.stderr)
        rc = 124
    p["pid"].unlink(missing_ok=True)
    print(f"[exit {rc}] report: {p['evidence'] / 'gui-report.json'}  stderr: {p['evidence'] / 'gui-stderr.txt'}")
    return rc


# --------------------------------------------------------------------------- gui (inner, in the app env)
def gui_inner(root: Path) -> int:
    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox, QPushButton
    from voymap.gui.main_window import MainWindow

    p = paths(root)
    ev = p["evidence"]
    out_path = ev / "gui-export.mbtiles"
    report = {"steps": [], "checks": []}
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    def pump(cond, timeout=30.0, what="condition"):
        end = time.time() + timeout
        while time.time() < end:
            app.processEvents()
            if cond():
                return True
            time.sleep(0.02)
        raise TimeoutError(f"timed out waiting for {what}")

    def js(code):
        box = []
        win.view.page().runJavaScript(code, 0, box.append)
        pump(lambda: box, 10, f"js {code[:40]}")
        return box[0]

    def step(name, **obs):
        report["steps"].append({"step": name, **obs})
        print(f"step {name}: {json.dumps(obs, default=str)}")

    def check(name, good, detail="", known=None):
        status = "pass" if good else ("known-bug" if known else "FAIL")
        report["checks"].append({"check": name, "status": status, "detail": detail, **({"known": known} if known else {})})
        print(f"{status:9s} {name} {detail}")

    def shot(name):
        end = time.time() + 0.5                      # let the web view paint the latest frame
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)
        f = ev / f"gui-{name}.png"
        win.grab().save(str(f))
        return f.name

    def button(text):
        for b in win.findChildren(QPushButton):
            if b.text() == text:
                return b
        raise LookupError(f"no button {text!r}")

    def click(widget, pos=None):
        QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, pos or widget.rect().center())
        app.processEvents()

    def menu_action(text):
        for a in win.menuBar().actions()[0].menu().actions():
            if a.text() == text:
                return a
        raise LookupError(f"no File menu action {text!r}")

    def with_dialogs(trigger, handlers, what, timeout=60):
        """Trigger something that opens modal dialogs in sequence; each handler answers one like a user."""
        seen, queue = [], list(handlers)

        def poll():
            d = app.activeModalWidget()
            if d is not None and d.isVisible() and queue:
                seen.append(queue.pop(0)(d))
            if queue:
                QTimer.singleShot(50, poll)

        QTimer.singleShot(50, poll)
        trigger()
        pump(lambda: not queue, timeout, what)
        return seen

    def file_dialog(path):
        def h(d):
            assert isinstance(d, QFileDialog), type(d)
            edit = d.findChild(QLineEdit, "fileNameEdit")     # type the full path, press Enter
            edit.setFocus()
            edit.setText(str(path))
            QTest.keyClick(edit, Qt.Key_Return)
            return str(path)
        return h

    def message_box(d):
        assert isinstance(d, QMessageBox), type(d)
        info = {"title": d.windowTitle(), "text": d.text()}
        d.accept()
        return info

    def key_map(key):
        QTest.keyClick(win.view.focusProxy(), key)
        app.processEvents()

    def track_segments():
        t = next((f for f in win.features if f.kind == "line"), None)
        return [len(s) for s in t.coords] if t else None

    rc = 0
    try:
        pump(lambda: win._page_ready, 60, "map page bridge ready")
        pump(lambda: js("document.getElementById('status').textContent") == "ready", 10, "page status ready")
        step("launch", status_bar=win.statusBar().currentMessage(), title=win.windowTitle(), screenshot=shot("01-ready"))

        # 1. File > Import GPX…
        with_dialogs(menu_action("Import GPX…").trigger, [file_dialog(p["gpx"])], "Import GPX dialog")
        pump(lambda: win.feature_list.count() == 2, 10, "2 features in list")
        names = [win.feature_list.item(i).text() for i in range(win.feature_list.count())]
        svg_paths = js("document.querySelectorAll('.leaflet-overlay-pane path').length")
        segs_before = track_segments()
        step("import-gpx", feature_list=names, map_paths=svg_paths, track_segments=segs_before, screenshot=shot("02-imported"))
        check("import shows track + waypoint", len(names) == 2 and svg_paths >= 2, names)

        # 2. select track, Extend track, click a point on the map, Esc
        row = next(i for i in range(win.feature_list.count()) if "Loop" in win.feature_list.item(i).text())
        item = win.feature_list.item(row)
        click(win.feature_list.viewport(), win.feature_list.visualItemRect(item).center())
        pump(lambda: win.style_box.isEnabled(), 5, "Selected feature box enabled")
        click(button("Extend track"))
        pump(lambda: js("getComputedStyle(document.getElementById('trackbar')).display") == "block", 10, "track bar")
        info0 = js("document.getElementById('trackinfo').textContent")
        fp = win.view.focusProxy()
        click(fp, QPoint(fp.width() // 2 + 40, fp.height() // 2 + 40))
        pump(lambda: js("document.getElementById('trackinfo').textContent") != info0, 5, "point added")
        info1 = js("document.getElementById('trackinfo').textContent")
        step("extend-track", trackbar=info0, after_map_click=info1, screenshot=shot("03-extending"))
        key_map(Qt.Key_Escape)
        pump(lambda: js("getComputedStyle(document.getElementById('trackbar')).display") == "none", 5, "track bar hidden")
        pump(lambda: track_segments() is not None, 5, "track back in model")
        segs_after = track_segments()
        step("cancel-extend", track_segments=segs_after, feature_list=[win.feature_list.item(i).text()
                                                                       for i in range(win.feature_list.count())],
             screenshot=shot("04-cancelled"))
        check("Esc ends extend mode", True, f"{info0!r} -> {info1!r} -> hidden")
        check("cancel restores original track", segs_after == segs_before, f"{segs_before} -> {segs_after}",
              known="vm-01 report #3, fork PR #3 (extend drops earlier segments)")

        # 3. export area = tracks extent; zooms 10-13 typed into the spin boxes
        click(button("Area = tracks extent"))
        pump(lambda: win.export_area is not None, 10, "export area from page")
        for sb, v in ((win.e_zmin, "10"), (win.e_zmax, "13")):
            sb.setFocus()
            sb.selectAll()
            QTest.keyClicks(sb, v)
            QTest.keyClick(sb, Qt.Key_Tab)
        app.processEvents()
        step("export-area", area=win.area_label.text(), estimate=win.estimate_label.text(),
             zooms=win.zoom_table.text(), screenshot=shot("05-area"))
        check("area + estimate shown", win.export_area is not None and "tiles" in win.estimate_label.text(),
              win.estimate_label.text().splitlines()[0])

        # 4. Export MBTiles… > save dialog > wait > "Export complete" box
        _, done = with_dialogs(lambda: click(button("Export MBTiles…")), [file_dialog(out_path), message_box],
                               "save dialog, export, then the finished box", timeout=180)
        step("export", dialog=done, overall=win.overall_label.text(), progress=win.progress_label.text(),
             screenshot=shot("06-exported"))
        check("export completes", done["title"] == "Export complete" and out_path.exists(), done["text"].split("\n")[0])

        # 5. File > Inspect MBTiles…
        _, insp = with_dialogs(menu_action("Inspect MBTiles…").trigger, [file_dialog(out_path), message_box],
                               "Inspect MBTiles dialog + result box")
        (ev / "gui-inspect.txt").write_text(insp["text"])
        step("inspect", text=insp["text"])
        check("GUI inspection lists the tiles table", "tiles" in insp["text"], "gui-inspect.txt")
    except Exception as e:  # noqa: BLE001
        report["error"] = f"{type(e).__name__}: {e}"
        print(f"ERROR {report['error']}")
        try:
            shot("99-error")
        except Exception:  # noqa: BLE001
            pass
        rc = 2
    if any(c["status"] == "FAIL" for c in report["checks"]):
        rc = rc or 1
    (ev / "gui-report.json").write_text(json.dumps(report, indent=2, default=str))
    win.close()
    app.processEvents()
    return rc


# --------------------------------------------------------------------------- mbtiles check
def cmd_check_mbtiles(path: Path) -> int:
    sys.path.insert(0, str(REPO))
    from PIL import Image
    from voymap.mbtiles import inspect as mb_inspect
    from voymap.tilemath import lonlat_to_tile

    ref = ["name", "type", "version", "description", "format", "created", "bounds"]
    info = mb_inspect(path)
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    n = db.execute("select count(*) from tiles").fetchone()[0]
    idx = [r[0] for r in db.execute("select name from sqlite_master where type='index' order by name")]
    x, y = lonlat_to_tile(*TRACK_SEGS[1][1], 13)
    row = db.execute("select tile_data from tiles where zoom_level=13 and tile_column=? and tile_row=?",
                     (x, (1 << 13) - 1 - y)).fetchone()
    reds = 0
    if row:
        px = Image.open(io.BytesIO(row[0])).convert("RGB").tobytes()
        reds = sum(1 for i in range(0, len(px), 3) if px[i] > 200 and px[i + 1] < 90 and px[i + 2] < 90)
    checks = [("7 CalTopo metadata keys in order", list(info["metadata"]) == ref, list(info["metadata"])),
              ("indexes idx_x/idx_y/idx_z", idx == ["idx_x", "idx_y", "idx_z"], idx),
              ("tiles written", n > 0, n),
              ("256x256 palette PNG", info["sample_tile"] and info["sample_tile"]["mode"] == "P"
               and tuple(info["sample_tile"]["size"]) == (256, 256), info["sample_tile"]),
              ("track burned in (red px at z13, TMS row)", reds > 20, reds)]
    bad = 0
    for name, good, detail in checks:
        bad += not good
        print(f"{'ok  ' if good else 'FAIL'} {name}: {detail}")
    return 1 if bad else 0


# --------------------------------------------------------------------------- cleanup
def cmd_cleanup(root: Path):
    p = paths(root)
    if p["pid"].exists():
        pid = int(p["pid"].read_text())
        if Path(f"/proc/{pid}").exists():
            os.kill(pid, 9)                          # the pid this root's `gui` started, never by name
            print(f"killed leftover GUI pid {pid}")
        p["pid"].unlink()
    for k in ("home", "input"):
        shutil.rmtree(p[k], ignore_errors=True)
    print(f"removed {p['home']} and {p['input']}; evidence kept at {p['evidence']}:")
    for f in sorted(p["evidence"].glob("*")):
        print(f"  {f.name}  {f.stat().st_size} B")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.environ.get("VOYMAP_VERIFY_ROOT"), help="run root (or $VOYMAP_VERIFY_ROOT)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed", help="create the isolated home, GPX and (offline) seeded cache")
    s.add_argument("--live", action="store_true", help="no fake source / seeded cache: use the real tile servers")
    sub.add_parser("doctor", help="read-only: is this root worth driving?")
    c = sub.add_parser("cli", help="run `voymap ARGS` in the isolated env (cwd = evidence dir), save transcript")
    c.add_argument("--tag", required=True, help="transcript name: evidence/cli-<tag>.txt")
    c.add_argument("args", nargs=argparse.REMAINDER)
    g = sub.add_parser("gui", help="drive the GUI offscreen: import, extend+cancel, area, export, inspect")
    g.add_argument("--timeout", type=int, default=300)
    sub.add_parser("_gui-inner")
    m = sub.add_parser("check-mbtiles", help="assert the device layout of an exported file")
    m.add_argument("path", type=Path)
    sub.add_parser("cleanup", help="kill this root's GUI if left running, delete home/input, keep evidence")
    a = ap.parse_args()
    if a.cmd != "check-mbtiles" and not a.root:
        ap.error("--root or $VOYMAP_VERIFY_ROOT is required")
    root = Path(a.root).resolve() if a.root else None
    if a.cmd == "seed":
        cmd_seed(root, a.live)
    elif a.cmd == "doctor":
        sys.exit(cmd_doctor(root))
    elif a.cmd == "cli":
        sys.exit(cmd_cli(root, [x for x in a.args if x != "--"], a.tag))
    elif a.cmd == "gui":
        sys.exit(cmd_gui(root, a.timeout))
    elif a.cmd == "_gui-inner":
        sys.exit(gui_inner(root))
    elif a.cmd == "check-mbtiles":
        sys.exit(cmd_check_mbtiles(a.path))
    elif a.cmd == "cleanup":
        cmd_cleanup(root)


if __name__ == "__main__":
    main()
