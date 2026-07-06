"""parts.py - custom KiCad symbols for parts not in the KiCad standard library.

Pinouts follow the manufacturer datasheets.  Each returns a kiutils Symbol
(single unit) ready for Board.embed_custom().
"""
from schlib import make_rect_symbol


def HLK_PM03():
    # Hi-Link HLK-PM03: isolated 230VAC -> 3.3V/900mA AC/DC module.
    # Pin1 AC-L, Pin2 AC-N, Pin3 -Vo (GND), Pin4 +Vo (3.3V)
    return make_rect_symbol(
        "Power:HLK-PM03", "PS", "HLK-PM03",
        left=[("1", "L~", "passive"), ("2", "N~", "passive")],
        right=[("4", "+Vo", "power_out"), ("3", "-Vo", "power_out")],
        half_width=8.89,
        description="Isolated AC/DC module 100-240VAC to 3.3V 900mA",
        keywords="ac-dc isolated power module",
        fp_filters="Converter_ACDC_HLK-PM*",
        datasheet="https://datasheet.lcsc.com/lcsc/HLK-PM03.pdf")


def TLP281_4():
    # Toshiba TLP281-4: quad transistor-output optocoupler, SOP-16.
    # LEDs on pins 1-8, output transistors on pins 9-16.
    left = [("1", "A1", "passive"), ("2", "K1", "passive"),
            ("3", "A2", "passive"), ("4", "K2", "passive"),
            ("5", "A3", "passive"), ("6", "K3", "passive"),
            ("7", "A4", "passive"), ("8", "K4", "passive")]
    right = [("16", "C1", "passive"), ("15", "E1", "passive"),
             ("14", "C2", "passive"), ("13", "E2", "passive"),
             ("12", "C3", "passive"), ("11", "E3", "passive"),
             ("10", "C4", "passive"), ("9", "E4", "passive")]
    return make_rect_symbol(
        "Isolator:TLP281-4", "U", "TLP281-4",
        left=left, right=right, half_width=8.89,
        description="Quad transistor-output optocoupler, 3.75kV, SOP-16",
        keywords="optocoupler quad phototransistor isolation",
        fp_filters="SOIC*3.9x9.9mm*P1.27mm* DIP*W7.62mm*",
        datasheet="https://toshiba.semicon-storage.com/info/TLP281-4_datasheet_en.pdf")


def MOC3021():
    # Fairchild/ON MOC3021: random-phase opto-TRIAC driver, 6-pin DIP.
    # 1 Anode, 2 Cathode, 3 NC, 4 Main Terminal, 5 substrate/NC, 6 Main Terminal
    return make_rect_symbol(
        "Isolator:MOC3021", "U", "MOC3021",
        left=[("1", "A", "input"), ("2", "K", "input"), ("3", "NC", "no_connect")],
        right=[("6", "MT", "passive"), ("5", "NC", "no_connect"), ("4", "MT", "passive")],
        half_width=7.62,
        description="Random-phase opto-isolated TRIAC driver, 400V, DIP-6",
        keywords="optocoupler triac driver isolation gate",
        fp_filters="DIP*W7.62mm*",
        datasheet="https://www.onsemi.com/pdf/datasheet/moc3021m-d.pdf")


def ESP32_DevKit():
    # ESP32-WROOM-32 DevKit V1 (DOIT, 30-pin).  A ready-made module that plugs
    # onto the carrier via two 1x15 female header rows.  It carries its own
    # USB-serial bridge, micro-USB, auto-reset and BOOT/EN buttons, so the
    # carrier only needs to route power (3V3/GND) and the GPIOs it uses.
    # Pin numbers 1..15 = left row (top->bottom), 16..30 = right row.
    left = [("1", "EN", "input"),
            ("2", "IO36/VP", "bidirectional"),
            ("3", "IO39/VN", "bidirectional"),
            ("4", "IO34", "bidirectional"),
            ("5", "IO35", "bidirectional"),
            ("6", "IO32", "bidirectional"),
            ("7", "IO33", "bidirectional"),
            ("8", "IO25", "bidirectional"),
            ("9", "IO26", "bidirectional"),
            ("10", "IO27", "bidirectional"),
            ("11", "IO14", "bidirectional"),
            ("12", "IO12", "bidirectional"),
            ("13", "GND", "power_in"),
            ("14", "IO13", "bidirectional"),
            ("15", "VIN", "power_in")]
    right = [("16", "GND", "power_in"),
             ("17", "IO23", "bidirectional"),
             ("18", "IO22", "bidirectional"),
             ("19", "IO1/TX0", "bidirectional"),
             ("20", "IO3/RX0", "bidirectional"),
             ("21", "IO21", "bidirectional"),
             ("22", "IO19", "bidirectional"),
             ("23", "IO18", "bidirectional"),
             ("24", "IO5", "bidirectional"),
             ("25", "IO17", "bidirectional"),
             ("26", "IO16", "bidirectional"),
             ("27", "IO4", "bidirectional"),
             ("28", "IO2", "bidirectional"),
             ("29", "IO15", "bidirectional"),
             ("30", "3V3", "power_in")]
    return make_rect_symbol(
        "Module:ESP32-DevKitC", "U", "ESP32-DevKitC-30",
        left=left, right=right, half_width=10.16,
        description="ESP32-WROOM-32 DevKit V1 (30-pin) plug-in module, USB programmable",
        keywords="esp32 wroom devkit module wifi ble",
        fp_filters="ESP32*DevKit* PinSocket*2.54mm*1x15*",
        datasheet="https://docs.espressif.com/projects/esp-idf/en/latest/esp32/hw-reference/esp32/get-started-devkitc.html")


def ME6211_33():
    # ME6211C33 3.3V LDO, SOT-23-5.  1 VIN 2 GND 3 EN 4 NC 5 VOUT
    return make_rect_symbol(
        "Regulator_Linear:ME6211C33", "U", "ME6211C33M5G",
        left=[("1", "VIN", "power_in"), ("3", "EN", "input")],
        right=[("5", "VOUT", "power_out")],
        bottom=[("2", "GND", "power_in")],
        top=[("4", "NC", "no_connect")],
        half_width=6.35,
        description="500mA low-dropout 3.3V regulator, SOT-23-5",
        keywords="ldo regulator 3.3v low dropout",
        fp_filters="SOT?23*",
        datasheet="https://datasheet.lcsc.com/lcsc/ME6211C33M5G.pdf")


def TP4056_module():
    # TP4056 + DW01/FS8205 charge+protect breakout board (Type-C variant).
    # A ready-made module: charges via its own USB-C, includes the PROG
    # resistor, DW01 protection and CHRG/STDBY LEDs onboard.  The carrier wires
    # only the battery (B+/B-) and the protected load output (OUT+/OUT-);
    # IN+/IN- are fed by the module's own USB-C, so they stay unconnected here.
    left = [("1", "IN+", "power_in"), ("2", "IN-", "power_in")]
    right = [("3", "B+", "passive"), ("4", "B-", "passive"),
             ("5", "OUT+", "power_out"), ("6", "OUT-", "power_out")]
    return make_rect_symbol(
        "Battery_Management:TP4056_Module", "U", "TP4056-Module",
        left=left, right=right, half_width=7.62,
        description="TP4056 Li-ion charge + DW01 protection breakout module, USB-C",
        keywords="battery charger li-ion lipo module tp4056 dw01 protection",
        fp_filters="PinHeader*1x06* TP4056*Module*",
        datasheet="https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf")
