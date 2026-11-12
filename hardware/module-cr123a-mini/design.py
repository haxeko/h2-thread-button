"""Board module-cr123a-mini: ESP32-H2-WROOM-02C button as long as one CR123A cell, the cell in the enclosure.

Single source of this board for the shared scripts of ../scripts (gen_project.py, gen_sch.py, gen_pcb.py,
gen_fab.py): the circuit (../scripts/circuit.py, adapted below) and the layout.

Board 34.5 x 14.8 mm (the length of a CR123A), 2 layers, 1.6 mm; the module antenna (6 mm) overhangs the top edge:
34.5 x 20.8 mm in all. The button (SW1) and the LED sit at the top edge, the antenna side, in the corner away from
the antenna. The cell lies along the bottom edge in the enclosure, whose battery contacts are wired to two pads on
the bottom side at that edge: BAT+ at the left end, BAT- (GND) at the right end. Q1 still protects against a
reversed cell.

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
The TPS63900 corner is that of the other boards turned by 90 degrees clockwise (seen from the top), with C3 and C4
closer to U2: straight tracks from the exposed pad, no vias in between. Every track is drawn here: the FreeRouting step
of gen_pcb.py has nothing left to route.
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
BAT_PLUS = (102.4, 113.4)   # BAT+ pad centre on the board (bottom side, bottom edge, left end): the footprint origin
BAT_MINUS = (132.5, 113.4)  # BAT- pad centre (bottom side, bottom edge, right end)
# The footprint sits on the bottom side (mirrored): local x = origin x - board x
CUSTOM_FOOTPRINTS = [dict(
    name=BAT_FP,
    descr="Wire pads of a CR123A that sits in the enclosure: pad 1 cell +, pad 2 cell - (GND), "
          "30.1 mm apart along the bottom edge; bottom side, no paste (hand soldered wires or the enclosure's "
          "contacts)",
    pads=[("1", 0, 0, 3.6, 1.6),
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
    # top edge (antenna side), left corner, as far from the antenna as the board allows: button, LED beside it
    "SW1": (102.95, 101.95, 0, F),
    "D1": (107.35, 101.55, 0, F),
    # TPS63900 below the button (U2 turned by 180 degrees: VOUT LX2 GND LX1 VIN on its left side from the top,
    # CFG3 CFG2 CFG1 SEL EN on its right side): L1 at the left edge, C4 (3V3) above, C3 (VIN) below, R1-R3 right;
    # C5 (3V3) between the button and L1
    "U2": (105.0, 107.4, 180, F),
    "L1": (101.65, 107.4, 90, F),
    "C4": (104.6, 105.05, 0, F),
    "C3": (104.6, 109.75, 0, F),
    "R1": (108.5, 107.4, 0, F),
    "R2": (108.5, 106.4, 0, F),
    "R3": (108.5, 105.4, 0, F),
    "C5": (101.55, 104.6, 180, F),
    # bottom edge, left: battery input (Q1 drain right above the BAT+ pad on the bottom side, C1)
    "Q1": (102.0, 112.75, 270, F),
    "C1": (104.8, 112.75, 270, F),
    # left of the module, one row per pin: C6 (pin 1, 3V3), R4 (pin 2, EN), C9 + R9 (pin 3, battery sense),
    # R7 + C8 (pin 5, button filter), R8 (pin 6, LED), R5 (pin 7, GPIO8 strap); R6 (button pull-up) at the top,
    # between the button line and the 3V3 trunk
    "C6": (114.3, 101.62, 270, F),
    "R6": (111.6, 101.9, 270, F),
    "R4": (113.3, 103.1, 0, F),
    "R9": (112.8, 104.2, 0, F),
    "C9": (114.4, 104.71, 270, F),
    "R7": (113.6, 107.05, 0, F),
    "C8": (113.6, 108.1, 180, F),
    "R8": (113.6, 109.15, 180, F),
    "R5": (113.6, 110.2, 0, F),
    # test pads, bottom side (pogo pins), under the module: EN, 3V3, D+, D- (upper row), BOOT, GND, TX, RX
    "TP5": (119.5, 109.6, 0, B), "TP1": (122.0, 109.6, 0, B), "TP8": (127.0, 109.6, 0, B),
    "TP7": (129.5, 109.6, 0, B),
    "TP6": (119.5, 112.2, 0, B), "TP2": (122.0, 112.2, 0, B), "TP3": (127.0, 112.2, 0, B),
    "TP4": (129.5, 112.2, 0, B),
}

# Hand-routed tracks (top layer unless "B"): every connection but GND (the pours connect it).
# (net, width, [points], layer)
ROUTES = [
    # button: both BTN_SW pads (top pair), then along the top edge over the LED to the lane at x 110.2, down to R7;
    # R6 hangs on it at the top. GND pads (bottom pair) to C5 and to the LED cathode
    ("/BTN_SW", 0.25, [(100.875, 100.875), (105.025, 100.875)], F),
    ("/BTN_SW", 0.2, [(105.025, 100.6), (110.2, 100.6), (110.2, 107.05), (113.09, 107.05)], F),
    ("/BTN_SW", 0.2, [(110.2, 102.41), (111.6, 102.41)], F),
    ("GND", 0.3, [(100.875, 103.025), (100.8, 104.6)], F),
    ("GND", 0.25, [(105.025, 103.025), (106.0, 102.4), (106.5625, 101.55)], F),
    # LED: anode down the lane at x 109.6 to R8
    ("/LED_A", 0.2, [(108.1375, 101.55), (109.6, 101.55), (109.6, 109.15), (113.09, 109.15)], F),
    # 3V3 at the converter: C5, C4 and the via to the bottom-side line to the module corner
    ("+3V3", 0.3, [(102.325, 104.6), (103.1, 104.6), (103.6, 105.05)], F),
    ("+3V3", 0.3, [(103.1, 103.55), (103.1, 104.6)], F),
    # TPS63900, the layout of the other boards turned by 90 degrees clockwise
    ("+3V3", 0.25, [(103.7875, 106.4), (103.8, 105.05)], F),                  # VOUT to C4
    ("/LX2", 0.3, [(103.7875, 106.9), (102.5, 106.9)], F),
    ("/LX1", 0.3, [(103.7875, 107.9), (102.5, 107.9)], F),
    ("GND", 0.25, [(103.7875, 107.4), (105.0, 107.4)], F),                    # pin 8 to exposed pad
    ("GND", 0.3, [(105.0, 107.4), (105.0, 105.05)], F),                       # exposed pad to C4
    ("GND", 0.3, [(105.0, 107.4), (105.0, 109.75)], F),                       # exposed pad to C3
    ("VBAT", 0.25, [(103.7875, 108.4), (103.8, 109.75)], F),                  # VIN to C3
    ("/CFG1", 0.2, [(106.2125, 107.4), (107.99, 107.4)], F),
    ("/CFG2", 0.2, [(106.2125, 106.9), (106.9, 106.9), (107.4, 106.4), (107.99, 106.4)], F),
    ("/CFG3", 0.2, [(106.2125, 106.4), (106.6, 106.4), (107.6, 105.4), (107.99, 105.4)], F),
    ("GND", 0.3, [(109.01, 105.4), (109.01, 107.9), (108.75, 108.35)], F),    # R1-R3 to GND
    ("VBAT", 0.25, [(106.5, 107.9), (106.5, 110.6)], F),                      # SEL and EN to VBAT
    # battery input: BAT+ pad (bottom side) -> via -> Q1 drain; Q1 source -> VBAT line along y 110.6 (C3, C1, SEL
    # and EN, via to R9)
    ("/BAT+", 0.5, [(102.0, 113.6), (101.0, 113.6)], F),
    ("VBAT", 0.3, [(101.05, 111.812), (101.05, 110.6), (107.2, 110.6)], F),
    ("VBAT", 0.3, [(103.8, 109.75), (103.8, 110.6)], F),                      # C3
    ("VBAT", 0.3, [(104.8, 110.6), (104.8, 111.975)], F),                     # C1
    ("GND", 0.3, [(102.95, 111.812), (103.6, 111.9)], F),                     # Q1 gate
    ("GND", 0.3, [(104.8, 113.525), (105.6, 113.9)], F),                      # C1
    # 3V3 at the module: R6 -> trunk along the top edge to C6 and pin 1; via from the converter, R4
    ("+3V3", 0.3, [(111.6, 101.39), (111.6, 101.12), (115.5, 101.12)], F),
    ("+3V3", 0.3, [(112.6, 101.12), (112.6, 102.25), (112.79, 103.1)], F),
    # pin 1: C6; pin 2: EN pull-up R4 and the stub to the EN test pad via
    ("GND", 0.2, [(114.3, 102.13), (114.7, 101.85), (117.55, 101.85)], F),    # C6, between pins 1 and 2
    ("/EN", 0.2, [(115.3, 102.9), (113.81, 103.1)], F),
    ("/EN", 0.2, [(116.6, 102.6), (117.3, 102.6)], F),
    # pin 3: battery sense, R9 from VBAT (via), C9 to GND at the pin
    ("/VBAT_SENSE", 0.2, [(115.3, 104.1), (114.4, 104.2), (113.31, 104.2)], F),
    ("GND", 0.25, [(114.4, 105.22), (113.6, 105.8)], F),                      # C9
    ("VBAT", 0.25, [(111.1, 104.7), (111.6, 104.2), (112.29, 104.2)], F),
    # pin 5: button filter R7 + C8
    ("/BTN", 0.2, [(115.3, 107.1), (114.11, 107.05)], F),
    ("/BTN", 0.2, [(114.11, 107.05), (114.11, 108.1)], F),                    # R7 to C8
    ("GND", 0.25, [(113.09, 108.1), (112.6, 108.25)], F),                     # C8
    # pin 6: LED series resistor; pin 7: GPIO8 strap (3V3 from the bottom side); pin 8: stub to the BOOT via
    ("/LED", 0.2, [(115.3, 108.85), (114.11, 109.15)], F),
    ("/STRAP8", 0.2, [(114.11, 110.2), (115.3, 110.1)], F),
    ("+3V3", 0.25, [(112.3, 110.95), (113.09, 110.2)], F),
    ("/BOOT", 0.2, [(116.6, 111.6), (117.3, 111.6)], F),
    # right of the module: inward stubs to vias next to the pads (UART, USB)
    ("/USB_DP", 0.2, [(132.8, 107.1), (132.1, 107.1)], F),
    ("/USB_DN", 0.2, [(132.8, 108.6), (132.1, 108.6)], F),
    ("/TXD0", 0.2, [(132.8, 110.1), (132.1, 110.1)], F),
    ("/RXD0", 0.2, [(132.8, 111.6), (132.1, 111.6)], F),
    # bottom side: 3V3 from the converter to the module corner, on to TP1 and down to R5
    ("+3V3", 0.3, [(103.1, 103.55), (104.4, 102.25), (112.6, 102.25)], B),
    ("+3V3", 0.3, [(112.6, 102.25), (114.1, 100.75), (120.8, 100.75), (120.8, 108.8), (121.5, 109.5)], B),
    ("+3V3", 0.3, [(112.6, 102.25), (111.9, 102.95), (111.9, 110.55), (112.3, 110.95)], B),
    # bottom side: VBAT to R9 (battery sense)
    ("VBAT", 0.3, [(107.2, 110.6), (109.9, 110.6), (111.1, 109.4), (111.1, 104.7)], B),
    # test pads on the bottom side, under the module
    ("/EN", 0.2, [(117.3, 102.6), (118.2, 103.5), (118.2, 108.75), (119.0, 109.5)], B),
    ("/BOOT", 0.2, [(117.3, 111.6), (118.9, 112.1)], B),
    ("/USB_DP", 0.2, [(132.1, 107.1), (128.0, 107.1), (127.0, 108.1), (127.0, 109.1)], B),
    ("/USB_DN", 0.2, [(132.1, 108.6), (130.5, 108.6), (129.7, 109.4)], B),
    ("/TXD0", 0.2, [(132.1, 110.1), (131.3, 110.9), (128.0, 110.9), (127.3, 111.6)], B),
    ("/RXD0", 0.2, [(132.1, 111.6), (130.3, 111.6), (129.8, 112.1)], B),
]
# GND vias: the pours connect them
VIAS = [("GND", 101.9, 103.55), ("GND", 106.8, 103.4), ("GND", 106.1, 104.6), ("GND", 108.75, 108.35),
        ("GND", 103.6, 111.9), ("GND", 105.6, 113.9), ("GND", 113.6, 105.8), ("GND", 112.6, 108.25),
        ("/BAT+", 101.0, 113.6), ("VBAT", 107.2, 110.6), ("VBAT", 111.1, 104.7),
        ("+3V3", 103.1, 103.55), ("+3V3", 112.6, 102.25), ("+3V3", 112.3, 110.95),
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
             ("BAT+", 102.0, 111.85, B, 0.6, 0.1, 0), ("BAT-", 132.5, 111.95, B, 0.6, 0.1, 0)]
