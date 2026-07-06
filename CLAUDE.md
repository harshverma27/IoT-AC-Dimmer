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
hardware/dimmer/   KiCad 10 project — mains dimmer (blank, needs capture)
hardware/remote/   KiCad 10 project — battery remote (blank, needs capture)
```

Tooling: KiCad 10 for schematic/layout authoring. **kicad-happy** plugin
(analysis/BOM/fab/docs only — not an authoring tool) for review, BOM, DRC,
EMC, JLCPCB export. Schematic capture is still empty — populate next.

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
| MCU | ESP32-WROOM-32 | Core 0: phase timing (`hw_timer_t` ISR). Core 1: WiFi/ESP-NOW/MQTT |
| PSU | HLK-PM03 | 230V→3.3V/900mA isolated. **No LDO** — direct 3.3V |
| AC in/out | MKDSN 5.08mm screw terminals | Live + Neutral |
| ZC detect | TLP281-4 + R1 10kΩ + D1 1N4007 + R2 10kΩ pull-up | 3.3V pulses → GPIO34 |
| Gate drive | MOC3021 + R3 330Ω | Opto TRIAC trigger from GPIO25 |
| Power switch | BT138-600 TRIAC + R4 470Ω gate + R5+C5 snubber | ~2000W max (12A) |
| Programming | CP2102 USB-Serial + USB-C + auto-reset | No external programmer |

Dimmer GPIO map:
- **GPIO34** — ZC detect input. Input-only RTC GPIO, **no internal pull-up**,
  needs external 10kΩ to 3.3V.
- **GPIO25** — TRIAC gate out (MOC3021 LED via R3). `hw_timer_t` fires 100µs pulse.

## Remote board

| Block | Part | Notes |
|-------|------|-------|
| Battery | LiPo 500mAh 3.7V, JST-PH | rechargeable |
| Charger | TP4056 | USB-C → LiPo 1A |
| LDO | ME6211 3.3V SOT-23-5 | 3.7V → clean 3.3V |
| MCU | ESP32-WROOM-32 | deep sleep, ext1 button wakeup, ESP-NOW TX |
| Buttons | 3x tactile 6x6mm + 100kΩ pull-up + 100nF debounce | UP / DOWN / ON-OFF |
| Programming | CP2102 USB-Serial + USB-C | |

Remote GPIO map (all input-only RTC GPIOs, ext1 wakeup, external 100kΩ pull-up):
- **GPIO39** — BTN UP
- **GPIO34** — BTN DOWN
- **GPIO35** — BTN ON/OFF

Use **100kΩ** pull-ups (not 10kΩ) to minimize deep-sleep leakage.
Only RTC GPIOs survive deep sleep for `esp_sleep_enable_ext1_wakeup()`.
Target sleep current ~5µA → ~4-6 month battery life.

## Firmware notes

- Dimmer: hardware timer ISR on Core 0 sets TRIAC fire delay after each zero
  crossing (phase-angle control). Networking stays on Core 1.
- Remote: wake on button (ext1), send ESP-NOW packet, sleep.
- Future: MQTT over WiFi + OTA (dimmer); BLE + display (remote).

## Conventions

- ESP-NOW is the primary link between boards. Dimmer also joins WiFi.
- When editing hardware, keep this file's part list in sync with the spec doc.
