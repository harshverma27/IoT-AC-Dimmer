# Schematic capture generator

Scripts that generated the initial schematic capture for both boards. The
`.kicad_sch` files are the source of truth — these scripts just bootstrapped
them so the capture is reproducible and reviewable in a diff.

| File | Purpose |
|------|---------|
| `schlib.py` | Thin KiCad-schematic builder on top of [`kiutils`](https://pypi.org/project/kiutils/): embeds stdlib symbols, builds custom rectangular symbols, places parts, and wires nets with labels + power ports. |
| `parts.py` | Custom symbols for parts absent from the KiCad standard library (HLK-PM03, TLP281-4, MOC3021, CP2102, ME6211, TP4056), with datasheet-accurate pinouts. |
| `gen_dimmer.py` | Builds `../dimmer/dimmer.kicad_sch`. |
| `gen_remote.py` | Builds `../remote/remote.kicad_sch`. |
| `validate.py` | ERC-lite: rebuilds the netlist from geometry + label names and reports nets / floating pins. |

## Regenerate

```bash
pip install kiutils
# KiCad standard symbol libraries are read from /usr/share/kicad/symbols
python3 gen_dimmer.py
python3 gen_remote.py
python3 validate.py ../dimmer/dimmer.kicad_sch ../remote/remote.kicad_sch
```

## Validation performed

Both schematics were loaded by a real `kicad-cli` (`sch export netlist`) and the
KiCad-computed netlist was cross-checked against the intended connectivity —
every functional net matches. The only unconnected pins are spare ESP32 GPIOs,
which are intentional (fixed-function boards, no breakout header in the spec).

## File format note

The schematics are written in KiCad-7 schematic format (`version 20230121`),
which is what `kiutils` emits. KiCad 9/10 opens them directly and will offer to
save in the newer format. Do not hand-edit the version token — the per-symbol
`instances` blocks require `>= 20230121` to be read correctly.
