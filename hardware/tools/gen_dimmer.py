#!/usr/bin/env python3
"""Generate hardware/dimmer/dimmer.kicad_sch (mains-side AC dimmer).

Blocks: ESP32 DevKit (plug-in module, programmed over its own micro-USB),
HLK-PM03 isolated PSU, AC in/out screw terminals, TLP281-4 zero-cross detect,
MOC3021 opto-TRIAC gate drive, BT138-600 TRIAC with snubber.  Connectivity is
expressed with net labels (signals) and power ports (rails); mains nets are
prefixed AC_.

The USB-serial subsystem (CP2102, USB-C, auto-reset transistors, BOOT/EN
buttons) is gone: the ESP32 DevKit carries its own USB bridge, micro-USB jack,
auto-reset and BOOT/EN buttons, so the carrier only routes 3V3/GND + the two
GPIOs it uses.
"""
import os
import schlib as S
import parts

OUT = os.path.join(os.path.dirname(__file__), "..", "dimmer", "dimmer.kicad_sch")

FP = {
    "esp32": "Module:ESP32-DevKitC",
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
}

b = S.Board("dimmer")
b.setup_power(("GND", "+3V3", "PWR_FLAG"))

# ---- embed standard-library symbols --------------------------------------
res = b.embed_stdlib("Device.kicad_sym", "R")
cap = b.embed_stdlib("Device.kicad_sym", "C")
diode = b.embed_stdlib("Diode.kicad_sym", "1N4007")
triac = b.embed_stdlib("Triac_Thyristor.kicad_sym", "BT138-600")
term = b.embed_stdlib("Connector.kicad_sym", "Screw_Terminal_01x02")

# ---- embed custom symbols ------------------------------------------------
esp = b.embed_custom(parts.ESP32_DevKit())
hlk = b.embed_custom(parts.HLK_PM03())
tlp = b.embed_custom(parts.TLP281_4())
moc = b.embed_custom(parts.MOC3021())


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
b.text_note((45, 80), "Zero-cross detect -> IO34", 1.5)
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
b.text_note((45, 140), "Opto-TRIAC gate drive <- IO25", 1.5)
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
# LOGIC SIDE - ESP32 DevKit (plug-in module, USB programmable)
# ==========================================================================
b.text_note((150, 40), "=== ESP32 DevKit (plug-in module, flash over micro-USB) ===", 2.0)

U1 = b.place(esp, "U1", "ESP32-DevKitC-30", 175, 110, footprint=FP["esp32"])
b.to_power(U1, "30", "+3V3")    # 3V3 pin fed from HLK-PM03 (bypasses onboard LDO)
b.to_power(U1, "13", "GND")
b.to_power(U1, "16", "GND")
b.net(U1, "4", "ZC_DET")        # IO34 <- zero-cross
b.net(U1, "8", "GATE_DRV")      # IO25 -> opto-TRIAC gate
# unused DevKit header pins
for p in ("1", "2", "3", "5", "6", "7", "9", "10", "11", "12", "14", "15",
          "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27",
          "28", "29"):
    b.no_connect(U1.pin(p))

# 3V3 rail decoupling / bulk (the DevKit also carries its own decoupling)
decouple("C1", "10uF", 150, 150, fp="cbulk")
decouple("C2", "100nF", 200, 150)
decouple("C4", "10uF", 78, 60, fp="cbulk")   # bulk on HLK 3V3 output

# programming reminder
b.text_note((150, 175),
            "Programming: plug micro-USB into the ESP32 DevKit (onboard CP2102 + auto-reset). "
            "Do NOT power from mains and USB at the same time.",
            1.4)

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
