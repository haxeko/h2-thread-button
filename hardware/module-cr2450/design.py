"""Board module-cr2450: ESP32-H2-WROOM-02C button, one CR2450 coin cell (Keystone 3008 holder, bottom side).

Single source of this board for the shared scripts of ../scripts (gen_project.py, gen_sch.py, gen_pcb.py,
gen_fab.py): the circuit (../scripts/circuit.py plus the battery parts below) and the layout.

Board 37.4 x 30.5 mm, 2 layers, 1.6 mm; the module antenna (6 mm) overhangs the top edge: 37.4 x 36.5 mm in all.
The top side carries the whole circuit, laid out as the former 29.8 x 23.9 mm CR2032 board (git history) moved 6 mm
to the right. The CR2450 holder is on the bottom side: its two SMT tabs (cell +) left and right, the contact pad
(cell -, GND) in the middle. The bottom side cannot be crossed between the tabs (tab, ring, contact pad, ring, tab
from edge to edge), so every connection between the upper and the lower half runs on the top side.
"""

import circuit
from circuit import C1210, GND, GROUND_NETS, LIB, POWER_NETS, PWR_FLAGS, V33, VBAT  # noqa: F401 (used by scripts)

PROJECT = "matter-button-module-cr2450"
BATTERY = "CR2450"
TITLE = "ESP32-H2 Matter over Thread button, CR2450"
COMPANY = circuit.COMPANY
REV = "1.0"
DATE = "2026-11-11"

HOLDER_FP = "BatteryHolder_Keystone_3008_CR2450"
# stock Keystone 3008 footprint: both tabs are pad "1"; the copy leaves the tab at x = +15.3 unnumbered. On the
# bottom side (mirrored) that tab is the left one, the numbered (BAT+) tab the right one, next to Q1.
# The stock courtyard is drawn as open pieces (KiCad 9 DRC: malformed courtyard): the copy has one closed polygon
# around the tabs and the retainer instead.
CUSTOM_FOOTPRINTS = [dict(
    name=HOLDER_FP, stock="Battery:BatteryHolder_Keystone_3008_1x2450", unnumber=(15.3, 0),
    courtyard=[(-4.45, -13.55), (4.45, -13.55), (4.45, -12.55), (13.35, -6.7), (13.35, -3.25), (18.8, -3.25),
               (18.8, 3.25), (13.35, 3.25), (13.35, 7.3), (12.41, 9.51), (10.15, 10.45), (9.15, 10.05),
               (4.56, 11.96), (0, 12.8), (-4.56, 11.96), (-9.15, 10.05), (-10.15, 10.45), (-12.41, 9.51),
               (-13.35, 7.3), (-13.35, 3.25), (-18.8, 3.25), (-18.8, -3.25), (-13.35, -3.25), (-13.35, -6.7),
               (-4.45, -12.55)])]

PARTS = circuit.finish(circuit.battery_parts(
    holder=dict(value="CR2450", fp=f"{LIB}:{HOLDER_FP}", mpn="Keystone 3008",
                desc="CR2450 retainer, SMT, tabs 30.6 mm apart"),
    bulk=[("220uF", C1210, "GRM32ER60J227ME05L", "C469553", "6.3 V X5R bulk"),
          ("220uF", C1210, "GRM32ER60J227ME05L", "C469553", "6.3 V X5R bulk")],
) + [dict(p) for p in circuit.CORE_PARTS])
TEXTS = circuit.core_texts(BATTERY)


def nets():
    return circuit.nets(PARTS)


# ------------------------------------------------------------------------------------------------------ layout
OUTLINE = (100.0, 100.0, 37.4, 30.5, 0.5)  # X0, Y0, W, H, corner radius (mm)
MODULE = (126.0, 104.0)  # antenna area (footprint y -10 .. -4) outside the top edge; 1.4 mm channel on its right
HOLDER = (118.7, 117.0)  # cell centre, bottom side: tabs 0.4 mm from the side edges, cell edge 4.75 mm from the antenna
# bottom side, ring from the edge of the contact pad (10 mm) to just outside the cell (12.25 mm): the crimped edge of
# the cell is its + terminal, so no copper at all (tracks, vias, pour) where the cell slides in and sits
KEEPOUT_RINGS = [(*HOLDER, 10.05, 12.6)]
NO_STITCH = [(*HOLDER, 12.9)]  # no stitching via under the cell (contact pad and ring)
SOLID_PADS = [("BT1", "2")]  # cell contact: solid connection to the bottom pour, no thermal spokes

F, B = "F", "B"
# ref: (x, y, rotation, side). Rotation counter-clockwise: 0 pad 1 left, 90 pad 1 down, 180 right, 270 up.
PLACE = {
    "U1": (*MODULE, 0, F),
    "BT1": (*HOLDER, 0, B),
    # left of the module, next to its pins: decoupling at pin 1 (3V3), EN pull-up (and RC option) at pin 2,
    # button RC filter and pull-up at pin 5 (GPIO10), GPIO8 strap at pin 7
    "C6": (115.6, 101.62, 270, F),
    "R4": (114.6, 103.1, 0, F),
    "C7": (114.6, 104.2, 180, F),
    "C8": (114.1, 106.2, 180, F),
    "R7": (115.6, 107.6, 90, F),
    "R6": (114.1, 109.1, 0, F),
    "R5": (114.6, 110.25, 0, F),
    # lower left: 3V3 out (C5, JP2) and the TPS63900 (VOUT left, VIN right, CFG resistors above, L1 below)
    "C5": (107.65, 115.2, 90, F),
    "JP2": (107.65, 118.62, 90, F),
    "U2": (112.85, 118.0, 270, F),
    "R1": (112.85, 114.5, 90, F),
    "R2": (111.85, 114.5, 90, F),
    "R3": (110.85, 114.5, 90, F),
    "L1": (112.85, 121.35, 180, F),
    "C4": (109.75, 118.8, 90, F),
    "C3": (115.95, 118.8, 90, F),
    # below the module: button, C2 under it; LED (IO22, pin 15) on its right
    "SW1": (120.9, 117.4, 0, F),
    "C2": (120.9, 121.5, 0, F),
    "R8": (125.7, 115.35, 180, F),
    "D1": (125.4, 116.8, 180, F),
    # battery input, right, above the + tab: tab (via in the pad) -> Q1 -> JP1 -> C1 -> C2, C3; sense R9, C9
    "Q1": (133.3, 117.3, 180, F),
    "JP1": (130.0, 117.2, 270, F),
    "C1": (128.6, 121.5, 180, F),
    "R9": (133.0, 121.0, 0, F),
    "C9": (133.0, 122.4, 180, F),
    # test pads, bottom side (pogo pins), outside the holder: top left GND, 3V3 / BOOT, EN; top right RX, TX, VSNS /
    # USB D-, D+; VBAT below the + tab
    "TP2": (102.0, 101.6, 0, B), "TP1": (104.54, 101.6, 0, B),
    "TP6": (102.0, 104.3, 0, B), "TP5": (104.54, 104.3, 0, B),
    "TP4": (128.9, 101.6, 0, B), "TP3": (131.44, 101.6, 0, B), "TP10": (133.98, 101.6, 0, B),
    "TP7": (131.44, 104.3, 0, B), "TP8": (133.98, 104.3, 0, B),
    "TP9": (133.6, 123.4, 0, B),
}

# Hand-routed tracks (top layer unless "B"): every connection but GND (the pours connect it). FreeRouting keeps them
# (locked) and routes whatever is left. (net, width, [points], layer)
ROUTES = [
    # TPS63900 (U2 rotated: bottom row VOUT LX2 GND LX1 VIN, top row CFG3 CFG2 CFG1 SEL EN, from left)
    ("GND", 0.25, [(112.85, 119.213), (112.85, 118.0)], F),                    # pin 8 to exposed pad
    ("GND", 0.3, [(112.85, 118.0), (111.05, 118.0), (109.75, 118.025)], F),    # EP, via, C4
    ("GND", 0.3, [(112.85, 118.0), (114.65, 118.0), (115.95, 118.025)], F),    # EP, via, C3
    ("/VOUT", 0.25, [(111.85, 119.213), (111.85, 119.5), (109.75, 119.5)], F),  # pin 6 to C4
    ("/VOUT", 0.3, [(109.75, 119.575), (108.95, 119.27), (107.65, 119.27)], F),  # C4 to JP2
    ("VBAT", 0.25, [(113.85, 119.213), (113.85, 119.5), (115.95, 119.5)], F),  # VIN to C3
    ("/LX1", 0.3, [(113.35, 119.213), (113.35, 120.6)], F),
    ("/LX2", 0.3, [(112.35, 119.213), (112.35, 120.6)], F),
    ("/CFG1", 0.2, [(112.85, 116.787), (112.85, 115.01)], F),
    ("/CFG2", 0.2, [(112.35, 116.787), (112.35, 116.1), (111.85, 115.6), (111.85, 115.01)], F),
    ("/CFG3", 0.2, [(111.85, 116.787), (111.85, 116.4), (110.85, 115.4), (110.85, 115.01)], F),
    ("VBAT", 0.25, [(113.35, 116.5), (113.85, 116.5)], F),                     # SEL and EN to VIN
    ("VBAT", 0.25, [(113.85, 116.5), (113.85, 116.0), (114.15, 115.7), (116.95, 115.7), (116.95, 119.6),
                    (116.425, 119.6)], F),
    ("GND", 0.3, [(110.85, 113.99), (113.75, 113.99)], F),                     # R1-R3 to GND
    # 3V3: JP2 -> C5 -> trunk along the left to pin 1; branch at x 112.5 for the pull-ups R4, R6, R5
    ("+3V3", 0.3, [(107.65, 115.975), (107.65, 117.97)], F),
    ("+3V3", 0.3, [(107.65, 116.6), (106.55, 116.6), (106.55, 101.12), (116.8, 101.12)], F),
    ("+3V3", 0.3, [(112.5, 101.12), (112.5, 110.25), (114.09, 110.25)], F),
    ("+3V3", 0.3, [(112.5, 103.1), (114.09, 103.1)], F),                       # R4
    ("+3V3", 0.3, [(112.5, 109.1), (113.59, 109.1)], F),                       # R6
    # C5 to the R1-R3 GND line (its via sits in the contact pad of the cell)
    ("GND", 0.3, [(107.65, 114.425), (108.6, 113.6), (110.6, 113.6), (110.85, 113.99)], F),
    ("GND", 0.2, [(115.6, 102.1), (116.0, 101.85), (118.85, 101.85)], F),      # C6, between pins 1 and 2
    ("/EN", 0.2, [(116.6, 102.9), (115.11, 103.1), (115.08, 104.2)], F),
    ("/EN", 0.2, [(117.9, 102.6), (118.6, 102.6)], F),                         # to TP5
    ("GND", 0.25, [(114.12, 104.2), (113.3, 104.95)], F),                      # C7
    ("GND", 0.25, [(113.62, 106.2), (113.3, 104.95)], F),                      # C8
    # button: GPIO10 RC at pin 5; BTN_SW enters the module margin between pins 5 and 6, runs down inside the
    # pads and leaves at the corner between pins 9 and 10 to SW1
    ("/BTN", 0.2, [(116.6, 107.1), (115.6, 107.09), (114.58, 106.2)], F),
    ("/BTN_SW", 0.2, [(115.6, 108.11), (114.61, 109.1)], F),
    ("/BTN_SW", 0.2, [(115.6, 108.11), (115.9, 107.85), (118.4, 107.85), (118.4, 115.3), (118.825, 116.0)], F),
    ("/BTN_SW", 0.25, [(118.825, 116.325), (122.975, 116.325)], F),            # both pads of contact 1
    ("GND", 0.3, [(118.825, 118.475), (122.975, 118.475)], F),                 # both pads of contact 2
    ("/STRAP8", 0.2, [(115.11, 110.25), (116.6, 110.1)], F),
    ("/BOOT", 0.2, [(116.6, 111.6), (110.6, 111.6), (110.6, 105.5)], F),       # to TP6, via above the cell
    # LED right of the button
    ("/LED", 0.2, [(126.75, 114.4), (126.75, 114.9), (126.21, 115.35)], F),
    ("/LED_A", 0.2, [(125.19, 115.35), (124.613, 116.8)], F),
    ("GND", 0.3, [(126.187, 116.8), (127.2, 116.0)], F),                       # D1 cathode
    # battery input: + tab (bottom side, via in the pad) -> Q1 -> JP1 -> C1 -> bus along the bottom -> C2, C3 / VIN
    ("/BAT+", 0.4, [(131.9, 116.5), (132.362, 117.3)], F),
    ("/VBAT_Q", 0.4, [(134.238, 116.35), (134.238, 115.75), (130.6, 115.75), (130.0, 116.35)], F),
    ("GND", 0.3, [(134.238, 118.25), (135.3, 120.4)], F),                      # Q1 gate, via below the tab
    ("VBAT", 0.4, [(130.0, 117.85), (130.0, 120.4)], F),                       # JP1 to C1
    ("VBAT", 0.4, [(130.075, 122.85), (130.075, 123.35), (116.95, 123.35), (116.95, 119.6)], F),
    ("VBAT", 0.4, [(119.425, 122.85), (119.425, 123.35)], F),                  # C2
    ("VBAT", 0.3, [(130.65, 121.0), (132.49, 121.0)], F),                      # R9, via to TP9
    ("GND", 0.3, [(122.375, 121.5), (123.4, 120.3)], F),                       # C2
    ("GND", 0.3, [(127.125, 121.5), (125.6, 120.0)], F),                       # C1
    # battery sense: R9 / C9 below the + tab, up the 1.4 mm channel right of the module to pin 27 (top side)
    ("/VBAT_SENSE", 0.2, [(133.51, 121.0), (133.48, 122.4)], F),
    ("/VBAT_SENSE", 0.2, [(133.51, 121.0), (133.81, 121.3), (136.5, 121.3), (136.5, 103.1), (136.0, 102.6),
                          (135.3, 102.6)], F),
    ("GND", 0.25, [(132.52, 122.4), (131.6, 122.9)], F),                       # C9
    ("VBAT", 0.3, [(131.6, 121.0), (133.6, 123.4)], B),                        # TP9
    # right of the module: inward stubs to vias next to the pads, to the test pads on the bottom side
    ("/VBAT_SENSE", 0.2, [(134.1, 102.6), (133.4, 102.6)], F),
    ("/USB_DP", 0.2, [(134.1, 107.1), (133.4, 107.1)], F),
    ("/USB_DN", 0.2, [(134.1, 108.6), (133.4, 108.6)], F),
    ("/TXD0", 0.2, [(134.1, 110.1), (133.4, 110.1)], F),
    ("/RXD0", 0.2, [(134.1, 111.6), (133.4, 111.6)], F),
    ("/VBAT_SENSE", 0.2, [(133.4, 102.6), (133.98, 101.6)], B),
    ("/USB_DP", 0.2, [(133.4, 107.1), (133.4, 104.88), (133.98, 104.3)], B),
    ("/USB_DN", 0.2, [(133.4, 108.6), (132.6, 108.6), (132.6, 105.4), (131.5, 104.3)], B),
    ("/TXD0", 0.2, [(133.4, 110.1), (132.2, 110.1), (130.3, 108.2), (130.3, 102.54), (130.9, 101.94)], B),
    ("/RXD0", 0.2, [(133.4, 111.6), (131.6, 111.6), (129.4, 109.4), (129.4, 102.4), (128.9, 101.6)], B),
    # left: test pads in the top left corner
    ("+3V3", 0.3, [(106.55, 101.12), (105.0, 101.12)], B),                    # from the trunk on top
    ("/EN", 0.2, [(118.6, 102.6), (118.25, 102.95), (106.0, 102.95), (104.9, 104.05)], B),
    ("/BOOT", 0.2, [(110.6, 105.5), (102.8, 105.5), (102.4, 105.0)], B),
]
# GND vias: inside the contact pad of the cell or outside the cell, never in the ring; none in the - tab
VIAS = [("GND", 114.65, 118.0), ("GND", 111.05, 118.0), ("GND", 113.75, 113.99), ("GND", 113.3, 104.95),
        ("GND", 120.9, 118.475), ("GND", 127.2, 116.0), ("GND", 135.3, 120.4), ("GND", 123.4, 120.3),
        ("GND", 125.6, 120.0), ("GND", 131.6, 122.9),
        ("/BAT+", 131.9, 116.5), ("+3V3", 106.55, 101.12), ("/EN", 118.6, 102.6), ("/BOOT", 110.6, 105.5),
        ("/VBAT_SENSE", 133.4, 102.6), ("/USB_DP", 133.4, 107.1), ("/USB_DN", 133.4, 108.6),
        ("/TXD0", 133.4, 110.1), ("/RXD0", 133.4, 111.6), ("VBAT", 131.6, 121.0)]

# reference designators shown on the silkscreen: ref -> (x, y) or None (footprint default)
SILK_REFS = {"U1": (126.0, 111.0), "JP1": (128.1, 118.9), "JP2": (107.65, 121.1)}

# silkscreen labels of the test pads (bottom side), below each pad
TP_LABEL = {"TP1": "3V3", "TP2": "GND", "TP3": "TX", "TP4": "RX", "TP5": "EN", "TP6": "BOOT", "TP7": "D-",
            "TP8": "D+", "TP9": "VBAT", "TP10": "VSNS"}

# top layer under the module body: no tracks (ground under the module, Espressif guideline); the margin next to the
# pads stays free: button line and test pad vias on the left, test pad vias on the right
UNDER_MODULE = [(119.0, 100.4), (133.0, 100.4), (133.0, 112.6), (119.0, 112.6)]

# silkscreen texts: (text, x, y, layer, size, thickness, angle)
TEXTS_PCB = [("Thread Button", 109.1, 106.4, F, 0.8, 0.12, 90), ("CR2450", 103.3, 127.5, F, 1.0, 0.15, 0),
             ("Made by Haxeko", 117.0, 101.3, B, 0.9, 0.13, 0), (f"rev {REV}", 125.4, 101.3, B, 0.6, 0.1, 0),
             ("+", 134.0, 112.9, B, 1.0, 0.15, 0), ("+", 103.4, 112.9, B, 1.0, 0.15, 0)]
