"""Board module-cr123a-mini: ESP32-H2-WROOM-02C button as long as one CR123A cell, the cell in the enclosure.

Single source of this board for the shared scripts of ../scripts (gen_project.py, gen_sch.py, gen_pcb.py,
gen_fab.py): the circuit (../scripts/circuit.py, adapted below) and the layout.

Board 34.5 x 14.8 mm (the length of a CR123A), 2 layers, 1.6 mm; the module antenna (6 mm) overhangs the top edge:
34.5 x 20.8 mm in all. The cell lies behind the board in the enclosure, whose battery contacts are wired to two pads
on the bottom side: BAT+ at the left end, BAT- (GND) at the right end. Q1 still protects against a reversed cell.

Every part is on the top side (one-sided assembly); the bottom side has copper only: the two battery pads and eight
test pads. Differences from the circuit of the other boards (there is no room for more):
  - BT1 is not a holder but the two wire pads (not in the BOM: cell and contacts belong to the enclosure)
  - the LED is on GPIO11 (module pin 6) and the battery sense on GPIO4 (pin 3, ADC1_CH3) instead of GPIO22 (pin 15,
    bottom edge of the module, no room below it) and GPIO1 (pin 27, right side): every pin in use is on the left side
    of the module. Firmware: sdkconfig.defaults.cr123a_mini.
  - no JP1 / JP2: the battery current is measured with the ammeter in the BAT+ wire, the converter output is the
    3V3 rail directly
  - one 22 uF on VBAT (the cell has a low internal resistance), no C2; no C7 (EN delay option, never fitted)
  - no test pads for VBAT and VBAT_SENSE (probe C1 and C9)
The TPS63900 corner keeps the routing of the other boards, turned by 180 degrees. Every track is drawn here: the
FreeRouting step of gen_pcb.py has nothing left to route.
"""

import circuit
from circuit import C0603, GND, GROUND_NETS, LIB, POWER_NETS, V33, VBAT  # noqa: F401 (used by scripts)

PROJECT = "matter-button-module-cr123a-mini"
BATTERY = "CR123A"
TITLE = "ESP32-H2 Matter over Thread button, CR123A, 34.5 mm board"
COMPANY = circuit.COMPANY
REV = "1.0"
DATE = "2026-11-12"

# ------------------------------------------------------------------------------------------------------ circuit
BAT_FP = "CR123A_WirePads"
BAT_PLUS = (101.3, 107.0)   # BAT+ pad centre on the board (bottom side, left end): the footprint origin
BAT_MINUS = (132.5, 113.4)  # BAT- pad centre (bottom side, right end corner)
# The footprint sits on the bottom side (mirrored): local x = origin x - board x
CUSTOM_FOOTPRINTS = [dict(
    name=BAT_FP,
    descr="Wire pads of a CR123A that sits in the enclosure: pad 1 cell +, pad 2 cell - (GND), "
          "31.2 mm apart; bottom side, no paste (hand soldered wires or the enclosure's contacts)",
    pads=[("1", 0, 0, 1.8, 4.8),
          ("2", BAT_PLUS[0] - BAT_MINUS[0], BAT_MINUS[1] - BAT_PLUS[1], 2.8, 1.6)])]

DROPPED = {"C7", "JP1", "JP2", "TP9", "TP10"}


def _adapt(p):
    p = dict(p)
    pins = dict(p["pins"])
    if p["ref"] == "U1":  # LED and battery sense on the left side of the module
        pins.update({"3": "VBAT_SENSE", "27": "NC", "6": "LED", "15": "NC"})
    if p["ref"] == "Q1":  # no JP1: source straight to VBAT
        pins["2"] = VBAT
    if p["ref"] in ("U2", "C4"):  # no JP2: the converter output is the 3V3 rail
        pins = {n: (V33 if net == "VOUT" else net) for n, net in pins.items()}
    p["pins"] = pins
    return p


PARTS = circuit.finish([_adapt(p) for p in circuit.battery_parts(
    holder=dict(value="CR123A", fp=f"{LIB}:{BAT_FP}", mpn="",
                desc="CR123A in the enclosure, its contacts wired to the BAT+ / BAT- pads", bom=False),
    bulk=[("22uF", C0603, "CL10A226MQ8NRNC", "C59461", "6.3 V X5R, VBAT input")],
) + circuit.CORE_PARTS if p["ref"] not in DROPPED])

# ERC power flags: VBAT and GND are driven by passive parts only; 3V3 by the converter output (no JP2)
PWR_FLAGS = [f for f in circuit.PWR_FLAGS if f[0] != V33]

_TEXT_CHANGES = {
    "C7: not fitted (the module has its own 10k/1uF RC)": "No EN capacitor (the module has its own 10k/1uF RC)",
    "7  LED GPIO22": "7  LED GPIO11 (module pin 6)",
    "8  Battery sense GPIO1 (ADC1_CH0), no divider": "8  Battery sense GPIO4 (ADC1_CH3, module pin 3), no divider",
    "1  Battery CR123A, reverse polarity protection, bulk capacitors":
        "1  Battery CR123A (in the enclosure, wired to BAT+/BAT-), reverse polarity protection",
    "4  Test pads (bottom side, pogo pins)": "4  Test pads (bottom side, pogo pins); current: ammeter in the BAT+ wire",
}
TEXTS = [(x, y, _TEXT_CHANGES.get(t, t), size) for x, y, t, size in circuit.core_texts(BATTERY)]


def nets():
    return circuit.nets(PARTS)


# ------------------------------------------------------------------------------------------------------ layout
OUTLINE = (100.0, 100.0, 34.5, 14.8, 0.5)  # X0, Y0, W, H, corner radius (mm)
MODULE = (124.7, 104.0)  # top right, antenna area (footprint y -10 .. -4) outside the top edge
KEEPOUT_RINGS = []
NO_STITCH = []
SOLID_PADS = [("BT1", "1"), ("BT1", "2")]  # wire pads: no thermal spokes (BAT- is in the GND pour)

F, B = "F", "B"
# ref: (x, y, rotation, side). Rotation counter-clockwise: 0 pad 1 left, 90 pad 1 down, 180 right, 270 up.
PLACE = {
    "U1": (*MODULE, 0, F),
    "BT1": (*BAT_PLUS, 0, B),
    # top left corner: TPS63900 (VIN left, 3V3 out right, L1 above, CFG resistors below), C5, the 3V3 trunk
    "U2": (104.6, 105.05, 90, F),
    "R1": (104.6, 108.55, 270, F),
    "R2": (105.6, 108.55, 270, F),
    "R3": (106.6, 108.55, 270, F),
    "L1": (104.6, 101.7, 0, F),
    "C4": (107.7, 104.25, 270, F),
    "C3": (101.5, 104.25, 270, F),
    "C5": (109.4, 104.3, 270, F),
    # left of the module, one row per pin: C6 (pin 1, 3V3), R4 (pin 2, EN), C9 + R9 (pin 3, battery sense),
    # R7 + C8 (pin 5, button filter), R8 (pin 6, LED), R5 (pin 7, GPIO8 strap); R6 button pull-up beside R7
    "C6": (114.3, 101.62, 270, F),
    "R4": (113.3, 103.1, 0, F),
    "R9": (112.8, 104.2, 0, F),
    "C9": (114.4, 104.71, 270, F),
    "R7": (113.6, 107.05, 0, F),
    "R6": (111.6, 107.05, 0, F),
    "C8": (113.6, 108.1, 180, F),
    "R8": (113.6, 109.15, 180, F),
    "R5": (113.6, 110.2, 0, F),
    # bottom band: battery input (Q1, C1) above the BAT+ pad and next to the converter input, button, LED
    "Q1": (101.9, 112.4, 90, F),
    "C1": (104.5, 112.6, 90, F),
    "SW1": (109.6, 112.6, 0, F),
    "D1": (113.6, 112.75, 90, F),
    # test pads, bottom side (pogo pins), under the module: EN, 3V3, D+, D- (upper row), BOOT, GND, TX, RX
    "TP5": (119.5, 109.6, 0, B), "TP1": (122.0, 109.6, 0, B), "TP8": (127.0, 109.6, 0, B),
    "TP7": (129.5, 109.6, 0, B),
    "TP6": (119.5, 112.2, 0, B), "TP2": (122.0, 112.2, 0, B), "TP3": (127.0, 112.2, 0, B),
    "TP4": (129.5, 112.2, 0, B),
}

# Hand-routed tracks (top layer unless "B"): every connection but GND (the pours connect it).
# (net, width, [points], layer)
ROUTES = [
    # TPS63900, the layout of the other boards turned by 180 degrees (U2: top row VIN LX1 GND LX2 VOUT, bottom row
    # EN SEL CFG1 CFG2 CFG3, from left)
    ("GND", 0.25, [(104.6, 103.8375), (104.6, 105.05)], F),                   # pin 8 to exposed pad
    ("GND", 0.3, [(104.6, 105.05), (106.4, 105.05), (107.7, 105.025)], F),    # EP, via, C4
    ("GND", 0.3, [(104.6, 105.05), (102.8, 105.05), (101.5, 105.025)], F),    # EP, via, C3
    ("+3V3", 0.25, [(105.6, 103.8375), (105.6, 103.55), (107.7, 103.55)], F),  # VOUT to C4
    ("VBAT", 0.25, [(103.6, 103.8375), (103.6, 103.55), (101.5, 103.55)], F),  # VIN to C3
    ("/LX1", 0.3, [(104.1, 103.8375), (104.1, 102.45)], F),
    ("/LX2", 0.3, [(105.1, 103.8375), (105.1, 102.45)], F),
    ("/CFG1", 0.2, [(104.6, 106.2625), (104.6, 108.04)], F),
    ("/CFG2", 0.2, [(105.1, 106.2625), (105.1, 106.95), (105.6, 107.45), (105.6, 108.04)], F),
    ("/CFG3", 0.2, [(105.6, 106.2625), (105.6, 106.65), (106.6, 107.65), (106.6, 108.04)], F),
    ("VBAT", 0.25, [(104.1, 106.55), (103.6, 106.55)], F),                    # SEL and EN to VIN
    ("VBAT", 0.25, [(103.6, 106.55), (103.6, 107.05), (103.3, 107.35), (100.5, 107.35), (100.5, 103.45),
                    (101.025, 103.45)], F),
    ("GND", 0.3, [(104.6, 109.06), (107.3, 109.06)], F),                      # R1-R3 to GND
    # 3V3: C4 -> C5 -> trunk along the top edge to pin 1; branch at x 110.3 for the pull-ups R4, R6, R5
    ("+3V3", 0.3, [(107.7, 103.475), (108.6, 103.475), (109.4, 103.79)], F),
    ("+3V3", 0.3, [(109.4, 103.79), (109.4, 101.12), (115.5, 101.12)], F),
    ("+3V3", 0.3, [(110.3, 101.12), (110.3, 110.2), (113.09, 110.2)], F),
    ("+3V3", 0.3, [(110.3, 103.1), (112.79, 103.1)], F),                      # R4
    ("+3V3", 0.3, [(110.3, 107.05), (111.09, 107.05)], F),                    # R6
    ("GND", 0.3, [(109.4, 104.81), (109.4, 105.7)], F),                       # C5
    # pin 1: C6; pin 2: EN pull-up R4 and the stub to the EN test pad via
    ("GND", 0.2, [(114.3, 102.13), (114.7, 101.85), (117.55, 101.85)], F),    # C6, between pins 1 and 2
    ("/EN", 0.2, [(115.3, 102.9), (113.81, 103.1)], F),
    ("/EN", 0.2, [(116.6, 102.6), (117.3, 102.6)], F),
    # pin 3: battery sense, R9 from VBAT, C9 to GND at the pin
    ("/VBAT_SENSE", 0.2, [(115.3, 104.1), (114.4, 104.2), (113.31, 104.2)], F),
    ("GND", 0.25, [(114.4, 105.22), (113.6, 105.8)], F),                      # C9
    # pin 5: button filter R7 + C8, pull-up R6
    ("/BTN", 0.2, [(115.3, 107.1), (114.11, 107.05)], F),
    ("/BTN", 0.2, [(114.11, 107.05), (114.11, 108.1)], F),                    # R7 to C8
    ("/BTN_SW", 0.2, [(112.11, 107.05), (113.09, 107.05)], F),                # R6 to R7
    ("GND", 0.25, [(113.09, 108.1), (112.3, 108.3)], F),                      # C8
    # pin 6: LED series resistor; pin 7: GPIO8 strap; pin 8: stub to the BOOT test pad via
    ("/LED", 0.2, [(115.3, 108.85), (114.11, 109.15)], F),
    ("/STRAP8", 0.2, [(114.11, 110.2), (115.3, 110.1)], F),
    ("/BOOT", 0.2, [(116.6, 111.6), (117.3, 111.6)], F),
    # battery input: BAT+ pad (bottom) -> via -> Q1 drain; Q1 source -> C1 -> converter input and R9 (bottom side)
    ("/BAT+", 0.5, [(101.9, 110.2), (101.6, 109.2)], B),
    ("/BAT+", 0.5, [(101.9, 110.2), (101.9, 110.9)], F),
    ("GND", 0.3, [(100.95, 113.0), (100.9, 111.9)], F),                       # Q1 gate
    ("VBAT", 0.4, [(102.85, 113.338), (103.6, 113.35), (104.5, 113.375)], F),  # Q1 source to C1
    ("VBAT", 0.4, [(103.6, 113.35), (103.6, 107.95), (103.0, 107.35)], B),    # to the converter input
    ("VBAT", 0.3, [(103.0, 107.35), (103.75, 106.6), (110.4, 106.6), (111.5, 105.5), (111.5, 104.7)], B),
    ("VBAT", 0.25, [(111.5, 104.7), (112.29, 104.2)], F),                     # R9
    ("GND", 0.3, [(104.5, 111.825), (105.4, 111.4)], F),                      # C1
    # button: both pads of each contact; BTN_SW from R6 / R7 on the bottom side, under the LED and strap rows
    ("/BTN_SW", 0.25, [(107.525, 111.525), (111.675, 111.525)], F),
    ("GND", 0.3, [(107.525, 113.675), (111.675, 113.675)], F),
    ("/BTN_SW", 0.2, [(112.11, 107.05), (112.6, 106.25)], F),
    ("/BTN_SW", 0.2, [(112.6, 106.25), (111.5, 107.35), (111.5, 109.6), (110.75, 110.35), (110.75, 110.9)], B),
    ("/BTN_SW", 0.25, [(110.75, 110.9), (111.675, 111.525)], F),
    # LED below the strap row, LED_A on the bottom side
    ("/LED_A", 0.2, [(113.09, 109.15), (112.2, 109.45)], F),
    ("/LED_A", 0.2, [(112.2, 109.45), (112.75, 110.0), (112.75, 111.2)], B),
    ("/LED_A", 0.2, [(112.75, 111.2), (113.6, 111.963)], F),
    ("GND", 0.3, [(113.6, 113.537), (114.5, 113.9)], F),                      # D1 cathode
    # right of the module: inward stubs to vias next to the pads (UART, USB)
    ("/USB_DP", 0.2, [(132.8, 107.1), (132.1, 107.1)], F),
    ("/USB_DN", 0.2, [(132.8, 108.6), (132.1, 108.6)], F),
    ("/TXD0", 0.2, [(132.8, 110.1), (132.1, 110.1)], F),
    ("/RXD0", 0.2, [(132.8, 111.6), (132.1, 111.6)], F),
    # test pads on the bottom side, under the module
    ("+3V3", 0.3, [(112.5, 101.12), (112.9, 100.75), (120.8, 100.75), (120.8, 108.8), (121.5, 109.5)], B),
    ("/EN", 0.2, [(117.3, 102.6), (118.2, 103.5), (118.2, 108.75), (119.0, 109.5)], B),
    ("/BOOT", 0.2, [(117.3, 111.6), (118.9, 112.1)], B),
    ("/USB_DP", 0.2, [(132.1, 107.1), (128.0, 107.1), (127.0, 108.1), (127.0, 109.1)], B),
    ("/USB_DN", 0.2, [(132.1, 108.6), (130.5, 108.6), (129.7, 109.4)], B),
    ("/TXD0", 0.2, [(132.1, 110.1), (131.3, 110.9), (128.0, 110.9), (127.3, 111.6)], B),
    ("/RXD0", 0.2, [(132.1, 111.6), (130.3, 111.6), (129.8, 112.1)], B),
]
# GND vias: the pours connect them
VIAS = [("GND", 102.8, 105.05), ("GND", 106.4, 105.05), ("GND", 107.3, 109.06), ("GND", 109.4, 105.7),
        ("GND", 113.6, 105.8), ("GND", 112.3, 108.3), ("GND", 109.6, 113.675), ("GND", 114.5, 113.9),
        ("GND", 100.9, 111.9), ("GND", 105.4, 111.4),
        ("/BAT+", 101.9, 110.2), ("VBAT", 103.6, 113.35), ("VBAT", 103.0, 107.35), ("VBAT", 111.5, 104.7),
        ("+3V3", 112.5, 101.12), ("/BTN_SW", 112.6, 106.25), ("/BTN_SW", 110.75, 110.9),
        ("/LED_A", 112.2, 109.45), ("/LED_A", 112.75, 111.2),
        ("/EN", 117.3, 102.6), ("/BOOT", 117.3, 111.6),
        ("/USB_DP", 132.1, 107.1), ("/USB_DN", 132.1, 108.6), ("/TXD0", 132.1, 110.1), ("/RXD0", 132.1, 111.6)]

# reference designators shown on the silkscreen: ref -> (x, y) or None (footprint default)
SILK_REFS = {"U1": (124.7, 111.0)}

# silkscreen labels of the test pads (bottom side): above the pads of the upper row, below those of the lower row
_UP = -1.35
TP_LABEL = {"TP5": ("EN", 0, _UP), "TP1": ("3V3", 0, _UP), "TP8": ("D+", 0, _UP), "TP7": ("D-", 0, _UP),
            "TP6": "BOOT", "TP2": "GND", "TP3": "TX", "TP4": "RX"}

# top layer under the module body: no tracks (ground under the module, Espressif guideline); the margins next to
# the pads stay free for the stubs and their vias
UNDER_MODULE = [(117.7, 100.4), (131.7, 100.4), (131.7, 112.6), (117.7, 112.6)]

# silkscreen texts: (text, x, y, layer, size, thickness, angle)
TEXTS_PCB = [("Made by Haxeko", 125.0, 101.4, B, 0.8, 0.12, 0),
             (f"CR123A mini rev {REV}", 125.0, 102.6, B, 0.6, 0.1, 0),
             ("BAT+", 101.7, 103.8, B, 0.6, 0.1, 0), ("BAT-", 132.5, 111.95, B, 0.6, 0.1, 0)]
