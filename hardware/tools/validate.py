#!/usr/bin/env python3
"""ERC-lite: rebuild the netlist from a generated .kicad_sch purely from
geometry and report nets + floating pins.  Independent cross-check of the
generator's intent (catches wrong pin numbers, net-name typos, missing joins).
"""
import sys
from collections import defaultdict
from kiutils.schematic import Schematic

Q = 100.0  # quantise to 0.01 mm


def key(x, y):
    return (round(x * Q), round(y * Q))


def build_pinmaps(sch):
    pm = {}
    ext = {}
    byname = {}
    for s in sch.libSymbols:
        lib_id = f"{s.libraryNickname}:{s.entryName}"
        byname[lib_id] = s
        d = {}
        for u in s.units:
            for p in u.pins:
                d[p.number] = (p.position.X, p.position.Y, p.name, p.electricalType)
        pm[lib_id] = d
        if s.extends:
            ext[lib_id] = f"{s.libraryNickname}:{s.extends}"
    # resolve extends (child inherits parent pins)
    for lib_id in list(pm):
        cur = lib_id
        chain = []
        while cur in ext:
            chain.append(ext[cur])
            cur = ext[cur]
        for parent in chain:
            for k, v in pm.get(parent, {}).items():
                pm[lib_id].setdefault(k, v)
    return pm


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def analyse(path):
    sch = Schematic().from_file(path)
    pm = build_pinmaps(sch)
    uf = UF()
    labels = defaultdict(list)   # point -> [netname]
    pin_at = defaultdict(list)   # point -> [(ref,pinnum,name,etype)]
    nc_pts = set()

    # wires
    for it in sch.graphicalItems:
        if getattr(it, "type", None) == "wire" and len(it.points) >= 2:
            pts = [key(p.X, p.Y) for p in it.points]
            for a, b in zip(pts, pts[1:]):
                uf.union(a, b)

    # labels
    for l in sch.labels:
        labels[key(l.position.X, l.position.Y)].append(l.text)
    for l in sch.globalLabels:
        labels[key(l.position.X, l.position.Y)].append(l.text)

    # no-connects
    for nc in sch.noConnects:
        nc_pts.add(key(nc.position.X, nc.position.Y))

    # symbol pins + power ports
    for s in sch.schematicSymbols:
        lib_id = f"{s.libraryNickname}:{s.entryName}"
        ref = next((p.value for p in s.properties if p.key == "Reference"), "?")
        val = next((p.value for p in s.properties if p.key == "Value"), "?")
        ox, oy = s.position.X, s.position.Y
        for num, (lx, ly, nm, et) in pm.get(lib_id, {}).items():
            pt = key(ox + lx, oy - ly)
            if ref.startswith("#PWR"):
                labels[pt].append(val)            # power port names its net
            elif ref.startswith("#FLG"):
                labels[pt].append("__FLAG__")
            else:
                pin_at[pt].append((ref, num, nm, et))

    # local labels of identical text on one sheet are the same net: union all
    # points that carry a given label name (KiCad name-based connectivity).
    name_anchor = {}
    for pt, names in labels.items():
        for n in names:
            if n == "__FLAG__":
                continue
            if n in name_anchor:
                uf.union(pt, name_anchor[n])
            else:
                name_anchor[n] = pt

    # every point that carries anything is a node; merge coincident points are
    # already same key. Nets = connected components.
    nets = defaultdict(lambda: {"names": set(), "pins": []})
    all_pts = set(labels) | set(pin_at) | set(nc_pts)
    for pt in all_pts:
        r = uf.find(pt)
        for n in labels.get(pt, []):
            nets[r]["names"].add(n)
        for pininfo in pin_at.get(pt, []):
            nets[r]["pins"].append(pininfo)

    # report
    named = {}
    for r, d in nets.items():
        realnames = sorted(n for n in d["names"] if n != "__FLAG__")
        name = realnames[0] if realnames else f"<unnamed@{r}>"
        named.setdefault(name, {"pins": [], "aliases": set()})
        named[name]["pins"] += d["pins"]
        named[name]["aliases"] |= set(realnames)

    print(f"\n=== {path} ===")
    print(f"symbols={len(sch.schematicSymbols)} libsyms={len(sch.libSymbols)} "
          f"wires={sum(1 for i in sch.graphicalItems if getattr(i,'type',None)=='wire')} "
          f"labels={len(sch.labels)} nc={len(sch.noConnects)} nets={len(named)}")

    # floating: component pins that are alone on a net and not no_connect
    nc_set = set()
    for pt in nc_pts:
        for pininfo in pin_at.get(pt, []):
            nc_set.add((pininfo[0], pininfo[1]))
    floating = []
    multi = 0
    for name, d in named.items():
        if len(d["pins"]) >= 2:
            multi += 1
        for (ref, num, nm, et) in d["pins"]:
            if len(d["pins"]) < 2 and (ref, num) not in nc_set and et != "no_connect":
                floating.append((name, ref, num, nm, et))

    print(f"multi-pin nets={multi}")
    print("\n-- key nets --")
    for name in sorted(named):
        if name.startswith("<unnamed"):
            continue
        pins = named[name]["pins"]
        if not pins:
            continue
        tag = ",".join(f"{r}.{n}({nm})" for r, n, nm, et in sorted(pins))
        print(f"  {name:12} [{len(pins)}] {tag}")

    print("\n-- FLOATING pins (single-pin nets, not NC) --")
    if floating:
        for name, ref, num, nm, et in sorted(floating):
            print(f"  !! {ref}.{num} {nm} ({et})  net={name}")
    else:
        print("  none")
    return floating


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyse(p)
