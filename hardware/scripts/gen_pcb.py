#!/usr/bin/env python3
"""Generate, route and check the PCB of a board (KiCad 9 pcbnew API + FreeRouting). Run from the board folder:
  cd hardware/<board>

  python3 ../scripts/gen_pcb.py place     board from the schematic netlist: outline, placement, nets, rule areas,
                                          hand routes, texts
  python3 ../scripts/gen_pcb.py route     FreeRouting (Specctra DSN/SES) for what the hand routes leave open, GND
                                          pours both layers, stitching vias
  python3 ../scripts/gen_pcb.py pour      GND pours and stitching vias again (after a manual change)
  python3 ../scripts/gen_pcb.py all       place + route
  python3 ../scripts/gen_pcb.py sync      values and part numbers from the schematic onto the routed board

The footprints, values, nets and symbol links come from the netlist that kicad-cli exports from the schematic,
as "Update PCB from Schematic" would do, so DRC with --schematic-parity checks the board against the schematic.
The layout (outline, placement, hand routes, vias, rule areas, silkscreen) is in the board's design.py.
"""

import math
import os
import re
import subprocess
import sys

from kicad_sexp import HW, KICAD_FP  # first: finds design.py

import pcbnew

import design
from design import (KEEPOUT_RINGS, NO_STITCH, PLACE, ROUTES, SILK_REFS, SOLID_PADS, TEXTS_PCB, TP_LABEL,
                    UNDER_MODULE, VIAS)

PCB = os.path.join(HW, design.PROJECT + ".kicad_pcb")
SCH = os.path.join(HW, design.PROJECT + ".kicad_sch")
PRO = os.path.join(HW, design.PROJECT + ".kicad_pro")
# the project file as gen_project.py wrote it, read before pcbnew touches it: NewBoard and SaveBoard write every
# default setting into it
PRO_TEXT = open(PRO).read() if os.path.exists(PRO) else None
BUILD = os.path.join(HW, "build")  # intermediate files (git-ignored)
FREEROUTING = os.environ.get("FREEROUTING_JAR", os.path.expanduser("~/freerouting-2.1.0.jar"))
JOB_TIMEOUT = os.environ.get("FREEROUTING_TIMEOUT", "00:03:00")

X0, Y0, W, H, R_CORNER = design.OUTLINE  # board outline, mm
F, B = "F", "B"


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


# ------------------------------------------------------------------------------------------------- netlist
def read_netlist():
    os.makedirs(BUILD, exist_ok=True)
    path = os.path.join(BUILD, design.PROJECT + ".net")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", path, SCH],
                   check=True, capture_output=True)
    text = open(path).read()
    comps = {}
    for blk in text.split("(comp ")[1:]:
        blk = blk.split("(libparts")[0]
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        comps[ref] = dict(
            value=re.search(r'\(value "([^"]*)"\)', blk).group(1),
            footprint=re.search(r'\(footprint "([^"]*)"\)', blk).group(1),
            tstamp=re.findall(r'\(tstamps "([^"]+)"\)', blk)[-1],
            fields=dict(re.findall(r'\(field \(name "([^"]+)"\)\s*"([^"]*)"\)', blk)),
            dnp='(property (name "dnp")' in blk)
    nets = {}
    for blk in text.split("(net (code")[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        nets[name] = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', blk)
    return comps, nets


def load_footprint(lib_id):
    nick, name = lib_id.split(":")
    path = os.path.join(HW, "lib", nick + ".pretty") if nick == design.LIB else \
        os.path.join(KICAD_FP, nick + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {lib_id} not found in {path}")
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp


def save(board):
    """SaveBoard, then the project file back as gen_project.py wrote it (PRO_TEXT)."""
    pcbnew.SaveBoard(PCB, board)
    if PRO_TEXT is not None:
        with open(PRO, "w") as f:
            f.write(PRO_TEXT)


# --------------------------------------------------------------------------------------------------- board
def add_outline(board):
    """Rectangle with rounded corners on Edge.Cuts."""
    x1, y1, x2, y2, r = X0, Y0, X0 + W, Y0 + H, R_CORNER

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a))
        s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    seg((x1 + r, y1), (x2 - r, y1))
    seg((x2, y1 + r), (x2, y2 - r))
    seg((x2 - r, y2), (x1 + r, y2))
    seg((x1, y2 - r), (x1, y1 + r))
    k = r * (1 - math.sqrt(0.5))
    for cx, cy, sx, sy, ex, ey, mx, my in [
            (x1 + r, y1 + r, x1, y1 + r, x1 + r, y1, x1 + k, y1 + k),
            (x2 - r, y1 + r, x2 - r, y1, x2, y1 + r, x2 - k, y1 + k),
            (x2 - r, y2 - r, x2, y2 - r, x2 - r, y2, x2 - k, y2 - k),
            (x1 + r, y2 - r, x1 + r, y2, x1, y2 - r, x1 + k, y2 - k)]:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(pt(sx, sy), pt(mx, my), pt(ex, ey))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)


def polygon(zone, pts):
    ol = zone.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(x), mm(y))


def add_rule_area(board, name, layers, pts, tracks=False, vias=False, pour=False):
    """Rule area: what is NOT allowed inside."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowCopperPour(pour)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    polygon(z, pts)
    board.Add(z)


def add_track(board, net, width, pts, layer):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)


def add_via(board, net, x, y, locked=True):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetWidth(mm(0.6))
    v.SetDrill(mm(0.3))
    v.SetNet(net)
    v.SetLocked(locked)
    board.Add(v)


def add_text(board, text, x, y, layer, size=0.8, thick=0.12, angle=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetTextAngleDegrees(angle)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        t.SetMirrored(True)
    board.Add(t)


def set_fields(fp, c, side):
    """Schematic fields kept on the footprint (hidden, on the fab layer): part numbers for the BOM and the CPL."""
    for k in ("MPN", "LCSC", "Description"):
        if c["fields"].get(k):
            fp.SetField(k, c["fields"][k])
            f = fp.GetFieldByName(k)
            f.SetVisible(False)
            f.SetLayer(pcbnew.B_Fab if side == "B" else pcbnew.F_Fab)
        elif fp.HasField(k):
            fp.RemoveField(k)
    fp.SetDNP(c["dnp"])


def place():
    comps, nets = read_netlist()
    board = pcbnew.NewBoard(PCB)
    board.SetCopperLayerCount(2)
    tb = board.GetTitleBlock()
    tb.SetTitle(design.TITLE)
    tb.SetRevision(design.REV)
    tb.SetCompany(design.COMPANY)
    tb.SetDate(design.DATE)

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {(ref, pin): name for name, nodes in nets.items() for ref, pin in nodes}

    missing = set(comps) ^ set(PLACE)
    assert not missing, f"placement table and schematic differ: {missing}"
    for ref, c in sorted(comps.items()):
        fp = load_footprint(c["footprint"])
        board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["tstamp"]))
        fp.SetSheetname("/")
        fp.SetSheetfile(os.path.basename(SCH))
        x, y, rot, side = PLACE[ref]
        set_fields(fp, c, side)
        fp.Value().SetVisible(False)  # values are in the BOM; the assembly drawing shows the designators
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            net = pin_net.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netinfo[net])
            if (ref, pad.GetNumber()) in SOLID_PADS:  # e.g. coin cell contact: solid, no thermal spokes
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        # reference designators on the silkscreen for the larger parts only; the 0402/0603 passives are too
        # dense, see the assembly drawing (F.Fab) instead; the test pads get their function as label
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
        fp.Reference().SetTextThickness(mm(0.12))
        fp.Reference().SetVisible(ref in SILK_REFS)
        if ref in SILK_REFS and SILK_REFS[ref]:
            fp.Reference().SetPosition(pt(*SILK_REFS[ref]))
            fp.Reference().SetTextAngleDegrees(0)

    for net, width, pts, layer in ROUTES:
        add_track(board, netinfo[net], width, pts, pcbnew.F_Cu if layer == F else pcbnew.B_Cu)
    for net, x, y in VIAS:
        add_via(board, netinfo[net], x, y)

    add_outline(board)
    add_rule_area(board, "under-module", [pcbnew.F_Cu], UNDER_MODULE, tracks=True)
    for n, (cx, cy, r1, r2) in enumerate(KEEPOUT_RINGS):  # bottom side: no copper at all in the ring
        for i in range(24):  # ring as 24 sectors (plain polygons for the Specctra export)
            a = [math.radians(15 * (i + k)) for k in (0, 0.5, 1)]
            pts = [(cx + r * math.cos(t), cy + r * math.sin(t)) for r, ts in ((r1, a), (r2, a[::-1])) for t in ts]
            add_rule_area(board, f"cell-ring-{n}-{i}", [pcbnew.B_Cu], pts, tracks=True, vias=True, pour=True)
    for name, layers, pts, tracks, vias, pour in getattr(design, "RULE_AREAS", []):
        add_rule_area(board, name, [pcbnew.F_Cu if layer == F else pcbnew.B_Cu for layer in layers], pts,
                      tracks=tracks, vias=vias, pour=pour)

    # silkscreen
    for text, x, y, layer, size, thick, angle in TEXTS_PCB:
        add_text(board, text, x, y, pcbnew.F_SilkS if layer == F else pcbnew.B_SilkS, size, thick, angle)
    for ref, label in TP_LABEL.items():
        x, y, _, _ = PLACE[ref]
        add_text(board, label, x, y + 1.35, pcbnew.B_SilkS, 0.6, 0.1)

    save(board)
    print("placed:", PCB)
    return board


def sync():
    """Values and part numbers changed in design.py (same footprints and nets): update the placed and routed board
    in place, no new placement or routing."""
    comps, _ = read_netlist()
    board = pcbnew.LoadBoard(PCB)
    board.GetTitleBlock().SetDate(design.DATE)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    missing = set(comps) ^ set(fps)
    assert not missing, f"board and schematic differ: {missing}, run the place and route stages"
    for ref, c in sorted(comps.items()):
        fp = fps[ref]
        if fp.GetFPIDAsString() != c["footprint"]:
            raise SystemExit(f"{ref}: footprint changed to {c['footprint']}, run the place and route stages")
        fp.SetValue(c["value"])
        set_fields(fp, c, "B" if fp.IsFlipped() else "F")
    save(board)
    print("synced:", PCB)


# ------------------------------------------------------------------------------------------------- routing
def freeroute(board):
    os.makedirs(BUILD, exist_ok=True)
    dsn = os.path.join(BUILD, design.PROJECT + ".dsn")
    ses = os.path.join(BUILD, design.PROJECT + ".ses")
    if os.path.exists(ses):
        os.remove(ses)
    assert pcbnew.ExportSpecctraDSN(board, dsn), "DSN export failed"
    # FreeRouting 2.1 keeps passing while connections stay unrouted: the job timeout ends it and writes the SES
    cmd = ["java", "-jar", FREEROUTING, "-de", dsn, "-do", ses, "--gui.enabled=false", "-da", "-inc", "Ground",
           f"--router.job_timeout={JOB_TIMEOUT}"]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    log = os.path.join(BUILD, "freerouting.log")
    with open(log, "w") as f:
        f.write(r.stdout + r.stderr)
    if not os.path.exists(ses):
        raise SystemExit("FreeRouting produced no SES, see " + log)
    assert pcbnew.ImportSpecctraSES(board, ses), "SES import failed"


def cleanup_pass(board, keep_nets=(design.GND,)):
    """One pass: remove the dangling stubs and duplicate segments FreeRouting leaves behind and the vias connected
    on one layer only (GND vias stay: the pours connect them). An end is connected when a pad, a via or another
    track of the same net covers it on the same layer."""
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    items = list(board.GetTracks())
    tracks = [t for t in items if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in items if t.GetClass() == "PCB_VIA"]
    seen, dups = set(), []  # FreeRouting sometimes leaves the same segment twice
    for t in tracks:
        ends = tuple(sorted(((t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y))))
        key = (t.GetNetCode(), t.GetLayer(), ends)
        if key in seen and not t.IsLocked():
            dups.append(t)
        seen.add(key)
    for t in dups:
        board.Remove(t)
    tracks = [t for t in tracks if t not in dups]

    def covered(pos, layer, net, skip):
        return (any(p.GetNetCode() == net and p.IsOnLayer(layer) and p.HitTest(pos) for p in pads) or
                any(v.GetNetCode() == net and v.HitTest(pos) for v in vias) or
                any(t is not skip and t.GetNetCode() == net and t.GetLayer() == layer and t.HitTest(pos)
                    for t in tracks))

    bad = [t for t in tracks
           if not (covered(t.GetStart(), t.GetLayer(), t.GetNetCode(), t) and
                   covered(t.GetEnd(), t.GetLayer(), t.GetNetCode(), t))]
    for v in vias:
        if v.GetNetname() in keep_nets:
            continue
        on = [any(t.GetNetCode() == v.GetNetCode() and t.GetLayer() == layer and
                  (v.HitTest(t.GetStart()) or v.HitTest(t.GetEnd())) for t in tracks) or
              any(p.GetNetCode() == v.GetNetCode() and p.IsOnLayer(layer) and p.HitTest(v.GetPosition())
                  for p in pads)
              for layer in (pcbnew.F_Cu, pcbnew.B_Cu)]
        if not all(on):
            bad.append(v)
    for t in bad:
        if not t.IsLocked():
            board.Remove(t)
    return len(dups) + len([t for t in bad if not t.IsLocked()])


def add_pour(board, net, layer, priority=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName("GND " + board.GetLayerName(layer))
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(priority)
    e = 0.0
    polygon(z, [(X0 + e, Y0 + e), (X0 + W - e, Y0 + e), (X0 + W - e, Y0 + H - e), (X0 + e, Y0 + H - e)])
    board.Add(z)
    return z


def fill(board):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def stitch(board, gnd, pitch=2.0, keep=0.35):
    """GND vias wherever both pours have copper around the whole via (plus `keep` mm)."""
    pours = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gnd.GetNetCode()]
    r = 0.3 + keep
    ring = [(0, 0)] + [(r * math.cos(a), r * math.sin(a)) for a in [i * math.pi / 6 for i in range(12)]]
    holes = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
             for fp in board.GetFootprints() for p in fp.Pads() if p.HasHole()]
    holes += [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
              for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    # nor on silkscreen text (labels of the test pads, designators, board name)
    texts = [t for t in board.GetDrawings() if t.GetClass() == "PCB_TEXT"]
    texts += [fp.Reference() for fp in board.GetFootprints() if fp.Reference().IsVisible()]
    boxes = []
    for t in texts:
        bb = t.GetBoundingBox()
        boxes.append((pcbnew.ToMM(bb.GetLeft()) - 0.5, pcbnew.ToMM(bb.GetTop()) - 0.5,
                      pcbnew.ToMM(bb.GetRight()) + 0.5, pcbnew.ToMM(bb.GetBottom()) + 0.5))
    added = []
    y = Y0 + 1.2
    while y < Y0 + H - 1.0:
        x = X0 + 1.2
        while x < X0 + W - 1.0:
            ok = all(any(z.HitTestFilledArea(layer, pt(x + dx, y + dy), 0) for z in pours if z.GetLayer() == layer)
                     for layer in (pcbnew.F_Cu, pcbnew.B_Cu) for dx, dy in ring)
            ok = ok and all(math.hypot(x - hx, y - hy) > 1.2 for hx, hy in holes + added)
            ok = ok and all(math.hypot(x - cx, y - cy) > r for cx, cy, r in NO_STITCH)  # e.g. under the cell
            ok = ok and not any(x1 <= x <= x2 and y1 <= y <= y2 for x1, y1, x2, y2 in boxes)
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pt(x, y))
                v.SetWidth(mm(0.6))
                v.SetDrill(mm(0.3))
                v.SetNet(gnd)
                board.Add(v)
                added.append((x, y))
            x += pitch
        y += pitch
    return len(added)


def drc(path, *extra):
    rpt = os.path.join(BUILD, "drc.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", *extra, "-o", rpt, path], check=True,
                   capture_output=True)
    return open(rpt).read()


def drc_dangling():
    """(x, y, net) of what KiCad's DRC calls dangling, GND excepted (the pours connect it)."""
    spots = set()
    for x, y, net in re.findall(r"\[(?:track|via)_dangling\].*?\n.*?\n\s+@\(([-\d.]+) mm, ([-\d.]+) mm\): "
                                r"(?:Track|Via) \[([^\]]*)\]", drc(PCB)):
        if net != design.GND:
            spots.add((round(float(x), 3), round(float(y), 3), net))
    return spots


def step_freeroute():
    board = pcbnew.LoadBoard(PCB)
    freeroute(board)
    save(board)


def step_cleanup():
    """One pass: geometric dangling test, then KiCad's DRC dangling report. Prints the number removed."""
    board = pcbnew.LoadBoard(PCB)
    n = cleanup_pass(board)
    if n == 0:
        spots = drc_dangling()
        for t in list(board.GetTracks()):
            ends = [t.GetStart(), t.GetEnd()] if t.GetClass() == "PCB_TRACK" else [t.GetPosition()]
            keys = {(round(pcbnew.ToMM(p.x), 3), round(pcbnew.ToMM(p.y), 3), t.GetNetname()) for p in ends}
            if keys & spots and not t.IsLocked():
                board.Remove(t)
                n += 1
    save(board)
    print("removed", n)


def step_pour():
    """GND pours on both layers and stitching vias; replaces earlier ones, so it can run again on its own."""
    board = pcbnew.LoadBoard(PCB)
    gnd = board.FindNet(design.GND)
    old = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gnd.GetNetCode()]
    old += [v for v in board.GetTracks() if v.GetClass() == "PCB_VIA" and v.GetNetCode() == gnd.GetNetCode()
            and not v.IsLocked()]
    for item in old:
        board.Remove(item)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        add_pour(board, gnd, layer)
    fill(board)
    n = stitch(board, gnd)
    fill(board)
    save(board)
    print("stitching vias", n)


def run_step(name):
    """Each step in its own process (os._exit: no teardown of the SWIG objects)."""
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "_" + name], capture_output=True, text=True)
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines() if "memory leak" not in line)
    if r.returncode != 0:
        raise SystemExit(f"step {name} failed:\n{out}")
    return out


def drc_unrouted():
    """Nets other than GND with a missing connection, from KiCad's DRC."""
    nets = set()
    for blk in drc(PCB).split("\n[")[1:]:
        if blk.startswith("unconnected_items"):
            nets.update(re.findall(r"@\([^)]*\): [^\[\n]*\[([^\]]*)\]", blk))
    return nets - {design.GND}


def route():
    if drc_unrouted():
        print(run_step("freeroute"))
    else:
        print("FreeRouting skipped: every connection but GND (pours) is routed")
    for _ in range(8):
        out = run_step("cleanup")
        if out.strip().endswith("removed 0"):
            break
    print(run_step("pour"))
    print("routed:", PCB)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage.startswith("_"):  # internal step, see run_step()
        {"_freeroute": step_freeroute, "_cleanup": step_cleanup, "_pour": step_pour}[stage]()
        sys.stdout.flush()
        os._exit(0)
    if stage in ("place", "all"):
        place()
    if stage in ("route", "all"):
        route()
    if stage == "pour":
        print(run_step("pour"))
    if stage == "sync":
        sync()
    sys.stdout.flush()
    os._exit(0)
