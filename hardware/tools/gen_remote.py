#!/usr/bin/env python3
"""Generate hardware/remote/remote.kicad_sch (battery ESP-NOW remote).

Blocks: LiPo battery (JST-PH), TP4056 USB-C charger, ME6211 3.3V LDO,
ESP32-WROOM-32 (deep-sleep, ext1 button wake), 3 tactile buttons with 100k
pull-ups + 100nF debounce (GPIO39/34/35), CP2102 USB-serial + auto-reset.
"""
import os
import schlib as S
import parts

OUT = os.path.join(os.path.dirname(__file__), "..", "remote", "remote.kicad_sch")

FP = {
    "esp32": "RF_Module:ESP32-WROOM-32",
    "jst": "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "tp4056": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "me6211": "Package_TO_SOT_SMD:SOT-23-5",
    "cp2102": "Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm",
    "usbc": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "sot23": "Package_TO_SOT_SMD:SOT-23",
    "r": "Resistor_SMD:R_0805_2012Metric",
    "c": "Capacitor_SMD:C_0805_2012Metric",
    "cbulk": "Capacitor_SMD:C_1206_3216Metric",
    "led": "LED_SMD:LED_0805_2012Metric",
    "btn": "Button_Switch_SMD:SW_SPST_PTS645",
}

b = S.Board("remote")
b.setup_power(("GND", "+3V3", "+5V", "PWR_FLAG"))

esp = b.embed_stdlib("RF_Module.kicad_sym", "ESP32-WROOM-32")
res = b.embed_stdlib("Device.kicad_sym", "R")
cap = b.embed_stdlib("Device.kicad_sym", "C")
led = b.embed_stdlib("Device.kicad_sym", "LED")
conn2 = b.embed_stdlib("Connector_Generic.kicad_sym", "Conn_01x02")
usbc = b.embed_stdlib("Connector.kicad_sym", "USB_C_Receptacle_USB2.0_16P")
npn = b.embed_stdlib("Transistor_BJT.kicad_sym", "MMBT3904")
swp = b.embed_stdlib("Switch.kicad_sym", "SW_Push")

tp = b.embed_custom(parts.TP4056())
me = b.embed_custom(parts.ME6211_33())
cp = b.embed_custom(parts.CP2102())


def R(ref, val, x, y):
    return b.place(res, ref, val, x, y, footprint=FP["r"])


def C(ref, val, x, y, fp="c"):
    return b.place(cap, ref, val, x, y, footprint=FP[fp])


# ==========================================================================
# POWER PATH: USB-C -> TP4056 charger -> LiPo -> ME6211 LDO -> 3V3
# ==========================================================================
b.text_note((10, 18), "=== CHARGE + POWER ===", 2.0)

# USB-C
J1 = b.place(usbc, "J1", "USB-C", 20, 60, footprint=FP["usbc"])
for p in ("A4", "B4", "A9", "B9"):
    b.to_power(J1, p, "+5V")
for p in ("A1", "B1", "A12", "B12", "S1"):
    b.to_power(J1, p, "GND")
b.net(J1, "A6", "USB_DP")
b.net(J1, "B6", "USB_DP")
b.net(J1, "A7", "USB_DM")
b.net(J1, "B7", "USB_DM")
b.net(J1, "A5", "CC1")
b.net(J1, "B5", "CC2")
b.no_connect(J1.pin("A8"))
b.no_connect(J1.pin("B8"))
Rc1 = R("R10", "5.1k", 35, 95)
b.net(Rc1, "1", "CC1")
b.to_power(Rc1, "2", "GND")
Rc2 = R("R11", "5.1k", 45, 95)
b.net(Rc2, "1", "CC2")
b.to_power(Rc2, "2", "GND")
b.pwr_flag(b.to_power(J1, "A4", "+5V"))

# TP4056 charger
U1 = b.place(tp, "U1", "TP4056", 80, 55, footprint=FP["tp4056"])
b.to_power(U1, "4", "+5V")     # VCC from USB
b.net(U1, "5", "VBAT")         # BAT
b.to_power(U1, "3", "GND")
b.to_power(U1, "8", "+5V")     # CE enable
b.to_power(U1, "1", "GND")     # TEMP disabled (tie to GND)
R1 = R("R1", "1.2k", 62, 70)   # PROG -> GND sets ~1A charge current
b.net(U1, "2", "PROG")
b.net(R1, "1", "PROG")
b.to_power(R1, "2", "GND")
# charge status LEDs (open-drain, sink to /CHRG, /STDBY)
LED1 = b.place(led, "LED1", "CHRG", 110, 45, footprint=FP["led"])
R2 = R("R2", "1k", 110, 35)
b.to_power(R2, "1", "+5V")
b.net(R2, "2", "LED_CHRG_A")
b.net(LED1, "2", "LED_CHRG_A")   # anode
b.net(LED1, "1", "CHRG_N")       # cathode -> /CHRG
b.net(U1, "7", "CHRG_N")
LED2 = b.place(led, "LED2", "FULL", 125, 45, footprint=FP["led"])
R3 = R("R3", "1k", 125, 35)
b.to_power(R3, "1", "+5V")
b.net(R3, "2", "LED_STBY_A")
b.net(LED2, "2", "LED_STBY_A")
b.net(LED2, "1", "STBY_N")
b.net(U1, "6", "STBY_N")

# Battery connector (JST-PH, LiPo 500mAh)
BT1 = b.place(conn2, "BT1", "LiPo_500mAh", 80, 110, footprint=FP["jst"])
b.net(BT1, "1", "VBAT")
b.to_power(BT1, "2", "GND")

# ME6211 LDO 3V3
U2 = b.place(me, "U2", "ME6211C33M5G", 150, 90, footprint=FP["me6211"])
b.net(U2, "1", "VBAT")
b.to_power(U2, "2", "GND")
b.net(U2, "3", "VBAT")         # EN tied to VIN (always on)
b.to_power(U2, "5", "+3V3")
b.no_connect(U2.pin("4"))
b.pwr_flag(b.to_power(U2, "5", "+3V3"))
Cin = C("C2", "1uF", 135, 115)
b.net(Cin, "1", "VBAT")
b.to_power(Cin, "2", "GND")
Cout = C("C3", "1uF", 165, 115)
b.to_power(Cout, "1", "+3V3")
b.to_power(Cout, "2", "GND")

# ==========================================================================
# MCU + BUTTONS
# ==========================================================================
b.text_note((205, 40), "=== MCU (deep sleep, ext1 wake) ===", 2.0)
U3 = b.place(esp, "U3", "ESP32-WROOM-32", 240, 110, footprint=FP["esp32"])
for g in ("1", "15", "38", "39"):
    b.to_power(U3, g, "GND")
b.to_power(U3, "2", "+3V3")
b.net(U3, "3", "EN")
b.net(U3, "25", "BOOT")        # IO0
b.net(U3, "34", "U0RXD")       # RXD0/IO3
b.net(U3, "35", "U0TXD")       # TXD0/IO1
# button inputs on RTC GPIOs
b.net(U3, "5", "BTN_UP")       # SENSOR_VN = GPIO39
b.net(U3, "6", "BTN_DOWN")     # IO34 = GPIO34
b.net(U3, "7", "BTN_ONOFF")    # IO35 = GPIO35
for p in ("17", "18", "19", "20", "21", "22", "32"):
    b.no_connect(U3.pin(p))

# EN / BOOT support
R7 = R("R7", "10k", 210, 70)
b.net(R7, "2", "EN")
b.to_power(R7, "1", "+3V3")
C9 = C("C9", "100nF", 200, 78)
b.net(C9, "1", "EN")
b.to_power(C9, "2", "GND")
R8 = R("R8", "10k", 275, 70)
b.net(R8, "2", "BOOT")
b.to_power(R8, "1", "+3V3")

# ESP32 decoupling
c4 = C("C4", "10uF", 212, 150, fp="cbulk")
b.to_power(c4, "1", "+3V3")
b.to_power(c4, "2", "GND")
c5 = C("C5", "100nF", 222, 150)
b.to_power(c5, "1", "+3V3")
b.to_power(c5, "2", "GND")

# ---- Buttons: 100k pull-up (low deep-sleep leakage) + 100nF debounce -------
b.text_note((150, 155), "Buttons: 100k pull-up (low sleep leakage) + 100nF debounce", 1.4)
btns = [("SW1", "UP", "BTN_UP", 150, 175),
        ("SW2", "DOWN", "BTN_DOWN", 175, 175),
        ("SW3", "ON/OFF", "BTN_ONOFF", 200, 175)]
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

# ==========================================================================
# USB-SERIAL (programming) + auto-reset
# ==========================================================================
b.text_note((25, 130), "USB-Serial + auto-reset", 1.5)
U4 = b.place(cp, "U4", "CP2102", 45, 155, footprint=FP["cp2102"])
b.to_power(U4, "8", "+5V")
b.to_power(U4, "7", "+5V")
b.net(U4, "6", "V3V3_USB")
b.to_power(U4, "3", "GND")
b.net(U4, "4", "USB_DP")
b.net(U4, "5", "USB_DM")
b.net(U4, "9", "CP_RST")
b.net(U4, "26", "U0RXD")
b.net(U4, "25", "U0TXD")
b.net(U4, "24", "RTS")
b.net(U4, "27", "DTR")
for p in ("23", "28", "1", "2"):
    b.no_connect(U4.pin(p))
for p in range(10, 23):
    b.no_connect(U4.pin(str(p)))
C10 = C("C10", "1uF", 27, 195)
b.net(C10, "1", "+5V")
b.to_power(C10, "2", "GND")
C11 = C("C11", "100nF", 63, 195)
b.net(C11, "1", "V3V3_USB")
b.to_power(C11, "2", "GND")
R9 = R("R9", "10k", 27, 130)
b.net(R9, "1", "CP_RST")
b.net(R9, "2", "V3V3_USB")

Q1 = b.place(npn, "Q1", "MMBT3904", 15, 180, footprint=FP["sot23"])
b.net(Q1, "1", "DTR")
b.net(Q1, "3", "EN")
b.net(Q1, "2", "RTS")
Q2 = b.place(npn, "Q2", "MMBT3904", 90, 180, footprint=FP["sot23"])
b.net(Q2, "1", "RTS")
b.net(Q2, "3", "BOOT")
b.net(Q2, "2", "DTR")

b.text_note((150, 205),
            "Target deep-sleep current ~5uA -> ~4-6 month battery life",
            1.4)

b.save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT))
print("symbols:", len(b.sch.schematicSymbols),
      "labels:", len(b.sch.labels),
      "wires:", len(b.sch.graphicalItems),
      "no-connects:", len(b.sch.noConnects))
