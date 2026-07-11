# IoT AC Dimmer

ESP32-based wireless phase-angle AC dimmer. Two PCBs linked over ESP-NOW:
a mains-side dimmer board that switches a TRIAC, and a battery-powered
remote with three buttons. Source spec: `IoT AC Dimmer Project.docx`
(v2.0, March 2026).

## What's in this repo

- **Dimmer board** (`hardware/dimmer/`) — 230V mains input, zero-cross
  detection, phase-angle TRIAC control (up to ~2000W / 12A), ESP32 DevKit V1
  running ESP-NOW RX + WiFi.
- **Remote board** (`hardware/remote/`) — LiPo-powered, 3 tactile buttons
  (UP / DOWN / ON-OFF), ESP32 DevKit V1 in deep sleep, ESP-NOW TX only.
- **Generator scripts** (`hardware/tools/`) — Python scripts (on top of
  `kiutils`) that bootstrapped the schematic captures for both boards, so
  the design is reproducible and diffable.

Both boards are designed in KiCad 10. Schematics for both boards are
captured and validated against a `kicad-cli`-exported netlist. PCB layout
is in progress (remote board has a first-pass placement + routing; dimmer
board layout is next).

## Repo layout

```
hardware/
  dimmer/     KiCad project — mains dimmer board (schematic + PCB)
  remote/     KiCad project — battery remote board (schematic + PCB)
  tools/      Python scripts that generated the schematic captures
IoT AC Dimmer Project.docx   Design spec (source of truth for requirements)
CLAUDE.md                    Detailed design notes, GPIO maps, part list
```

See `hardware/README.md`, `hardware/tools/README.md`, and `CLAUDE.md` for
full detail — part lists, GPIO pin maps, and design rationale.

## ⚠️ Safety notice

The dimmer board connects directly to 230V AC mains. It uses an opto-isolated
zero-cross detector (TLP281-4) and an opto-isolated TRIAC driver (MOC3021)
to keep mains-side and logic-side circuitry galvanically isolated, with a
routed FR4 isolation slot under both optoisolators. Do not bridge that
isolation slot with copper or traces, and do not power the dimmer board from
mains and USB at the same time. If you build this, treat it as a mains-voltage
project: use proper enclosures, creepage/clearance spacing, and fusing, and
follow your local electrical code. Build and use at your own risk.

## Hardware overview

### Dimmer board

| Block | Part | Notes |
|-------|------|-------|
| MCU | ESP32 DevKit V1 (30-pin plug-in module) | Core 0: phase timing ISR. Core 1: WiFi/ESP-NOW/MQTT |
| PSU | HLK-PM03 | Isolated 230V→3.3V/900mA, feeds DevKit 3V3 directly (no LDO) |
| AC in/out | MKDSN 5.08mm screw terminals | Live + Neutral |
| Zero-cross detect | TLP281-4 opto + 1N4007 + resistors | 3.3V pulses into GPIO34 |
| Gate drive | MOC3021 opto + resistor | Drives TRIAC gate from GPIO25 |
| Power switch | BT138-600 TRIAC + gate resistor + RC snubber | ~2000W max (12A) |
| Programming | Onboard CP2102 + micro-USB on the DevKit itself | No separate USB circuitry on the carrier board |

### Remote board

| Block | Part | Notes |
|-------|------|-------|
| Battery | LiPo 500mAh 3.7V, JST-PH | Rechargeable |
| Charger | TP4056 charge/protect module (USB-C) | Handles charging, protection, and status LEDs |
| LDO | ME6211 3.3V SOT-23-5 | Regulates battery voltage down to clean 3.3V |
| MCU | ESP32 DevKit V1 (30-pin plug-in module) | ext1 button wakeup, ESP-NOW TX, deep sleep between presses |
| Buttons | 3× 6×6mm tactile THT, pull-up + debounce RC | UP / DOWN / ON-OFF |

Full GPIO maps, exact part numbers, and design rationale (including the
plug-in-DevKit battery-life tradeoff on the remote) live in `CLAUDE.md`.

## Getting started

Requires KiCad 10.

```bash
kicad hardware/dimmer/dimmer.kicad_pro
kicad hardware/remote/remote.kicad_pro
```

The `.kicad_sch` files are KiCad-7 format; KiCad 10 opens and upgrades them
automatically. Don't hand-edit the format version token — see
`hardware/tools/README.md` for why.

To regenerate a schematic capture from the Python generators:

```bash
cd hardware/tools
pip install kiutils
python3 gen_dimmer.py
python3 gen_remote.py
python3 validate.py ../dimmer/dimmer.kicad_sch ../remote/remote.kicad_sch
```

## Status

- Schematics: captured and validated for both boards.
- PCB layout: remote board has first-pass placement/routing; dimmer board
  layout not yet started.
- Firmware: not yet in this repo.

## Firmware plan (not yet implemented)

- Dimmer: hardware timer ISR on Core 0 sets TRIAC fire delay after each
  zero crossing (phase-angle dimming). Networking (WiFi/ESP-NOW/MQTT)
  stays on Core 1.
- Remote: wake on button press (`ext1`), send an ESP-NOW packet, go back
  to deep sleep.
- Future: MQTT + OTA on the dimmer; BLE + display on the remote.
