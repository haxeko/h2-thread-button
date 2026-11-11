#!/usr/bin/env python3
"""Generate the KiCad project settings (.kicad_pro: design rules, net classes), the project library
lib/matter_button.{kicad_sym,pretty} and the project library tables of a board. Run from the board folder:
  cd hardware/<board> && python3 ../scripts/gen_project.py

- ESP32-H2-WROOM-02C symbol and footprint: not in the KiCad 9 library. Land pattern from the module datasheet
  v1.2, chapter 11.1 (18 x 20 mm, 28 castellated pads 1.5 x 0.9 mm, pitch 1.5 mm, thermal pad 29 in two parts).
- VBAT: power symbol for the battery rail (KiCad has +BATT, not VBAT).
- Battery holder copies (design.CUSTOM_FOOTPRINTS): a stock coin cell holder footprint has two pads "1" (the two
  tabs of the same metal clip). KiCad 9 would ask for a copper connection between them around the cell, so the copy
  leaves one tab unnumbered (soldered, mechanical only).
"""

import json
import os

from kicad_sexp import HW, KICAD_FP, effects, num, q, stock_symbol, uid, write  # first: finds design.py

import design
from design import GROUND_NETS, LIB, POWER_NETS, PROJECT

DATASHEET = "https://www.espressif.com/sites/default/files/documentation/esp32-h2-wroom-02c_datasheet_en.pdf"


# ------------------------------------------------------------------------------------------------- symbols
def pin(kind, x, y, angle, length, name, number, hide_name=False):
    nm = effects(hide=False) if not hide_name else effects(hide=True)
    return (f"\t\t\t(pin {kind} line (at {num(x)} {num(y)} {angle}) (length {num(length)})\n"
            f"\t\t\t\t(name {q(name)} {nm})\n"
            f"\t\t\t\t(number {q(number)} {effects()})\n"
            f"\t\t\t)\n")


def prop(name, value, x, y, hide=False, justify=None):
    return f"\t\t(property {q(name)} {q(value)} (at {num(x)} {num(y)} 0) {effects(hide=hide, justify=justify)})\n"


def module_symbol():
    L, R = -17.78, 17.78
    left = [  # (number, name, type, y)
        ("1", "3V3", "power_in", 22.86), ("14", "VBAT", "power_in", 20.32), ("2", "EN", "input", 15.24),
        ("7", "IO8", "bidirectional", 10.16), ("8", "IO9", "bidirectional", 7.62),
        ("5", "IO10", "bidirectional", 2.54), ("6", "IO11", "bidirectional", 0),
        ("10", "IO12", "bidirectional", -2.54), ("11", "IO13", "bidirectional", -5.08),
        ("12", "IO14", "bidirectional", -7.62),
        ("16", "NC", "no_connect", -12.7), ("17", "NC", "no_connect", -15.24),
        ("18", "NC", "no_connect", -17.78), ("19", "NC", "no_connect", -20.32),
    ]
    right = [
        ("28", "IO0", 22.86), ("27", "IO1/ADC1_CH0", 20.32), ("26", "IO2", 17.78), ("25", "IO3", 15.24),
        ("3", "IO4", 12.7), ("4", "IO5", 10.16), ("15", "IO22", 5.08), ("20", "IO25", 2.54),
        ("21", "RXD0/IO23", -2.54), ("22", "TXD0/IO24", -5.08), ("23", "IO26/USB_D-", -10.16),
        ("24", "IO27/USB_D+", -12.7),
    ]
    out = ["\t(symbol \"ESP32-H2-WROOM-02C\"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n",
           prop("Reference", "U", -12.7, 29.21, justify="left"),
           prop("Value", "ESP32-H2-WROOM-02C", -12.7, 26.67, justify="left"),
           prop("Footprint", f"{LIB}:ESP32-H2-WROOM-02C", 0, -38.1, hide=True),
           prop("Datasheet", DATASHEET, 0, -40.64, hide=True),
           prop("Description", "ESP32-H2 module, 802.15.4 (Thread, Zigbee) + Bluetooth LE 5.3, 4 MB flash, PCB "
                "antenna, 18 x 20 mm", 0, -43.18, hide=True),
           prop("ki_keywords", "ESP32-H2 Thread Zigbee Matter BLE RISC-V module", 0, 0, hide=True),
           prop("ki_fp_filters", "ESP32?H2?WROOM?02C*", 0, 0, hide=True),
           "\t\t(symbol \"ESP32-H2-WROOM-02C_0_1\"\n"
           "\t\t\t(rectangle (start -12.7 25.4) (end 12.7 -27.94) (stroke (width 0.254) (type default)) "
           "(fill (type background)))\n\t\t)\n",
           "\t\t(symbol \"ESP32-H2-WROOM-02C_1_1\"\n"]
    for n, name, kind, y in left:
        out.append(pin(kind, L, y, 0, 5.08, name, n))
    for n, name, y in right:
        out.append(pin("bidirectional", R, y, 180, 5.08, name, n))
    for n, x in (("9", -2.54), ("13", 0), ("29", 2.54)):
        out.append(pin("power_in", x, -33.02, 90, 5.08, "GND", n))
    out.append("\t\t)\n\t\t(embedded_fonts no)\n\t)\n")
    return "".join(out)


def vbat_symbol():
    """Power symbol for the battery rail after the reverse polarity MOSFET (net VBAT), drawn like +3V3."""
    s = stock_symbol("power:+3V3").replace('"+3V3', '"VBAT')
    desc = f'(property "Description" "Battery rail ({design.BATTERY} after Q1). '
    s = s.replace('(property "Description" "', desc, 1)
    return "\t" + s.replace("\n", "\n\t") + "\n"


def write_symbols():
    text = ("(kicad_symbol_lib\n\t(version 20241209)\n\t(generator \"kicad_symbol_editor\")\n"
            "\t(generator_version \"9.0\")\n" + module_symbol() + vbat_symbol() + ")\n")
    write(os.path.join(HW, "lib", LIB + ".kicad_sym"), text)


# ---------------------------------------------------------------------------------------------- footprints
def fp_line(name, x1, y1, x2, y2, layer, w):
    return (f"\t(fp_line (start {num(x1)} {num(y1)}) (end {num(x2)} {num(y2)}) "
            f"(stroke (width {num(w)}) (type solid)) (layer {q(layer)}) (uuid {q(uid(name, layer, x1, y1, x2, y2))}))\n")


def fp_rect(name, x1, y1, x2, y2, layer, w):
    return (f"\t(fp_rect (start {num(x1)} {num(y1)}) (end {num(x2)} {num(y2)}) "
            f"(stroke (width {num(w)}) (type solid)) (fill no) (layer {q(layer)}) "
            f"(uuid {q(uid(name, 'rect', layer, x1, y1))}))\n")


def fp_text(name, text, x, y, layer, size=1.0, thick=0.15):
    return (f"\t(fp_text user {q(text)} (at {num(x)} {num(y)} 0) (layer {q(layer)}) "
            f"(uuid {q(uid(name, 'text', text, layer))}) {effects(size, thickness=thick)})\n")


def fp_prop(name, key, value, x, y, layer, hide=False):
    h = " (hide yes)" if hide else ""
    return (f"\t(property {q(key)} {q(value)} (at {num(x)} {num(y)} 0) (layer {q(layer)}){h} "
            f"(uuid {q(uid(name, 'prop', key))}) {effects(1.0, thickness=0.15)})\n")


def smd(name, number, x, y, w, h, paste=True, extra=""):
    layers = '"F.Cu" "F.Mask" "F.Paste"' if paste else '"F.Cu" "F.Mask"'
    return (f"\t(pad {q(number)} smd rect (at {num(x)} {num(y)}) (size {num(w)} {num(h)}) (layers {layers}){extra} "
            f"(uuid {q(uid(name, 'pad', number, x, y))}))\n")


def via_pad(name, number, x, y, d=0.6, drill=0.3):
    return (f"\t(pad {q(number)} thru_hole circle (at {num(x)} {num(y)}) (size {num(d)} {num(d)}) "
            f"(drill {num(drill)}) (layers \"*.Cu\") (remove_unused_layers no) (zone_connect 2) "
            f"(uuid {q(uid(name, 'via', number, x, y))}))\n")


MODULE_DESCR = ("ESP32-H2-WROOM-02C module, 18 x 20 mm, land pattern of the datasheet v1.2 chapter 11.1. "
                "Antenna area (y -10 .. -4): no copper on any layer, best outside the board edge. " + DATASHEET)


def module_footprint():
    """Origin = module centre. Antenna end at y = -10 (antenna area y -10 .. -4), pads 10-19 at y = +9.75."""
    n = "ESP32-H2-WROOM-02C"
    o = [f"(footprint {q(n)}\n\t(version 20241229)\n\t(generator \"pcbnew\")\n\t(generator_version \"9.0\")\n"
         "\t(layer \"F.Cu\")\n"
         f"\t(descr {q(MODULE_DESCR)})\n"
         "\t(tags \"ESP32-H2 Espressif Thread Zigbee Matter BLE module\")\n",
         fp_prop(n, "Reference", "REF**", 0, 11.9, "F.SilkS"),
         fp_prop(n, "Value", n, 0, 1.0, "F.Fab"),
         fp_prop(n, "Datasheet", DATASHEET, 0, 0, "F.Fab", hide=True),
         fp_prop(n, "Description", "ESP32-H2 module 802.15.4 + BLE, PCB antenna", 0, 0, "F.Fab", hide=True),
         "\t(attr smd)\n"]
    # fabrication outline, antenna boundary, pin 1 chamfer
    o.append(fp_line(n, -9, -10, 9, -10, "F.Fab", 0.1))
    o.append(fp_line(n, 9, -10, 9, 10, "F.Fab", 0.1))
    o.append(fp_line(n, 9, 10, -9, 10, "F.Fab", 0.1))
    o.append(fp_line(n, -9, 10, -9, -3.4, "F.Fab", 0.1))
    o.append(fp_line(n, -9, -3.4, -8.4, -4, "F.Fab", 0.1))
    o.append(fp_line(n, -9, -4, -9, -10, "F.Fab", 0.1))
    o.append(fp_line(n, -8.4, -4, 9, -4, "F.Fab", 0.1))
    o.append(fp_text(n, "ANTENNA (no copper)", 0, -7, "F.Fab", 1.0))
    o.append(fp_text(n, "${REFERENCE}", 0, 7.0, "F.Fab", 1.0))
    # silkscreen: bottom corners and pin 1 dot only, the antenna end overhangs the board edge (outline on F.Fab)
    s = 9.11
    o.append(fp_line(n, -s, 9.8, -s, 10.11, "F.SilkS", 0.12))
    o.append(fp_line(n, -s, 10.11, -7.45, 10.11, "F.SilkS", 0.12))
    o.append(fp_line(n, s, 9.8, s, 10.11, "F.SilkS", 0.12))
    o.append(fp_line(n, s, 10.11, 7.45, 10.11, "F.SilkS", 0.12))
    o.append(f"\t(fp_circle (center -7.45 -2.9) (end -7.3 -2.9) (stroke (width 0.3) (type solid)) (fill yes) "
             f"(layer \"F.SilkS\") (uuid {q(uid(n, 'pin1dot'))}))\n")
    o.append(fp_rect(n, -9.75, -10.25, 9.75, 10.75, "F.CrtYd", 0.05))
    # pads: 1-9 left (top to bottom), 10-19 bottom (left to right), 20-28 right (bottom to top)
    for i in range(1, 10):
        o.append(smd(n, i, -8.75, -2.9 + (i - 1) * 1.5, 1.5, 0.9))
    for i in range(10, 20):
        o.append(smd(n, i, -6.75 + (i - 10) * 1.5, 9.75, 0.9, 1.5))
    for i in range(20, 29):
        o.append(smd(n, i, 8.75, 9.1 - (i - 20) * 1.5, 1.5, 0.9))
    # thermal pad 29 (GND): two parts, solid zone connection, tented thermal vias in the large part
    o.append(smd(n, 29, -0.47, 2.01, 2.8, 0.55, extra=" (zone_connect 2)"))
    o.append(smd(n, 29, -0.47, 3.73, 2.8, 1.6, extra=" (solder_paste_margin_ratio -0.1) (zone_connect 2)"))
    for x in (-1.47, -0.47, 0.53):  # thermal vias of the datasheet land pattern, tented on the bottom side
        o.append(via_pad(n, 29, x, 2.01, d=0.5))
        o.append(via_pad(n, 29, x, 3.73))
    # antenna keep-out
    o.append("\t(zone (net 0) (net_name \"\") (layers \"F.Cu\" \"B.Cu\") "
             f"(uuid {q(uid(n, 'antenna-keepout'))}) (name \"antenna\") (hatch full 0.508)\n"
             "\t\t(connect_pads (clearance 0)) (min_thickness 0.254) (filled_areas_thickness no)\n"
             "\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) "
             "(footprints allowed))\n"
             "\t\t(placement (enabled no) (sheetname \"\"))\n"
             "\t\t(fill (thermal_gap 0.508) (thermal_bridge_width 0.508))\n"
             "\t\t(polygon (pts (xy -9 -10) (xy 9 -10) (xy 9 -4) (xy -9 -4)))\n\t)\n")
    o.append("\t(embedded_fonts no)\n)\n")
    return "".join(o)


def holder_footprint(f):
    """Copy of a stock footprint (f["stock"], "Lib:Name") renamed f["name"], the pad "1" at f["unnumber"] (x, y)
    left unnumbered."""
    lib, name = f["stock"].split(":")
    with open(os.path.join(KICAD_FP, lib + ".pretty", name + ".kicad_mod")) as fh:
        s = fh.read()
    s = s.replace(f'(footprint "{name}"', f'(footprint "{f["name"]}"', 1)
    if f.get("unnumber"):
        x, y = f["unnumber"]
        s = s.replace('(descr "', f'(descr "Copy of {f["stock"]} with the tab at ({num(x)}, {num(y)}) unnumbered '
                      '(same metal clip as pad 1, soldered for strength only). ', 1)
        old = f'(pad "1" smd rect\n\t\t(at {num(x)} {num(y)})'
        assert old in s, f"stock footprint {f['stock']} changed"
        s = s.replace(old, f'(pad "" smd rect\n\t\t(at {num(x)} {num(y)})')
    for text in f.get("drop_silk_text", []):  # e.g. a polarity mark that would land outside the board
        s = s.replace('(descr "', f'(descr "Copy of {f["stock"]} without the silkscreen text {text}. ', 1)
        s = remove_blocks(s, lambda item: item.startswith(f'(fp_text user "{text}"') and '"F.SilkS"' in item,
                          ("fp_text",))
    if f.get("courtyard"):  # replace a courtyard KiCad 9 reports as malformed by one closed polygon
        s = remove_layer_graphics(s, "F.CrtYd")
        pts = " ".join(f"(xy {num(px)} {num(py)})" for px, py in f["courtyard"])
        poly = (f'\t(fp_poly (pts {pts}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") '
                f'(uuid {q(uid(f["name"], "courtyard"))}))\n')
        i = s.index("\t(pad ")
        s = s[:i] + poly + s[i:]
    return s


def remove_layer_graphics(text, layer):
    """Remove the graphic items (fp_line, fp_arc, fp_circle, fp_rect, fp_poly) drawn on `layer`."""
    return remove_blocks(text, lambda item: f'(layer "{layer}")' in item,
                         ("fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly"))


def _find_head(text, head, i):
    """Index of the next '(head' followed by white space (a block of that type) from i, -1 if none."""
    while True:
        k = text.find("(" + head, i)
        if k < 0 or text[k + 1 + len(head)].isspace():
            return k
        i = k + 1


def remove_blocks(text, match, heads):
    """Remove the balanced '(head ...' blocks for which match(block) is true, with their indentation and newline."""
    out, i = [], 0
    while True:
        j = min((k for k in (_find_head(text, h, i) for h in heads) if k >= 0), default=-1)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        depth = 0
        for e in range(j, len(text)):
            depth += text[e] == "("
            depth -= text[e] == ")"
            if depth == 0:
                break
        line = text.rfind("\n", i, j)
        start = line + 1 if line >= 0 and not text[line + 1:j].strip() else j  # the indentation goes too
        if match(text[j:e + 1]):
            out.append(text[i:start])
            i = e + 1
            if text[i:i + 1] == "\n":
                i += 1
        else:
            out.append(text[i:e + 1])
            i = e + 1


def write_footprints():
    d = os.path.join(HW, "lib", LIB + ".pretty")
    write(os.path.join(d, "ESP32-H2-WROOM-02C.kicad_mod"), module_footprint())
    for f in getattr(design, "CUSTOM_FOOTPRINTS", []):
        write(os.path.join(d, f["name"] + ".kicad_mod"), holder_footprint(f))


def write_tables():
    write(os.path.join(HW, "sym-lib-table"),
          f'(sym_lib_table\n\t(version 7)\n\t(lib (name "{LIB}") (type "KiCad") '
          f'(uri "${{KIPRJMOD}}/lib/{LIB}.kicad_sym") (options "") (descr "Project parts"))\n)\n')
    write(os.path.join(HW, "fp-lib-table"),
          f'(fp_lib_table\n\t(version 7)\n\t(lib (name "{LIB}") (type "KiCad") '
          f'(uri "${{KIPRJMOD}}/lib/{LIB}.pretty") (options "") (descr "Project footprints"))\n)\n')


# ------------------------------------------------------------------------------------------------- project
def netclass(name, track, priority):
    return {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": name,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": priority, "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": track, "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6}


def write_project():
    """Design rules for a standard 2-layer 1.6 mm board (JLCPCB / PCBWay standard process: 0.127 mm track and
    space, 0.3 mm drill). Routing uses 0.2 mm clearance, 0.2 mm signal and 0.3 mm power tracks, 0.6/0.3 mm vias."""
    pro = {
        "board": {"design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "silk_line_width": 0.12,
                         "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12,
                         "fab_line_width": 0.1, "courtyard_line_width": 0.05, "zones": {"min_clearance": 0.25}},
            "diff_pair_dimensions": [], "drc_exclusions": [], "meta": {"version": 2},
            "rules": {"max_error": 0.005, "min_clearance": 0.15, "min_connection": 0.0,
                      "min_copper_edge_clearance": 0.3, "min_groove_width": 0.0, "min_hole_clearance": 0.25,
                      "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
                      "min_resolved_spokes": 1, "min_silk_clearance": 0.0, "min_text_height": 0.6,
                      "min_text_thickness": 0.08, "min_through_hole_diameter": 0.3, "min_track_width": 0.15,
                      "min_via_annular_width": 0.1, "min_via_diameter": 0.5, "solder_mask_to_copper_clearance": 0.0,
                      "use_height_for_length_calcs": True},
            "track_widths": [0.0, 0.2, 0.3, 0.5],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}],
            "zones_allow_external_fillets": False}},
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 3},
        "net_settings": {
            "classes": [netclass("Default", 0.2, 2147483647), netclass("Power", 0.3, 0),
                        netclass("Ground", 0.3, 1)],
            "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in POWER_NETS] +
                                 [{"netclass": "Ground", "pattern": n} for n in GROUND_NETS]},
        "pcbnew": {"page_layout_descr_file": ""},
        "sheets": [[uid(PROJECT, "root-sheet"), "Root"]],
        "text_variables": {},
    }
    write(os.path.join(HW, PROJECT + ".kicad_pro"), json.dumps(pro, indent=2) + "\n")


if __name__ == "__main__":
    write_project()
    write_symbols()
    write_footprints()
    write_tables()
    print("library written to", os.path.join(HW, "lib"))
