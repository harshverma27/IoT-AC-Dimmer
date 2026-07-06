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


def CP2102():
    # Silicon Labs CP2102 USB-to-UART bridge, QFN-28.
    left = [("8", "VBUS", "power_in"), ("7", "REGIN", "power_in"),
            ("6", "VDD", "power_out"), ("4", "D+", "bidirectional"),
            ("5", "D-", "bidirectional"), ("3", "GND", "power_in"),
            ("9", "~{RST}", "input")]
    right = [("26", "TXD", "output"), ("25", "RXD", "input"),
             ("24", "RTS", "output"), ("23", "CTS", "input"),
             ("28", "DSR", "input"), ("27", "DTR", "output"),
             ("1", "DCD", "input"), ("2", "RI", "input")]
    nc = [(str(n), "NC", "no_connect") for n in range(10, 23)]  # pins 10..22
    return make_rect_symbol(
        "Interface_USB:CP2102", "U", "CP2102",
        left=left, right=right, top=nc[:7], bottom=nc[7:], half_width=12.7,
        description="USB to UART bridge controller, QFN-28",
        keywords="usb uart serial bridge cp2102",
        fp_filters="QFN*5x5mm*P0.5mm*",
        datasheet="https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf")


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


def TP4056():
    # TP4056 1A Li-ion linear charger, SOP-8 (EP).
    left = [("8", "CE", "input"), ("4", "VCC", "power_in"),
            ("1", "TEMP", "input"), ("2", "PROG", "passive")]
    right = [("5", "BAT", "power_out"), ("7", "~{CHRG}", "open_collector"),
             ("6", "~{STDBY}", "open_collector"), ("3", "GND", "power_in")]
    return make_rect_symbol(
        "Battery_Management:TP4056", "U", "TP4056",
        left=left, right=right, half_width=8.89,
        description="1A standalone linear Li-ion battery charger, SOP-8",
        keywords="battery charger li-ion lipo usb",
        fp_filters="SOIC*3.9x4.9mm*P1.27mm*",
        datasheet="https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf")
