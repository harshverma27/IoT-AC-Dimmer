# Hardware

Two KiCad 10 boards. See root `CLAUDE.md` for the full design spec.

| Dir | Board | Notes |
|-----|-------|-------|
| `dimmer/` | Mains-side AC dimmer | 230V, TRIAC phase control, ESP-NOW RX + WiFi. **Isolation slot required.** |
| `remote/` | Battery remote | LiPo, 3 buttons, ESP-NOW TX, deep sleep |

Each dir holds `*.kicad_pro` / `*.kicad_sch` / `*.kicad_pcb`.

## Status
- **Schematics: captured** for both boards (`dimmer.kicad_sch`, `remote.kicad_sch`).
  Validated by `kicad-cli` netlist export — every functional net matches intent.
- **PCB layout: not started** (`*.kicad_pcb` still blank) — next phase.

The capture was bootstrapped by the scripts in `tools/` (see `tools/README.md`);
the `.kicad_sch` files are the source of truth.

| Board | Parts placed | Key nets |
|-------|-------------|----------|
| dimmer | 31 | mains L/N/L_OUT, ZC detect → GPIO34, gate drive → GPIO25, +3V3/+5V, USB/UART, auto-reset |
| remote | 34 | VBUS/VBAT/+3V3 power path, BTN_UP/DOWN/ONOFF (GPIO39/34/35), USB/UART, auto-reset |

## Workflow
- Open a board: `kicad hardware/dimmer/dimmer.kicad_pro`
  (schematics are KiCad-7 format `20230121`; KiCad 9/10 opens and upgrades them).
- Next: assign/refine footprints, then lay out the PCB — remember the **isolation
  slot** under U2/U3 on the dimmer.
- Analysis / review / BOM / fab: use the **kicad-happy** skills (kicad, bom, jlcpcb, emc…).
