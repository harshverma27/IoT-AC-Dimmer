# Hardware

Two KiCad 10 boards. See root `CLAUDE.md` for the full design spec.

| Dir | Board | Notes |
|-----|-------|-------|
| `dimmer/` | Mains-side AC dimmer | 230V, TRIAC phase control, ESP-NOW RX + WiFi. **Isolation slot required.** |
| `remote/` | Battery remote | LiPo, 3 buttons, ESP-NOW TX, deep sleep |

Each dir holds `*.kicad_pro` / `*.kicad_sch` / `*.kicad_pcb` (schematics + layout
currently empty — populate next).

## Workflow
- Open a board: `kicad hardware/dimmer/dimmer.kicad_pro`
- Analysis / review / BOM / fab: use the **kicad-happy** skills (kicad, bom, jlcpcb, emc…).
