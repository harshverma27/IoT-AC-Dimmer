"""schlib.py - lightweight KiCad-10 schematic builder built on kiutils.

Bootstraps the initial schematic capture for the IoT AC Dimmer boards. It
embeds real KiCad standard-library symbols where they exist and defines clean
custom symbols (correct datasheet pinouts) for the parts that don't ship with
KiCad, then places them and wires them up with a net-label / power-symbol
netlist.

Connectivity model (single root sheet):
  * Signal nets   -> identical local labels on a short stub at each pin.
  * Power nets    -> a power port symbol (GND/+3V3/+5V/VBUS) on a stub at each pin.
Both styles are canonical KiCad and produce a correct netlist for ERC.

Coordinate note: KiCad places a library symbol with its Y axis flipped, so for a
symbol dropped at orientation 0 a pin at library (lx, ly) lands at schematic
(sym_x + lx, sym_y - ly).  All placements here use orientation 0 (no rotation).
"""
from __future__ import annotations
import copy
import uuid as _uuid
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib, Symbol, SymbolPin
from kiutils.items.schitems import (
    SchematicSymbol, LocalLabel, Connection, Junction, NoConnect,
    SymbolProjectInstance, SymbolProjectPath,
)
from kiutils.items.syitems import SyRect
from kiutils.items.common import (
    Position, Property, Effects, Font, Stroke, Justify,
)

SYMDIR = "/usr/share/kicad/symbols"


def uid() -> str:
    return str(_uuid.uuid4())


def _eff(size=1.27, hide=False, justify=None, bold=False):
    j = Justify()
    if justify == "left":
        j.horizontally = "left"
    elif justify == "right":
        j.horizontally = "right"
    return Effects(font=Font(height=size, width=size, bold=bold), justify=j, hide=hide)


# --------------------------------------------------------------------------
# Custom symbol construction
# --------------------------------------------------------------------------
PITCH = 2.54


def make_rect_symbol(lib_id, ref, value, left=None, right=None, top=None,
                     bottom=None, half_width=None, description="", keywords="",
                     fp_filters=None, datasheet="~", in_bom=True, on_board=True,
                     power=False):
    """Build a rectangular multi-pin symbol.

    Each side list holds (number, name, etype) tuples laid out on a 2.54 grid.
    Returns a kiutils Symbol ready to embed in a schematic's lib_symbols.
    """
    left = left or []
    right = right or []
    top = top or []
    bottom = bottom or []
    nick, name = lib_id.split(":", 1)

    rows = max(len(left), len(right), 1)
    cols = max(len(top), len(bottom), 1)
    # vertical extent driven by side pins, horizontal by top/bottom pins
    body_h = (rows + 1) * PITCH
    if half_width is None:
        longest = max([len(n) for _, n, _ in left + right] + [3])
        half_width = max(cols * PITCH, longest * 0.55 + PITCH) + PITCH
        half_width = round(half_width / 1.27) * 1.27
    half_h = body_h / 2

    sym = Symbol.create_new(id=name, reference=ref, value=value,
                            datasheet=datasheet)
    sym.libraryNickname = nick
    sym.entryName = name
    sym.inBom = in_bom
    sym.onBoard = on_board
    sym.isPower = power
    sym.pinNamesOffset = 0.508
    # metadata properties
    sym.properties.append(Property(key="Description", value=description, id=4,
                                   position=Position(0, 0, 0), effects=_eff(hide=True)))
    if keywords:
        sym.properties.append(Property(key="ki_keywords", value=keywords, id=5,
                                       position=Position(0, 0, 0), effects=_eff(hide=True)))
    if fp_filters:
        sym.properties.append(Property(key="ki_fp_filters", value=fp_filters, id=6,
                                       position=Position(0, 0, 0), effects=_eff(hide=True)))
    # place reference above, value below the body
    sym.properties[0].position = Position(-half_width, half_h + 1.27, 0)
    sym.properties[0].effects = _eff(justify="left")
    sym.properties[1].position = Position(-half_width, -half_h - 1.27, 0)
    sym.properties[1].effects = _eff(justify="left")

    # unit sub-symbols are named bare ("NAME_0_1"), never nick-prefixed
    body = Symbol(libraryNickname=None, entryName=name, unitId=0, styleId=1)
    body.graphicItems.append(SyRect(
        start=Position(-half_width, half_h), end=Position(half_width, -half_h),
        stroke=Stroke(width=0.254, type="default"),
        fill=None))
    from kiutils.items.common import Fill
    body.graphicItems[0].fill = Fill(type="background")

    unit = Symbol(libraryNickname=None, entryName=name, unitId=1, styleId=1)

    def add_side(pin_list, side):
        n = len(pin_list)
        for i, (num, nm, et) in enumerate(pin_list):
            if side in ("L", "R"):
                y = (n - 1) / 2 * PITCH - i * PITCH
                if side == "L":
                    pos = Position(-half_width - PITCH, y, 0)
                else:
                    pos = Position(half_width + PITCH, y, 180)
            else:
                x = -(n - 1) / 2 * PITCH + i * PITCH
                if side == "T":
                    pos = Position(x, half_h + PITCH, 270)
                else:
                    pos = Position(x, -half_h - PITCH, 90)
            unit.pins.append(SymbolPin(
                electricalType=et, graphicalStyle="line", position=pos,
                length=PITCH, name=nm, number=str(num),
                nameEffects=_eff(), numberEffects=_eff()))

    add_side(left, "L")
    add_side(right, "R")
    add_side(top, "T")
    add_side(bottom, "B")

    sym.units = [body, unit]
    # lib_symbol properties in the 20230121 schematic format carry no `id`
    for p in sym.properties:
        p.id = None
    return sym


# --------------------------------------------------------------------------
# Board builder
# --------------------------------------------------------------------------
class Placed:
    __slots__ = ("board", "lib_id", "ref", "pos")

    def __init__(self, board, lib_id, ref, pos):
        self.board = board
        self.lib_id = lib_id
        self.ref = ref
        self.pos = pos

    def pin(self, number):
        return self.board._pin_abs(self, str(number))


class Board:
    def __init__(self, project_name):
        self.project = project_name
        self.sch = Schematic.create_new()
        # kiutils emits KiCad-7-era structure (per-symbol `instances` blocks) but
        # defaults the version token to 20211014 (KiCad 6, which stored instances
        # in a top-level block). Stamp the version that matches the structure so
        # KiCad 9/10 reads the per-symbol instances and keeps annotations.
        self.sch.version = "20230121"
        self.sch.generator = "eeschema"
        self.sch.uuid = uid()
        self.sheet_path = "/" + self.sch.uuid
        self._embedded = {}          # lib_id -> Symbol
        self._pinmaps = {}           # lib_id -> {number: (lx, ly, angle)}

    # ---- symbol embedding ----------------------------------------------
    def _register(self, sym):
        lib_id = f"{sym.libraryNickname}:{sym.entryName}"
        if lib_id in self._embedded:
            return lib_id
        self._embedded[lib_id] = sym
        self.sch.libSymbols.append(sym)
        pm = {}
        for u in sym.units:
            for p in u.pins:
                pm[p.number] = (p.position.X, p.position.Y, p.position.angle)
        self._pinmaps[lib_id] = pm
        return lib_id

    def embed_custom(self, sym):
        return self._register(sym)

    def embed_stdlib(self, libfile, entry, alias=None):
        """Embed a standard-lib symbol (and its extends-parents) under its own
        library nickname (== libfile stem). Returns the lib_id."""
        nick = libfile.replace(".kicad_sym", "")
        lib = SymbolLib().from_file(f"{SYMDIR}/{libfile}")
        by_name = {s.entryName: s for s in lib.symbols}
        want = entry
        chain = []          # [child, parent, grandparent, ...]
        seen = set()
        while want and want not in seen:
            seen.add(want)
            s = by_name[want]
            chain.append(s)
            want = s.extends
        # A schematic's embedded lib_symbols cannot use `extends` (KiCad flattens
        # inheritance there), so collapse the chain into one self-contained symbol.
        base = copy.deepcopy(chain[-1])          # deepest ancestor holds graphics
        for s in reversed(chain[:-1]):           # apply overrides parent -> child
            for p in s.properties:
                cur = [q for q in base.properties if q.key == p.key]
                if cur:
                    cur[0].value = p.value
                else:
                    base.properties.append(copy.deepcopy(p))
            if s.units:
                base.units = copy.deepcopy(s.units)
            for attr in ("hidePinNumbers", "pinNames", "pinNamesOffset",
                         "pinNamesHide"):
                v = getattr(s, attr, None)
                if v is not None:
                    setattr(base, attr, v)
        base.entryName = entry
        base.libraryNickname = nick
        base.extends = None
        for p in base.properties:
            p.id = None
        for u in base.units:                     # rename units to the child name
            u.libraryNickname = None              # unit names are bare, no nickname
            u.entryName = entry
        return self._register(base)

    # ---- geometry -------------------------------------------------------
    def _pin_abs(self, placed, number):
        lx, ly, _ = self._pinmaps[placed.lib_id][number]
        return (placed.pos[0] + lx, placed.pos[1] - ly)

    def _pin_out(self, placed, number):
        """Outward unit vector (schematic space) for a pin's free end."""
        _, _, ang = self._pinmaps[placed.lib_id][number]
        return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(ang)]

    # ---- placement ------------------------------------------------------
    def place(self, lib_id, ref, value, x, y, footprint="", fields=None,
              unit=1, dnp=False, mirror=None, hide_value=False, ref_dy=None,
              val_dy=None):
        pm = self._pinmaps[lib_id]
        # estimate a body extent for label placement
        xs = [c[0] for c in pm.values()] or [0]
        ys = [c[1] for c in pm.values()] or [0]
        top = max(ys) if ys else 2.54
        bot = min(ys) if ys else -2.54
        rdy = ref_dy if ref_dy is not None else (top + 2.54)
        vdy = val_dy if val_dy is not None else (bot - 2.54)
        s = SchematicSymbol()
        s.libraryNickname, s.entryName = lib_id.split(":", 1)
        s.position = Position(x, y, 0)
        s.uuid = uid()
        s.unit = unit
        s.inBom = True
        s.onBoard = True
        s.dnp = dnp
        s.fieldsAutoplaced = True
        if mirror:
            s.mirror = mirror
        props = [
            Property(key="Reference", value=ref, id=0,
                     position=Position(x, y - rdy, 0), effects=_eff()),
            Property(key="Value", value=value, id=1,
                     position=Position(x, y - vdy, 0),
                     effects=_eff(hide=hide_value)),
            Property(key="Footprint", value=footprint, id=2,
                     position=Position(x, y, 0), effects=_eff(hide=True)),
            Property(key="Datasheet", value="~", id=3,
                     position=Position(x, y, 0), effects=_eff(hide=True)),
        ]
        if fields:
            nid = 4
            for k, v in fields.items():
                props.append(Property(key=k, value=v, id=nid,
                                      position=Position(x, y, 0),
                                      effects=_eff(hide=True)))
                nid += 1
        s.properties = props
        s.instances = [SymbolProjectInstance(
            name=self.project,
            paths=[SymbolProjectPath(sheetInstancePath=self.sheet_path,
                                     reference=ref, unit=unit)])]
        self.sch.schematicSymbols.append(s)
        return Placed(self, lib_id, ref, (x, y))

    # ---- primitives -----------------------------------------------------
    def wire(self, p1, p2):
        self.sch.graphicalItems.append(Connection(
            type="wire",
            points=[Position(round(p1[0], 4), round(p1[1], 4)),
                    Position(round(p2[0], 4), round(p2[1], 4))],
            uuid=uid()))

    def junction(self, p):
        self.sch.junctions.append(Junction(position=Position(p[0], p[1]), uuid=uid()))

    def no_connect(self, p):
        self.sch.noConnects.append(NoConnect(position=Position(p[0], p[1]), uuid=uid()))

    def label(self, p, text, angle=0):
        self.sch.labels.append(LocalLabel(
            text=text, position=Position(p[0], p[1], angle),
            effects=_eff(justify="left"), uuid=uid()))

    def text_note(self, p, text, size=1.27):
        from kiutils.items.schitems import Text
        self.sch.texts.append(Text(text=text, position=Position(p[0], p[1], 0),
                                   effects=_eff(size=size, justify="left"), uuid=uid()))

    # ---- high level connections ----------------------------------------
    _STUB = 2.54

    def net(self, placed, number, name):
        """Attach a signal pin to a named net via a stub + local label."""
        end = placed.pin(number)
        ox, oy = self._pin_out(placed, number)
        lend = (round(end[0] + ox * self._STUB, 4), round(end[1] + oy * self._STUB, 4))
        self.wire(end, lend)
        lang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[(ox, oy)]
        self.label(lend, name, lang)
        return lend

    def to_power(self, placed, number, kind):
        """Drop a power port (kind = GND/+3V3/+5V/VBUS) on a pin via a stub."""
        lib_id = self._power_ids[kind]
        end = placed.pin(number)
        ox, oy = self._pin_out(placed, number)
        pend = (round(end[0] + ox * self._STUB, 4), round(end[1] + oy * self._STUB, 4))
        self.wire(end, pend)
        # power symbol pin is at local (0,0); place origin so pin lands on pend
        self.place(lib_id, "#PWR", kind, pend[0], pend[1], hide_value=True,
                   ref_dy=0, val_dy=0)
        # give the anonymous power ref a real unique name
        self.sch.schematicSymbols[-1].properties[0].value = f"#PWR{self._pwrn():03d}"
        self.sch.schematicSymbols[-1].properties[0].effects.hide = True
        self.sch.schematicSymbols[-1].instances[0].paths[0].reference = \
            self.sch.schematicSymbols[-1].properties[0].value
        return pend

    def pwr_flag(self, at):
        lib_id = self._power_ids["PWR_FLAG"]
        self.place(lib_id, f"#FLG{self._pwrn():03d}", "PWR_FLAG", at[0], at[1],
                   hide_value=True, ref_dy=0, val_dy=0)
        self.sch.schematicSymbols[-1].properties[0].effects.hide = True

    # ---- power infra ----------------------------------------------------
    _pwr_counter = 0

    def _pwrn(self):
        self._pwr_counter += 1
        return self._pwr_counter

    def setup_power(self, kinds=("GND", "+3V3", "+5V", "VBUS", "PWR_FLAG")):
        self._power_ids = {}
        for k in kinds:
            self._power_ids[k] = self.embed_stdlib("power.kicad_sym", k)

    # ---- output ---------------------------------------------------------
    def save(self, path):
        self.sch.to_file(path)
        # sanity: re-read
        Schematic().from_file(path)
