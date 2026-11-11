"""Board module-cr123a: ESP32-H2-WROOM-02C button, one CR123A cell (Bulgin BX0123 holder, bottom side).

Single source of this board for the shared scripts of ../scripts (gen_project.py, gen_sch.py, gen_pcb.py,
gen_fab.py): the circuit (../scripts/circuit.py plus the battery parts below) and the layout.

Board 42.4 x 27.5 mm, 2 layers, 1.6 mm; the module antenna (6 mm) overhangs the top edge: 42.4 x 33.5 mm in all.
The holder (41.3 x 20 mm, through-hole) is on the bottom side, centred on a row 16.5 mm below the top edge: its two
contacts (- left, + right in the top view) and two locating pegs (3.2 mm holes) sit in that row, below the module.
Top side: module at the top right, its pull-ups and button filter on its left (as on the coin cell boards), 3.3 V
trunk along the top; under the hole row the TPS63900 (left), the button (middle) and the battery input (right).
Bottom side: the holder; the test pads in the strip above it.
The CR123A has a low internal resistance (well under 1 ohm, pulses of 1 A and more): no bulk capacitor bank, one
100 uF on VBAT besides the 10 uF at the converter input.
"""

import circuit
from circuit import C1206, GND, GROUND_NETS, LIB, POWER_NETS, PWR_FLAGS, V33, VBAT  # noqa: F401 (used by scripts)

PROJECT = "matter-button-module-cr123a"
BATTERY = "CR123A"
TITLE = "ESP32-H2 Matter over Thread button, CR123A"
COMPANY = circuit.COMPANY
REV = "1.0"
DATE = "2026-11-11"

HOLDER_FP = "BatteryHolder_Bulgin_BX0123_CR123A"
# stock footprint without its "+" silkscreen mark 4 mm outside the holder (off the board here); TEXTS_PCB has one
CUSTOM_FOOTPRINTS = [dict(name=HOLDER_FP, stock="Battery:BatteryHolder_Bulgin_BX0123_1xCR123", drop_silk_text=["+"])]

PARTS = circuit.finish(circuit.battery_parts(
    holder=dict(value="CR123A", fp=f"{LIB}:{HOLDER_FP}", mpn="Bulgin BX0123",
                desc="CR123A holder, through-hole, contacts 37.8 mm apart"),
    bulk=[("100uF", C1206, "CL31A107MQHNNNE", "C15008", "6.3 V X5R bulk")],
) + [dict(p) for p in circuit.CORE_PARTS])
TEXTS = circuit.core_texts(BATTERY)


def nets():
    return circuit.nets(PARTS)


# ------------------------------------------------------------------------------------------------------ layout
OUTLINE = (100.0, 100.0, 42.4, 27.5, 0.5)  # X0, Y0, W, H, corner radius (mm)
MODULE = (132.6, 104.0)  # top right, antenna area (footprint y -10 .. -4) outside the top edge
# holder origin = + contact (pad 1); on the bottom side the - contact (pad 2) is 37.8 mm to its left, the locating
# pegs 10.425 and 27.375 mm: contacts at x 102.3 / 140.1, pegs at 112.725 / 129.675, all at y 116.5
HOLDER = (140.1, 116.5)
KEEPOUT_RINGS = []  # the cell lies in a plastic holder: no exposed cell can on the board
NO_STITCH = []
SOLID_PADS = []

F, B = "F", "B"
# ref: (x, y, rotation, side). Rotation counter-clockwise: 0 pad 1 left, 90 pad 1 down, 180 right, 270 up.
PLACE = {
    "U1": (*MODULE, 0, F),
    "BT1": (*HOLDER, 0, B),
    # left of the module, next to its pins (same placement relative to the module as on the coin cell boards)
    "C6": (122.2, 101.62, 270, F),
    "R4": (121.2, 103.1, 0, F),
    "C7": (121.2, 104.2, 180, F),
    "C8": (120.7, 106.2, 180, F),
    "R7": (122.2, 107.6, 90, F),
    "R6": (120.7, 109.1, 0, F),
    "R5": (121.2, 110.25, 0, F),
    # LED under the module pin 15 (GPIO22), right of the peg hole
    "R8": (133.8, 115.35, 0, F),
    "D1": (134.3, 116.9, 0, F),
    # lower band, left: 3V3 out (C5, JP2) and the TPS63900 (VOUT left, VIN right, CFG resistors above, L1 below)
    "C5": (105.0, 119.6, 90, F),
    "JP2": (105.0, 123.02, 90, F),
    "U2": (110.2, 122.4, 270, F),
    "R1": (110.2, 118.9, 90, F),
    "R2": (109.2, 118.9, 90, F),
    "R3": (108.2, 118.9, 90, F),
    "L1": (110.2, 125.75, 180, F),
    "C4": (107.1, 123.2, 90, F),
    "C3": (113.3, 123.2, 90, F),
    # lower band, middle: button
    "SW1": (127.0, 122.5, 0, F),
    # lower band, right: + contact -> Q1 -> JP1 -> C1 -> VBAT; battery sense R9, C9
    "Q1": (138.9, 120.6, 0, F),
    "JP1": (134.8, 122.6, 180, F),
    "C1": (135.0, 125.4, 0, F),
    "R9": (131.0, 125.3, 0, F),
    "C9": (131.0, 126.6, 180, F),
    # test pads, bottom side (pogo pins), in the strip above the holder: top left GND, 3V3 / BOOT, EN; top right
    # VBAT, RX, TX, VSNS / USB D-, D+
    "TP2": (102.0, 101.6, 0, B), "TP1": (104.54, 101.6, 0, B),
    "TP6": (102.0, 104.3, 0, B), "TP5": (104.54, 104.3, 0, B),
    "TP9": (132.96, 101.6, 0, B), "TP4": (135.5, 101.6, 0, B), "TP3": (138.04, 101.6, 0, B),
    "TP10": (140.58, 101.6, 0, B),
    "TP7": (138.04, 104.3, 0, B), "TP8": (140.58, 104.3, 0, B),
}

# Hand-routed tracks (top layer unless "B"): the converter, the module pins and the test pads. FreeRouting keeps them
# (locked) and routes the rest (battery input, VBAT bus, sense line, LED, button line, BOOT); the pours connect GND.
# (net, width, [points], layer)
ROUTES = [
    # TPS63900 (U2 rotated: bottom row VOUT LX2 GND LX1 VIN, top row CFG3 CFG2 CFG1 SEL EN, from left)
    ("GND", 0.25, [(110.2, 123.613), (110.2, 122.4)], F),                     # pin 8 to exposed pad
    ("GND", 0.3, [(110.2, 122.4), (108.4, 122.4), (107.1, 122.425)], F),      # EP, via, C4
    ("GND", 0.3, [(110.2, 122.4), (112.0, 122.4), (113.3, 122.425)], F),      # EP, via, C3
    ("/VOUT", 0.25, [(109.2, 123.613), (109.2, 123.9), (107.1, 123.9)], F),   # pin 6 to C4
    ("/VOUT", 0.3, [(107.1, 123.975), (106.3, 123.67), (105.0, 123.67)], F),  # C4 to JP2
    ("VBAT", 0.25, [(111.2, 123.613), (111.2, 123.9), (113.3, 123.9)], F),    # VIN to C3
    ("/LX1", 0.3, [(110.7, 123.613), (110.7, 125.0)], F),
    ("/LX2", 0.3, [(109.7, 123.613), (109.7, 125.0)], F),
    ("/CFG1", 0.2, [(110.2, 121.188), (110.2, 119.41)], F),
    ("/CFG2", 0.2, [(109.7, 121.188), (109.7, 120.5), (109.2, 120.0), (109.2, 119.41)], F),
    ("/CFG3", 0.2, [(109.2, 121.188), (109.2, 120.8), (108.2, 119.8), (108.2, 119.41)], F),
    ("VBAT", 0.25, [(110.7, 120.9), (111.2, 120.9)], F),                      # SEL and EN to VIN
    ("VBAT", 0.25, [(111.2, 120.9), (111.2, 120.4), (111.5, 120.1), (114.3, 120.1), (114.3, 124.0),
                    (113.775, 124.0)], F),
    ("GND", 0.3, [(108.2, 118.39), (111.1, 118.39)], F),                      # R1-R3 to GND
    ("GND", 0.3, [(105.0, 118.825), (104.2, 118.2)], F),                      # C5
    # 3V3: JP2 -> C5 -> trunk up between the - contact and the left peg, along the top edge to pin 1; branch at
    # x 119.1 for the pull-ups R4, R6, R5
    ("+3V3", 0.3, [(105.0, 120.375), (105.0, 122.37)], F),
    ("+3V3", 0.3, [(105.0, 121.0), (106.0, 121.0), (106.0, 101.12), (123.4, 101.12)], F),
    ("+3V3", 0.3, [(119.1, 101.12), (119.1, 110.25), (120.69, 110.25)], F),
    ("+3V3", 0.3, [(119.1, 103.1), (120.69, 103.1)], F),                      # R4
    ("+3V3", 0.3, [(119.1, 109.1), (120.19, 109.1)], F),                      # R6
    ("GND", 0.2, [(122.2, 102.1), (122.6, 101.85), (125.45, 101.85)], F),     # C6, between pins 1 and 2
    ("/EN", 0.2, [(123.2, 102.9), (121.71, 103.1), (121.68, 104.2)], F),
    ("/EN", 0.2, [(124.5, 102.6), (125.2, 102.6)], F),                        # to TP5
    ("GND", 0.25, [(120.72, 104.2), (119.9, 105.25)], F),                     # C7
    ("GND", 0.25, [(120.22, 106.2), (119.9, 105.25)], F),                     # C8
    # button: GPIO10 RC at pin 5; BTN_SW enters the module margin between pins 5 and 6, runs down inside the
    # pads, leaves at the corner between pins 9 and 10 and goes down between the pegs to SW1
    ("/BTN", 0.2, [(123.2, 107.1), (122.2, 107.09), (121.18, 106.2)], F),
    ("/BTN_SW", 0.2, [(122.2, 108.11), (121.21, 109.1)], F),
    ("/BTN_SW", 0.2, [(122.2, 108.11), (122.5, 107.85), (125.0, 107.85), (125.0, 120.9), (124.925, 121.425)], F),
    ("/BTN_SW", 0.25, [(124.925, 121.425), (129.075, 121.425)], F),           # both pads of contact 1
    ("GND", 0.3, [(124.925, 123.575), (129.075, 123.575)], F),                # both pads of contact 2
    ("/STRAP8", 0.2, [(121.71, 110.25), (123.2, 110.1)], F),
    # LED under pin 15
    ("/LED", 0.2, [(133.35, 114.4), (133.35, 114.9), (133.29, 115.35)], F),
    ("/LED_A", 0.2, [(134.31, 115.35), (135.087, 116.9)], F),
    ("GND", 0.3, [(133.513, 116.9), (132.6, 117.7)], F),                      # D1 cathode
    # battery input: + contact -> Q1 drain; Q1 source -> JP1; gate to GND
    ("/BAT+", 0.4, [(140.1, 116.5), (139.838, 120.6)], F),
    ("/VBAT_Q", 0.4, [(137.962, 121.55), (137.0, 122.6), (135.45, 122.6)], F),
    ("GND", 0.3, [(137.962, 119.65), (137.2, 119.2)], F),                     # Q1 gate
    ("GND", 0.3, [(130.52, 126.6), (129.6, 126.5)], F),                       # C9
    # right of the module: inward stubs to vias next to the pads, to the test pads on the bottom side
    ("/VBAT_SENSE", 0.2, [(140.7, 102.6), (140.0, 102.6)], F),
    ("/USB_DP", 0.2, [(140.7, 107.1), (140.0, 107.1)], F),
    ("/USB_DN", 0.2, [(140.7, 108.6), (140.0, 108.6)], F),
    ("/TXD0", 0.2, [(140.7, 110.1), (140.0, 110.1)], F),
    ("/RXD0", 0.2, [(140.7, 111.6), (140.0, 111.6)], F),
    ("/VBAT_SENSE", 0.2, [(140.0, 102.6), (140.58, 101.6)], B),
    ("/USB_DP", 0.2, [(140.0, 107.1), (140.0, 104.88), (140.58, 104.3)], B),
    ("/USB_DN", 0.2, [(140.0, 108.6), (139.2, 108.6), (139.2, 105.4), (138.1, 104.3)], B),
    ("/TXD0", 0.2, [(140.0, 110.1), (138.8, 110.1), (136.9, 108.2), (136.9, 102.54), (137.5, 101.94)], B),
    ("/RXD0", 0.2, [(140.0, 111.6), (138.2, 111.6), (136.0, 109.4), (136.0, 102.4), (135.5, 101.6)], B),
    # left: test pads in the top left corner
    ("+3V3", 0.3, [(106.0, 101.12), (105.0, 101.12)], B),                     # from the trunk on top
    ("/EN", 0.2, [(125.2, 102.6), (124.85, 102.95), (106.0, 102.95), (104.9, 104.05)], B),
]
# GND vias: the pours connect them (127.2, 118.6 keeps the top pour between the button line and the LED)
VIAS = [("GND", 112.0, 122.4), ("GND", 108.4, 122.4), ("GND", 111.1, 118.39), ("GND", 104.2, 118.2),
        ("GND", 119.9, 105.25), ("GND", 127.0, 123.575), ("GND", 132.6, 117.7), ("GND", 137.2, 119.2),
        ("GND", 129.6, 126.5), ("GND", 127.2, 118.6),
        ("+3V3", 106.0, 101.12), ("/EN", 125.2, 102.6),
        ("/VBAT_SENSE", 140.0, 102.6), ("/USB_DP", 140.0, 107.1), ("/USB_DN", 140.0, 108.6),
        ("/TXD0", 140.0, 110.1), ("/RXD0", 140.0, 111.6)]

# reference designators shown on the silkscreen: ref -> (x, y) or None (footprint default)
SILK_REFS = {"U1": (132.6, 111.0), "JP1": (132.3, 122.6), "JP2": (103.2, 125.4)}

# silkscreen labels of the test pads (bottom side), below each pad
TP_LABEL = {"TP1": "3V3", "TP2": "GND", "TP3": "TX", "TP4": "RX", "TP5": "EN", "TP6": "BOOT", "TP7": "D-",
            "TP8": "D+", "TP9": "VBAT", "TP10": "VSNS"}

# top layer under the module body: no tracks (ground under the module, Espressif guideline); the margin next to the
# pads stays free: button line and test pad vias on the left, test pad vias on the right
UNDER_MODULE = [(125.6, 100.4), (139.6, 100.4), (139.6, 112.6), (125.6, 112.6)]

# silkscreen texts: (text, x, y, layer, size, thickness, angle)
TEXTS_PCB = [("Thread Button", 112.5, 105.5, F, 1.0, 0.15, 0), ("CR123A", 112.5, 107.5, F, 1.0, 0.15, 0),
             ("Made by Haxeko", 118.0, 101.3, B, 0.9, 0.13, 0), (f"rev {REV}", 127.0, 101.3, B, 0.6, 0.1, 0),
             ("+", 140.1, 113.6, B, 1.5, 0.2, 0), ("-", 102.3, 113.6, B, 1.5, 0.2, 0)]
