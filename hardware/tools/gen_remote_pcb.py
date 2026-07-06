#!/usr/bin/env python3
"""Generate hardware/remote/remote.kicad_pcb from remote.kicad_sch.

First-pass PCB for the battery remote: loads the real KiCad footprints, places
every part in functional groups, assigns the schematic netlist to the pads and
draws the board outline (Edge.Cuts).  Traces and the GND pour are left for the
routing pass -- this establishes placement + full ratsnest.

Netlist is reconstructed from the schematic with validate.py's proven
geometry/label connectivity, so the PCB nets always match the captured design.

Self-check: a courtyard/pad-bbox overlap test runs before writing, since there
is no GUI DRC in this environment.
"""
import os
import sys
import subprocess
import tempfile
from collections import defaultdict
from kiutils.schematic import Schematic
from kiutils.board import Board, Net
from kiutils.footprint import Footprint
from kiutils.items.common import Position, Net as PadNet
from kiutils.items.gritems import GrLine
import validate as V

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "remote", "remote.kicad_pcb")


def fresh_schematic():
    """Emit a fresh kiutils-native (20230121) schematic to a scratch file.

    The committed schematic may have been re-saved by KiCad into a newer format
    that kiutils under-parses (silently dropping power-net pins), so the netlist
    is always taken from the generator's own output, never the committed file.
    """
    tmp = tempfile.mktemp(suffix=".kicad_sch")
    subprocess.run([sys.executable, os.path.join(HERE, "gen_remote.py")],
                   env={**os.environ, "REMOTE_SCH_OUT": tmp},
                   check=True, stdout=subprocess.DEVNULL)
    return tmp
STOCK = "/usr/share/kicad/footprints"
PROJECT_FP = os.path.join(HERE, "..", "footprints")


# --------------------------------------------------------------------------
# 1. Netlist from the schematic (reuse validate.py connectivity)
# --------------------------------------------------------------------------
def extract(path):
    sch = Schematic().from_file(path)
    pm = V.build_pinmaps(sch)
    uf = V.UF()
    labels = defaultdict(list)
    pin_at = defaultdict(list)

    for it in sch.graphicalItems:
        if getattr(it, "type", None) == "wire" and len(it.points) >= 2:
            pts = [V.key(p.X, p.Y) for p in it.points]
            for a, b in zip(pts, pts[1:]):
                uf.union(a, b)
    for l in sch.labels:
        labels[V.key(l.position.X, l.position.Y)].append(l.text)
    comps = {}
    for s in sch.schematicSymbols:
        lib_id = f"{s.libraryNickname}:{s.entryName}"
        ref = next((p.value for p in s.properties if p.key == "Reference"), "?")
        fp = next((p.value for p in s.properties if p.key == "Footprint"), "")
        if not ref.startswith("#"):
            comps[ref] = fp
        ox, oy = s.position.X, s.position.Y
        for num, (lx, ly, nm, et) in pm.get(lib_id, {}).items():
            pt = V.key(ox + lx, oy - ly)
            if ref.startswith("#PWR"):
                val = next((p.value for p in s.properties if p.key == "Value"), "?")
                labels[pt].append(val)
            elif ref.startswith("#FLG"):
                labels[pt].append("__FLAG__")
            else:
                pin_at[pt].append((ref, num))

    anchor = {}
    for pt, names in labels.items():
        for n in names:
            if n == "__FLAG__":
                continue
            if n in anchor:
                uf.union(pt, anchor[n])
            else:
                anchor[n] = pt

    nets = defaultdict(lambda: {"names": set(), "pins": []})
    for pt in set(labels) | set(pin_at):
        r = uf.find(pt)
        nets[r]["names"].update(n for n in labels.get(pt, []) if n != "__FLAG__")
        nets[r]["pins"].extend(pin_at.get(pt, []))

    named = {}
    for d in nets.values():
        if not d["pins"]:
            continue
        name = sorted(d["names"])[0] if d["names"] else None
        if name is None:
            continue
        named.setdefault(name, [])
        named[name].extend(d["pins"])
    return comps, named


# --------------------------------------------------------------------------
# 2. Footprint loading
# --------------------------------------------------------------------------
def fp_path(lib_id):
    nick, name = lib_id.split(":", 1)
    base = PROJECT_FP if nick == "IoT_AC_Dimmer" else STOCK
    return os.path.join(base, f"{nick}.pretty", f"{name}.kicad_mod")


def load_fp(lib_id, ref, value, x, y, angle=0):
    fp = Footprint.from_file(fp_path(lib_id))
    fp.position = Position(x, y, angle)
    for gi in fp.graphicItems:
        t = getattr(gi, "type", None)
        if t == "reference":
            gi.text = ref
        elif t == "value":
            gi.text = value
    return fp


def pad_bbox(fp):
    """Axis-aligned bbox of a placed footprint's pads, in board coords."""
    import math
    a = math.radians(fp.position.angle or 0)
    ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for p in fp.pads:
        px, py = p.position.X, p.position.Y
        rx = px * ca - py * sa + fp.position.X
        ry = px * sa + py * ca + fp.position.Y
        sx = (p.size.X if p.size else 1) / 2
        sy = (p.size.Y if p.size else 1) / 2
        xs += [rx - sx, rx + sx]
        ys += [ry - sy, ry + sy]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------
# 3. Placement (mm, KiCad board coords: +y is down)
# --------------------------------------------------------------------------
#   ref -> (x, y, angle).  Left column = power/charge + buttons; right = DevKit.
PLACE = {
    "BT1": (12, 8, 0),      # JST-PH battery
    "U1": (10, 18, 0),      # TP4056 module (1x6 header)
    "U2": (28, 12, 0),      # ME6211 LDO
    "C2": (23, 20, 0),      # VSYS in cap
    "C3": (33, 20, 0),      # 3V3 out cap
    "C4": (30, 30, 0),      # 3V3 bulk
    "C5": (37, 30, 0),      # 3V3 100nF
    "U3": (56, 30, 0),      # ESP32 DevKit (big)
    # three button groups, each a vertical stack: pull-up / debounce / button
    "R4": (11, 42, 0), "C6": (11, 47, 0), "SW1": (11, 53, 0),   # UP
    "R5": (25, 42, 0), "C7": (25, 47, 0), "SW2": (25, 53, 0),   # DOWN
    "R6": (39, 42, 0), "C8": (39, 47, 0), "SW3": (39, 53, 0),   # ON/OFF
}
BOARD = (78, 60)   # width, height mm


def main():
    comps, nets = extract(fresh_schematic())
    missing = set(comps) - set(PLACE)
    if missing:
        sys.exit(f"no placement for: {sorted(missing)}")

    board = Board.create_new()
    # net table: 0 = unconnected, then one per named net
    net_num = {"": 0}
    board.nets = [Net(0, "")]
    for i, name in enumerate(sorted(nets), start=1):
        net_num[name] = i
        board.nets.append(Net(i, name))
    pad_net = {}   # (ref, pad) -> (num, name)
    for name, pins in nets.items():
        for ref, pad in pins:
            pad_net[(ref, pad)] = (net_num[name], name)

    placed = {}
    for ref, lib_id in comps.items():
        x, y, ang = PLACE[ref]
        value = ref  # value text not critical for layout; keep ref
        fp = load_fp(lib_id, ref, value, x, y, ang)
        for pad in fp.pads:
            num, nm = pad_net.get((ref, str(pad.number)), (0, ""))
            pad.net = PadNet(num, nm)
        board.footprints.append(fp)
        placed[ref] = fp

    # ---- self-check: pad-bbox overlaps (clearance 0.8mm) -----------------
    CLR = 0.8
    boxes = {r: pad_bbox(f) for r, f in placed.items()}
    clashes = []
    refs = sorted(boxes)
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = boxes[refs[i]], boxes[refs[j]]
            if (a[0] - CLR < b[2] and b[0] - CLR < a[2] and
                    a[1] - CLR < b[3] and b[1] - CLR < a[3]):
                clashes.append((refs[i], refs[j]))
    # also flag anything outside the board outline
    outside = [r for r, bx in boxes.items()
               if bx[0] < 1 or bx[1] < 1 or bx[2] > BOARD[0] - 1 or bx[3] > BOARD[1] - 1]

    # ---- board outline (Edge.Cuts rectangle) -----------------------------
    w, h = BOARD
    corners = [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]
    for (x1, y1), (x2, y2) in zip(corners, corners[1:]):
        board.graphicItems.append(GrLine(
            start=Position(x1, y1), end=Position(x2, y2),
            layer="Edge.Cuts", width=0.15))

    board.to_file(os.path.abspath(OUT))
    Board().from_file(os.path.abspath(OUT))   # sanity re-read

    print("wrote", os.path.abspath(OUT))
    print(f"footprints={len(board.footprints)} nets={len(board.nets)-1} "
          f"board={w}x{h}mm")
    print("pad-bbox clashes:", clashes or "none")
    print("outside outline:", outside or "none")
    if clashes or outside:
        sys.exit("PLACEMENT PROBLEM - fix PLACE/BOARD")


if __name__ == "__main__":
    main()
