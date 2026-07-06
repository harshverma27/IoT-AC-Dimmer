#!/usr/bin/env python3
"""Generate hardware/remote/remote.kicad_sch (battery ESP-NOW remote).

Blocks: LiPo battery (JST-PH), TP4056 charge+protect MODULE (charges over its
own USB-C), ME6211 3.3V LDO, ESP32 DevKit (plug-in module, flashed over its own
micro-USB), 3 tactile THT buttons with 100k pull-ups + 100nF debounce
(GPIO39/34/35).

The onboard USB-serial subsystem (CP2102, board USB-C, auto-reset) is gone: the
ESP32 DevKit carries its own USB bridge + micro-USB.  TP4056 is now a module, so
the external charge LEDs and PROG resistor live on that module, not the carrier.

NOTE: a plug-in DevKit's onboard LDO + USB bridge leak in deep sleep, so battery
life is days/weeks rather than the ~4-6 months a bare WROOM would give.  This is
an accepted trade for build/flash simplicity.
"""
import os
import schlib as S
import parts

OUT = os.path.join(os.path.dirname(__file__), "..", "remote", "remote.kicad_sch")

FP = {
    "esp32": "Module:ESP32-DevKitC",
    "jst": "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "tp4056": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "me6211": "Package_TO_SOT_SMD:SOT-23-5",
    "r": "Resistor_SMD:R_0805_2012Metric",
    "c": "Capacitor_SMD:C_0805_2012Metric",
    "cbulk": "Capacitor_SMD:C_1206_3216Metric",
    "btn": "Button_Switch_THT:SW_PUSH_6mm",
}

b = S.Board("remote")
b.setup_power(("GND", "+3V3", "PWR_FLAG"))

res = b.embed_stdlib("Device.kicad_sym", "R")
cap = b.embed_stdlib("Device.kicad_sym", "C")
conn2 = b.embed_stdlib("Connector_Generic.kicad_sym", "Conn_01x02")
swp = b.embed_stdlib("Switch.kicad_sym", "SW_Push")

tp = b.embed_custom(parts.TP4056_module())
me = b.embed_custom(parts.ME6211_33())
esp = b.embed_custom(parts.ESP32_DevKit())


def R(ref, val, x, y):
    return b.place(res, ref, val, x, y, footprint=FP["r"])


def C(ref, val, x, y, fp="c"):
    return b.place(cap, ref, val, x, y, footprint=FP[fp])


# ==========================================================================
# POWER PATH: TP4056 module (USB-C charge) -> LiPo -> ME6211 LDO -> 3V3
# ==========================================================================
b.text_note((10, 18), "=== CHARGE + POWER ===", 2.0)

# TP4056 charge + protection module (charged via its own USB-C)
U1 = b.place(tp, "U1", "TP4056-Module", 60, 60, footprint=FP["tp4056"])
b.no_connect(U1.pin("1"))       # IN+  (module has its own USB-C)
b.no_connect(U1.pin("2"))       # IN-
b.net(U1, "3", "VBAT")          # B+  -> LiPo +
b.net(U1, "4", "BATT_N")        # B-  -> LiPo - (through module protection FETs)
b.net(U1, "5", "VSYS")          # OUT+ -> protected system rail
b.to_power(U1, "6", "GND")      # OUT- -> logic ground

# Battery connector (JST-PH, LiPo 500mAh)
BT1 = b.place(conn2, "BT1", "LiPo_500mAh", 60, 115, footprint=FP["jst"])
b.net(BT1, "1", "VBAT")
b.net(BT1, "2", "BATT_N")

# ME6211 LDO 3V3 (VSYS ~3.7V -> clean 3.3V)
U2 = b.place(me, "U2", "ME6211C33M5G", 150, 90, footprint=FP["me6211"])
b.net(U2, "1", "VSYS")          # VIN
b.to_power(U2, "2", "GND")
b.net(U2, "3", "VSYS")          # EN tied to VIN (always on)
b.to_power(U2, "5", "+3V3")
b.no_connect(U2.pin("4"))
b.pwr_flag(b.to_power(U2, "5", "+3V3"))
Cin = C("C2", "1uF", 135, 115)
b.net(Cin, "1", "VSYS")
b.to_power(Cin, "2", "GND")
Cout = C("C3", "1uF", 165, 115)
b.to_power(Cout, "1", "+3V3")
b.to_power(Cout, "2", "GND")

# ==========================================================================
# MCU - ESP32 DevKit (deep sleep, ext1 wake) + BUTTONS
# ==========================================================================
b.text_note((205, 40), "=== ESP32 DevKit (flash over micro-USB) ===", 2.0)
U3 = b.place(esp, "U3", "ESP32-DevKitC-30", 250, 110, footprint=FP["esp32"])
b.to_power(U3, "30", "+3V3")    # 3V3 pin fed from ME6211 (bypasses onboard LDO)
b.to_power(U3, "13", "GND")
b.to_power(U3, "16", "GND")
# button inputs on RTC GPIOs (ext1 wake sources)
b.net(U3, "3", "BTN_UP")        # IO39 / SENSOR_VN
b.net(U3, "4", "BTN_DOWN")      # IO34
b.net(U3, "5", "BTN_ONOFF")     # IO35
# unused DevKit header pins
for p in ("1", "2", "6", "7", "8", "9", "10", "11", "12", "14", "15",
          "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27",
          "28", "29"):
    b.no_connect(U3.pin(p))

# 3V3 rail decoupling / bulk (the DevKit also carries its own decoupling)
c4 = C("C4", "10uF", 212, 150, fp="cbulk")
b.to_power(c4, "1", "+3V3")
b.to_power(c4, "2", "GND")
c5 = C("C5", "100nF", 222, 150)
b.to_power(c5, "1", "+3V3")
b.to_power(c5, "2", "GND")

# ---- Buttons: 6mm THT tactile, 100k pull-up + 100nF debounce ---------------
b.text_note((150, 155), "Buttons: 6mm THT tactile, 100k pull-up (low sleep leakage) + 100nF debounce", 1.4)
btns = [("SW1", "UP", "BTN_UP", 150, 185),
        ("SW2", "DOWN", "BTN_DOWN", 175, 185),
        ("SW3", "ON/OFF", "BTN_ONOFF", 200, 185)]
pu_idx = 4
db_idx = 6
for ref, label, net, x, y in btns:
    sw = b.place(swp, ref, label, x, y, footprint=FP["btn"])
    b.net(sw, "1", net)
    b.to_power(sw, "2", "GND")
    rp = R(f"R{pu_idx}", "100k", x, y - 22)
    b.net(rp, "2", net)
    b.to_power(rp, "1", "+3V3")
    cd = C(f"C{db_idx}", "100nF", x + 10, y)
    b.net(cd, "1", net)
    b.to_power(cd, "2", "GND")
    pu_idx += 1
    db_idx += 1

b.text_note((150, 210),
            "Flash: plug micro-USB into the ESP32 DevKit (onboard CP2102 + auto-reset + BOOT/EN).",
            1.4)

b.save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT))
print("symbols:", len(b.sch.schematicSymbols),
      "labels:", len(b.sch.labels),
      "wires:", len(b.sch.graphicalItems),
      "no-connects:", len(b.sch.noConnects))
