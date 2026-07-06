# IoT AC Dimmer — Project Memory

ESP32 phase-angle AC dimmer. Two boards, ESP-NOW wireless link.
Source spec: `IoT AC Dimmer Project.docx` (v2.0, March 2026, by Harsh).

## Goal of this repo

Design + fabricate the **two PCBs** described in the spec (KiCad). This repo
holds the hardware design (schematics, layout, gerbers) and firmware.

- **Dimmer board** — mains-side, phase-angle TRIAC control, ESP-NOW RX + WiFi.
- **Remote board** — battery, 3 buttons, ESP-NOW TX only, deep sleep.

## Repo layout

```
hardware/dimmer/   KiCad project — mains dimmer (schematic captured; PCB TODO)
hardware/remote/   KiCad project — battery remote (schematic captured; PCB TODO)
hardware/tools/    Python generators that bootstrapped the schematic capture
```

Tooling: KiCad 10 for schematic/layout authoring. **kicad-happy** plugin
(analysis/BOM/fab/docs only — not an authoring tool) for review, BOM, DRC,
EMC, JLCPCB export. **Schematics are captured** for both boards (validated via
`kicad-cli` netlist export); PCB layout is the next phase. The `.kicad_sch`
files are KiCad-7 format (`20230121`) — KiCad 10 opens and upgrades them.

## ⚠️ Safety — dimmer board is on 230V mains

Non-negotiable design rules:
- **Galvanic isolation slot**: routed FR4 cutout under TLP281-4 (ZC detect) and
  MOC3021 (gate drive). Keep the isolation barrier unbroken — no copper, no
  traces cross the slot.
- Red rails in spec = 230V AC. Green dashed = 3.3V bus. Keep mains creepage/
  clearance generous; respect the barrier.
- HLK-PM03 is isolated 230V→3.3V. Its output ground is the logic ground.

## Dimmer board

| Block | Part | Notes |
|-------|------|-------|
| MCU | ESP32 DevKit V1 (30-pin plug-in module) | Core 0: phase timing (`hw_timer_t` ISR). Core 1: WiFi/ESP-NOW/MQTT. Seats on 2×1×15 female headers |
| PSU | HLK-PM03 | 230V→3.3V/900mA isolated. **No LDO** — direct 3.3V into DevKit 3V3 pin |
| AC in/out | MKDSN 5.08mm screw terminals | Live + Neutral |
| ZC detect | TLP281-4 + R1 10kΩ + D1 1N4007 + R2 10kΩ pull-up | 3.3V pulses → GPIO34 |
| Gate drive | MOC3021 + R3 330Ω | Opto TRIAC trigger from GPIO25 |
| Power switch | BT138-600 TRIAC + R4 470Ω gate + R5+C5 snubber | ~2000W max (12A) |
| Programming | **On the DevKit** (onboard CP2102 + micro-USB + auto-reset + BOOT/EN) | No CP2102/USB-C on the carrier. Don't power mains + USB together |

Dimmer GPIO map:
- **GPIO34** — ZC detect input. Input-only RTC GPIO, **no internal pull-up**,
  needs external 10kΩ to 3.3V.
- **GPIO25** — TRIAC gate out (MOC3021 LED via R3). `hw_timer_t` fires 100µs pulse.

## Remote board

| Block | Part | Notes |
|-------|------|-------|
| Battery | LiPo 500mAh 3.7V, JST-PH | rechargeable |
| Charger | TP4056 charge+protect **module** (Type-C) | Charges via the module's own USB-C. B+/B-→LiPo, OUT+/OUT-→system. DW01 protection + PROG resistor + charge LEDs are onboard the module |
| LDO | ME6211 3.3V SOT-23-5 | VSYS (OUT+) 3.7V → clean 3.3V into DevKit 3V3 pin |
| MCU | ESP32 DevKit V1 (30-pin plug-in module) | ext1 button wakeup, ESP-NOW TX. Flashed over the DevKit's own micro-USB |
| Buttons | 3× tactile 6×6mm **THT** + 100kΩ pull-up + 100nF debounce | UP / DOWN / ON-OFF |

⚠️ **Battery-life caveat:** the plug-in DevKit's onboard LDO + USB bridge leak in
deep sleep, so runtime is days/weeks, not the ~4–6 months a bare WROOM would give
(traded away for build/flash simplicity — chosen deliberately).

Remote GPIO map (all input-only RTC GPIOs, ext1 wakeup, external 100kΩ pull-up):
- **GPIO39** — BTN UP
- **GPIO34** — BTN DOWN
- **GPIO35** — BTN ON/OFF

Use **100kΩ** pull-ups (not 10kΩ) to minimize deep-sleep leakage.
Only RTC GPIOs survive deep sleep for `esp_sleep_enable_ext1_wakeup()`.
The bare-WROOM ~5µA sleep target no longer holds with the plug-in DevKit (see
caveat above); if months-long battery life is needed later, switch the remote
back to a bare ESP32-WROOM-32 + external programming header.

## Firmware notes

- Dimmer: hardware timer ISR on Core 0 sets TRIAC fire delay after each zero
  crossing (phase-angle control). Networking stays on Core 1.
- Remote: wake on button (ext1), send ESP-NOW packet, sleep.
- Future: MQTT over WiFi + OTA (dimmer); BLE + display (remote).

## Conventions

- ESP-NOW is the primary link between boards. Dimmer also joins WiFi.
- When editing hardware, keep this file's part list in sync with the spec doc.
