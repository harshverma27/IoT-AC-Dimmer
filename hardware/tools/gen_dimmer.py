#!/usr/bin/env python3
"""Generate hardware/dimmer/dimmer.kicad_sch (mains-side AC dimmer).

Blocks: ESP32-WROOM-32 MCU, HLK-PM03 isolated PSU, AC in/out screw terminals,
TLP281-4 zero-cross detect, MOC3021 opto-TRIAC gate drive, BT138-600 TRIAC with
snubber, CP2102 USB-serial + USB-C + auto-reset.  Connectivity is expressed with
net labels (signals) and power ports (rails); mains nets are prefixed AC_.
"""
import os
import schlib as S
import parts

OUT = os.path.join(os.path.dirname(__file__), "..", "dimmer", "dimmer.kicad_sch")

FP = {
    "esp32": "RF_Module:ESP32-WROOM-32",
    "hlk": "Converter_ACDC:Converter_ACDC_HiLink_HLK-PMxx",
    "term2": "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
    "tlp": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
    "moc": "Package_DIP:DIP-6_W7.62mm",
    "triac": "Package_TO_SOT_THT:TO-220-3_Vertical",
    "r": "Resistor_SMD:R_0805_2012Metric",
    "rmains": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "c": "Capacitor_SMD:C_0805_2012Metric",
    "cbulk": "Capacitor_SMD:C_1206_3216Metric",
    "csnub": "Capacitor_THT:C_Rect_L11.5mm_W5.0mm_P7.50mm_FKS3",
    "d": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "cp2102": "Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm",
    "usbc": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "sot23": "Package_TO_SOT_SMD:SOT-23",
    "sw": "Button_Switch_SMD:SW_SPST_PTS645",
}

b = S.Board("dimmer")
b.setup_power(("GND", "+3V3", "+5V", "PWR_FLAG"))

# ---- embed standard-library symbols --------------------------------------
esp = b.embed_stdlib("RF_Module.kicad_sym", "ESP32-WROOM-32")
res = b.embed_stdlib("Device.kicad_sym", "R")
cap = b.embed_stdlib("Device.kicad_sym", "C")
diode = b.embed_stdlib("Diode.kicad_sym", "1N4007")
triac = b.embed_stdlib("Triac_Thyristor.kicad_sym", "BT138-600")
term = b.embed_stdlib("Connector.kicad_sym", "Screw_Terminal_01x02")
usbc = b.embed_stdlib("Connector.kicad_sym", "USB_C_Receptacle_USB2.0_16P")
npn = b.embed_stdlib("Transistor_BJT.kicad_sym", "MMBT3904")
swp = b.embed_stdlib("Switch.kicad_sym", "SW_Push")

# ---- embed custom symbols ------------------------------------------------
hlk = b.embed_custom(parts.HLK_PM03())
tlp = b.embed_custom(parts.TLP281_4())
moc = b.embed_custom(parts.MOC3021())
cp = b.embed_custom(parts.CP2102())


# ---- convenience placers -------------------------------------------------
def R(ref, val, x, y, fp="r"):
    return b.place(res, ref, val, x, y, footprint=FP[fp])


def C(ref, val, x, y, fp="c"):
    return b.place(cap, ref, val, x, y, footprint=FP[fp])


def decouple(ref, val, x, y, pos_net="+3V3", fp="c"):
    c = C(ref, val, x, y, fp)
    b.to_power(c, "1", pos_net)
    b.to_power(c, "2", "GND")
    return c


# ==========================================================================
# MAINS SIDE (isolated) - left of the board
# ==========================================================================
b.text_note((10, 18), "=== MAINS 230V (ISOLATED) ===", 2.0)

J1 = b.place(term, "J1", "AC_IN_L_N", 25, 40, footprint=FP["term2"])
b.net(J1, "1", "AC_L_IN")
b.net(J1, "2", "AC_N")

J2 = b.place(term, "J2", "AC_OUT_LOAD", 25, 170, footprint=FP["term2"])
b.net(J2, "1", "AC_L_OUT")
b.net(J2, "2", "AC_N")

# Isolated PSU
PS1 = b.place(hlk, "PS1", "HLK-PM03", 60, 40, footprint=FP["hlk"])
b.net(PS1, "1", "AC_L_IN")
b.net(PS1, "2", "AC_N")
b.to_power(PS1, "4", "+3V3")   # +Vo
b.to_power(PS1, "3", "GND")    # -Vo == logic ground
b.pwr_flag(b.to_power(PS1, "4", "+3V3"))  # declare +3V3 driven

# ---- Zero-cross detect (TLP281-4 channel 1) ------------------------------
b.text_note((45, 80), "Zero-cross detect -> GPIO34", 1.5)
U2 = b.place(tlp, "U2", "TLP281-4", 70, 110, footprint=FP["tlp"])
R1 = R("R1", "10k", 45, 95, fp="rmains")
D1 = b.place(diode, "D1", "1N4007", 55, 110, footprint=FP["d"])
R2 = R("R2", "10k", 100, 95)
# mains side of the opto LED
b.net(R1, "1", "AC_L_IN")
b.net(R1, "2", "ZC_LED_A")
b.net(U2, "1", "ZC_LED_A")     # A1
b.net(U2, "2", "AC_N")         # K1 -> neutral (LED cathode returns to neutral)
b.net(D1, "1", "ZC_LED_A")     # cathode -> LED-anode node (anti-parallel clamp)
b.net(D1, "2", "AC_N")         # anode -> neutral
# logic side phototransistor
b.net(U2, "16", "ZC_DET")      # collector
b.to_power(U2, "15", "GND")    # emitter
b.net(R2, "1", "ZC_DET")
b.to_power(R2, "2", "+3V3")    # pull-up (GPIO34 has no internal pull-up)
# unused opto channels 2-4
for p in ("3", "4", "5", "6", "7", "8", "14", "13", "12", "11", "10", "9"):
    b.no_connect(U2.pin(p))

# ---- Gate drive (MOC3021) + TRIAC ----------------------------------------
b.text_note((45, 140), "Opto-TRIAC gate drive <- GPIO25", 1.5)
U3 = b.place(moc, "U3", "MOC3021", 70, 165, footprint=FP["moc"])
R3 = R("R3", "330", 100, 158)
Q1 = b.place(triac, "Q1", "BT138-600", 40, 175, footprint=FP["triac"])
R4 = R("R4", "470", 55, 165)
R5 = R("R5", "47", 25, 195, fp="rmains")
C5 = C("C5", "100nF/X2", 40, 195, fp="csnub")
# opto input LED (logic side)
b.net(R3, "1", "GATE_DRV")
b.net(R3, "2", "MOC_LED_A")
b.net(U3, "1", "MOC_LED_A")    # anode
b.to_power(U3, "2", "GND")     # cathode
# opto output + TRIAC gate (mains side)
b.net(U3, "6", "AC_L_IN")      # MT tied to live (MT2 reference)
b.net(U3, "4", "MOC_MT")
b.net(R4, "1", "MOC_MT")
b.net(R4, "2", "TRIAC_G")
b.no_connect(U3.pin("3"))
b.no_connect(U3.pin("5"))
# TRIAC in series with load
b.net(Q1, "1", "AC_L_OUT")     # A1 / MT1 -> load
b.net(Q1, "2", "AC_L_IN")      # A2 / MT2 -> live
b.net(Q1, "3", "TRIAC_G")
# snubber across MT1-MT2
b.net(R5, "1", "AC_L_IN")
b.net(R5, "2", "SNUB")
b.net(C5, "1", "SNUB")
b.net(C5, "2", "AC_L_OUT")

# ==========================================================================
# LOGIC SIDE
# ==========================================================================
b.text_note((130, 40), "=== LOGIC 3V3 ===", 2.0)

U1 = b.place(esp, "U1", "ESP32-WROOM-32", 160, 110, footprint=FP["esp32"])
for g in ("1", "15", "38", "39"):
    b.to_power(U1, g, "GND")
b.to_power(U1, "2", "+3V3")
b.net(U1, "3", "EN")
b.net(U1, "6", "ZC_DET")        # IO34
b.net(U1, "10", "GATE_DRV")     # IO25
b.net(U1, "34", "U0RXD")        # RXD0/IO3
b.net(U1, "35", "U0TXD")        # TXD0/IO1
b.net(U1, "25", "BOOT")         # IO0
# internal-flash pins: do not connect
for p in ("17", "18", "19", "20", "21", "22", "32"):
    b.no_connect(U1.pin(p))

# strapping / reset support
R6 = R("R6", "10k", 130, 70)
b.net(R6, "2", "EN")
b.to_power(R6, "1", "+3V3")
C3 = C("C3", "100nF", 118, 78)
b.net(C3, "1", "EN")
b.to_power(C3, "2", "GND")
R7 = R("R7", "10k", 195, 70)
b.net(R7, "2", "BOOT")
b.to_power(R7, "1", "+3V3")
SW1 = b.place(swp, "SW1", "BOOT", 205, 150, footprint=FP["sw"])
b.net(SW1, "1", "BOOT")
b.to_power(SW1, "2", "GND")
SW2 = b.place(swp, "SW2", "EN", 118, 150, footprint=FP["sw"])
b.net(SW2, "1", "EN")
b.to_power(SW2, "2", "GND")

# ESP32 decoupling
decouple("C1", "10uF", 132, 145, fp="cbulk")
decouple("C2", "100nF", 142, 145)
decouple("C4", "10uF", 78, 60, fp="cbulk")   # bulk on HLK 3V3 output

# ---- CP2102 USB-serial ----------------------------------------------------
b.text_note((225, 40), "USB-Serial + auto-reset", 1.5)
U4 = b.place(cp, "U4", "CP2102", 250, 110, footprint=FP["cp2102"])
b.to_power(U4, "8", "+5V")     # VBUS
b.to_power(U4, "7", "+5V")     # REGIN
b.net(U4, "6", "V3V3_USB")     # VDD (CP2102 internal LDO output)
b.to_power(U4, "3", "GND")
b.net(U4, "4", "USB_DP")
b.net(U4, "5", "USB_DM")
b.net(U4, "9", "CP_RST")
b.net(U4, "26", "U0RXD")       # CP2102 TXD -> ESP RX
b.net(U4, "25", "U0TXD")       # CP2102 RXD -> ESP TX
b.net(U4, "24", "RTS")
b.net(U4, "27", "DTR")
for p in ("23", "28", "1", "2"):
    b.no_connect(U4.pin(p))
for p in range(10, 23):
    b.no_connect(U4.pin(str(p)))
# CP2102 support parts
C6 = C("C6", "1uF", 232, 150)
b.net(C6, "1", "+5V")
b.to_power(C6, "2", "GND")
C7 = C("C7", "100nF", 268, 150)
b.net(C7, "1", "V3V3_USB")
b.to_power(C7, "2", "GND")
R8 = R("R8", "10k", 232, 78)
b.net(R8, "1", "CP_RST")
b.net(R8, "2", "V3V3_USB")

# auto-reset (classic two-transistor DTR/RTS -> EN/IO0)
Q2 = b.place(npn, "Q2", "MMBT3904", 215, 175, footprint=FP["sot23"])
b.net(Q2, "1", "DTR")          # base
b.net(Q2, "3", "EN")           # collector
b.net(Q2, "2", "RTS")          # emitter
Q3 = b.place(npn, "Q3", "MMBT3904", 240, 175, footprint=FP["sot23"])
b.net(Q3, "1", "RTS")          # base
b.net(Q3, "3", "BOOT")         # collector
b.net(Q3, "2", "DTR")          # emitter

# ---- USB-C connector ------------------------------------------------------
J3 = b.place(usbc, "J3", "USB-C", 290, 110, footprint=FP["usbc"])
for p in ("A4", "B4", "A9", "B9"):
    b.to_power(J3, p, "+5V")
for p in ("A1", "B1", "A12", "B12", "S1"):
    b.to_power(J3, p, "GND")
b.net(J3, "A6", "USB_DP")
b.net(J3, "B6", "USB_DP")
b.net(J3, "A7", "USB_DM")
b.net(J3, "B7", "USB_DM")
b.net(J3, "A5", "CC1")
b.net(J3, "B5", "CC2")
b.no_connect(J3.pin("A8"))
b.no_connect(J3.pin("B8"))
Rc1 = R("R9", "5.1k", 305, 150)
b.net(Rc1, "1", "CC1")
b.to_power(Rc1, "2", "GND")
Rc2 = R("R10", "5.1k", 315, 150)
b.net(Rc2, "1", "CC2")
b.to_power(Rc2, "2", "GND")
# declare +5V and V3V3_USB driven
b.pwr_flag(b.to_power(J3, "A4", "+5V"))

# isolation-barrier reminder note
b.text_note((45, 210),
            "ISOLATION BARRIER: routed slot under U2/U3 - no copper crosses (AC_ nets vs GND/3V3)",
            1.4)

b.save(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT))
print("symbols:", len(b.sch.schematicSymbols),
      "labels:", len(b.sch.labels),
      "wires:", len(b.sch.graphicalItems),
      "no-connects:", len(b.sch.noConnects))
