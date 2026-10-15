#!/usr/bin/env python3
"""
    CT1 coffee table rebuilt in SolidCraft, driven over MCP.

    Mirrors ct1.py: one leg component placed four times, one shelf component
    placed twice (the lower one flipped), and a glass top.

    Start SolidCraft with a control port so you can watch it build:
        solidcraft --control 7878
    then run all stages, or a single one:
        python ct1_solidcraft.py [--length MM] [--width MM] [new|leg|place_legs|shelf|glass|finish]

    Copyright 2018 Gustav Näslund, CERN OHL v.1.2 (see ct1.py)
"""

import json
import math
import os
import sys

from sc import Session

BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")

# Basic dimensions
LENGTH = 1000
WIDTH = 700
HEIGHT = 500
HEIGHT_1 = 340
HEIGHT_2 = 160

# Material dimensions
GLASS_T = 10
SHELF_T = 18
LEG_T = 36

# Shared parameters
INS_D = 3
INS_L = 50
CX = 200
CL_SIDE = 2
CL_BELOW = 3

WOOD = "Wood - Oak"
GLASS = "Glass - Clear"


def sagitta_mid(p0, p1, sag):
    """Point halfway along a CadQuery sagittaArc from p0 to p1."""
    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy)
    # Positive sagitta bulges to the left of the direction of travel
    return (mx - dy / d * sag, my + dx / d * sag)


def radius_mid(p0, p1, radius):
    """Point halfway along a CadQuery radiusArc, via its sagitta."""
    half = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 2.0
    sag = abs(radius) - math.sqrt(radius ** 2 - half ** 2)
    return sagitta_mid(p0, p1, sag if radius > 0 else -sag)


def fillet(s, body, edges, radius):
    """Fillet exactly as asked; fall back to fitting the radius if it is too big."""
    try:
        return s.execute("solid.fillet", body=body, edges=edges, radius=radius)
    except RuntimeError as e:
        print(f"  fillet r{radius} did not fit exactly, reducing: {str(e)[:200]}")
        return s.execute("solid.fillet", body=body, edges=edges, radius=radius, fit="reduce")


def draw_profile(s, start, segments):
    """Draw a closed profile in the active sketch.

    segments is a list of ("line", end) or ("arc", end, through) in sketch coordinates.
    """
    pos = start
    for seg in segments:
        if seg[0] == "line":
            s.execute("sketch.line", points=[list(pos), list(seg[1])])
        else:
            s.execute("sketch.arc.three_point", start=list(pos), end=list(seg[1]), through=list(seg[2]))
        pos = seg[1]


def out(suffix):
    """Output path; non-default sizes get their own files, e.g. build/ct1_1500x650.step."""
    name = "ct1" if (LENGTH, WIDTH) == (1000, 700) else f"ct1_{LENGTH}x{WIDTH}"
    return os.path.join(BUILD_DIR, name + suffix)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def stage_new(s):
    s.call("new_design", name=f"CT1 coffee table {LENGTH}x{WIDTH}")


def stage_leg(s):
    """The leg, in the same local frame as ct1.py but with z from 0 to HEIGHT.

    Local origin is the glass corner; +X points diagonally in towards the table centre.
    """
    s.execute("component.create", name="leg")

    corner_protection = 16
    s1, s2, s3, s4 = -20, -8, -10, -35

    x0 = CX + INS_L / 2.0 + corner_protection
    x1 = CX - INS_L / 2.0 + corner_protection
    x2 = x1 - 25
    x3 = 100
    x4 = 80
    x5 = x3 - 55

    y0 = HEIGHT
    y2 = HEIGHT_1 - SHELF_T + INS_D
    y1 = y2 - 12
    y3 = y2 - INS_D
    y5 = HEIGHT_2 - INS_D
    y4 = y5 + INS_D
    y6 = y5 + 12
    y7 = y0 - 30

    # Profile in (x, z) exactly as ct1.py draws it
    pts = {
        "p0": (0, y0), "p1": (x4, y0), "p2": (x2, y1), "p3": (x1, y1), "p4": (x1, y2),
        "p5": (x0, y2), "p6": (x0, y3), "p7": (x0, y4), "p8": (x0, y5), "p9": (x1, y5),
        "p10": (x1, y6), "p11": (x2, y6), "p12": (x3, 0), "p13": (x5, 0), "p14": (0, y7),
    }
    P = {k: (x - corner_protection, z) for k, (x, z) in pts.items()}
    arc = lambda a, b, sag: ("arc", P[b], sagitta_mid(P[a], P[b], sag))
    segments = [
        ("line", P["p1"]), arc("p1", "p2", s1),
        ("line", P["p3"]), ("line", P["p4"]), ("line", P["p5"]), ("line", P["p6"]),
        arc("p6", "p7", s2),
        ("line", P["p8"]), ("line", P["p9"]), ("line", P["p10"]), ("line", P["p11"]),
        arc("p11", "p12", s3),
        ("line", P["p13"]), arc("p13", "p14", s4),
        ("line", P["p0"]),
    ]

    # The XZ sketch plane maps sketch (u, v) to world (X, -Z)
    to_sketch = lambda p: (p[0], -p[1])
    s.execute("sketch.create", plane="XZ", name="leg profile")
    draw_profile(s, to_sketch(P["p0"]), [
        (seg[0],) + tuple(to_sketch(p) for p in seg[1:]) for seg in segments
    ])
    s.execute("sketch.export_dxf", path=out("_leg.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=LEG_T, direction="symmetric", name="leg", body_name="leg")

    # Fillets on the edges across the thickness, as in ct1.py
    for (x, z), r in [(P["p14"], 100), (P["p2"], 20), (P["p3"], 8), (P["p10"], 8), (P["p11"], 20)]:
        fillet(s, "leg", [[x, 0, z]], r)

    # ct1.py also rounds the curved outline edges with r7 (edges("%CIRCLE")), but
    # SolidCraft 0.12 can only blend straight edges, so that step is left out.

    # Recess for the glass: a square turned 45 degrees around the hole axis
    recess_half_diag = CX + CL_SIDE
    recess_depth = GLASS_T + CL_BELOW
    s.execute("sketch.create", plane="XY", offset=HEIGHT - recess_depth, name="glass recess")
    s.execute("sketch.line", closed=True, points=[
        [CX - recess_half_diag, 0], [CX, -recess_half_diag],
        [CX + recess_half_diag, 0], [CX, recess_half_diag],
    ])
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=recess_depth + 5, operation="cut", targets=["leg"],
              name="glass recess")

    # Hole for the threaded rod
    s.execute("solid.cylinder", radius=4, height=HEIGHT, base=[CX, 0, 0],
              operation="cut", targets=["leg"], name="rod hole")

    s.execute("appearance.assign", bodies=["leg"], appearance=WOOD)
    s.execute("component.activate", component="root")


def stage_place_legs(s):
    """Four placements of the leg component, same Locations as ct1.py."""
    comps = s.execute("component.list")["components"]
    leg = next(c for c in comps if c["name"] == "leg")
    occs = [o["id"] for o in leg["occurrences"]]
    while len(occs) < 4:
        occs.append(s.execute("occurrence.copy", component="leg")["occurrence"])
    placements = [
        (LENGTH / 2, WIDTH / 2, -135),
        (LENGTH / 2, -WIDTH / 2, 135),
        (-LENGTH / 2, -WIDTH / 2, 45),
        (-LENGTH / 2, WIDTH / 2, -45),
    ]
    for occ, (x, y, angle) in zip(occs, placements):
        s.execute("occurrence.move", occurrence=occ, space="world", origin=[0, 0, 0],
                  axis=[0, 0, 1], angle=f"{angle} deg", translate=[x, y, 0])


def stage_shelf(s):
    """Upper shelf built in place; the lower one is the same component flipped about X."""
    s.execute("component.create", name="shelf")
    z_bottom = HEIGHT_1 - SHELF_T

    r3 = 80
    s1, s2, s3 = -40, -100, 40
    x2 = (LENGTH - 0.85 * math.sqrt(CX ** 2 / 2)) / 2.0
    x1 = x2 - r3
    y1 = (WIDTH - 0.85 * math.sqrt(CX ** 2 / 2)) / 2.0
    y2 = y1 - r3

    p = [(-x1, y1), (x1, y1), (x2, y2), (x2, -y2), (x1, -y1), (-x1, -y1), (-x2, -y2), (-x2, y2)]
    kinds = [("s", s1), ("r", s2), ("s", s3), ("r", s2)] * 2
    segments = []
    for i, (kind, v) in enumerate(kinds):
        a, b = p[i], p[(i + 1) % len(p)]
        mid = sagitta_mid(a, b, v) if kind == "s" else radius_mid(a, b, v)
        segments.append(("arc", b, mid))

    s.execute("sketch.create", plane="XY", offset=z_bottom, name="shelf outline")
    draw_profile(s, p[0], segments)
    s.execute("sketch.export_dxf", path=out("_shelf.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=SHELF_T, name="shelf", body_name="shelf")

    # Round the corners where the arcs meet, then the top and bottom outline
    z_mid = z_bottom + SHELF_T / 2
    fillet(s, "shelf", [[x, y, z_mid] for x, y in p], 20)
    topo = s.call("body_topology", body="shelf")
    outline = [e["mid"] for e in topo["edges"]
               if abs(e["start"][2] - e["end"][2]) < 1e-6
               and min(abs(e["mid"][2] - z_bottom), abs(e["mid"][2] - z_bottom - SHELF_T)) < 1e-6]
    print(f"  rounding {len(outline)} top/bottom outline edges")
    fillet(s, "shelf", outline, 4)

    # Rod holes and the shallow recesses where the legs sit
    hole_x = LENGTH / 2.0 - math.sqrt(CX ** 2 / 2)
    hole_y = WIDTH / 2.0 - math.sqrt(CX ** 2 / 2)
    hole_pos = [(hole_x, hole_y, 45), (hole_x, -hole_y, -45), (-hole_x, -hole_y, 45), (-hole_x, hole_y, -45)]

    s.execute("sketch.create", plane="XY", offset=z_bottom, name="leg recesses")
    for x, y, angle in hole_pos:
        c, si = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        corners = [(x + u * c - v * si, y + u * si + v * c)
                   for u, v in [(-INS_L / 2, -LEG_T / 2), (INS_L / 2, -LEG_T / 2),
                                (INS_L / 2, LEG_T / 2), (-INS_L / 2, LEG_T / 2)]]
        res = s.execute("sketch.line", points=[list(q) for q in corners], closed=True)
        for pid in res["created"]["points"]:
            s.execute("sketch.fillet", point=pid, radius=7)
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=INS_D, operation="cut", targets=["shelf"], name="leg recesses")

    for i, (x, y, _) in enumerate(hole_pos):
        s.execute("solid.cylinder", diameter=9, height=SHELF_T, base=[x, y, z_bottom],
                  operation="cut", targets=["shelf"], name=f"rod hole {i + 1}")

    s.execute("appearance.assign", bodies=["shelf"], appearance=WOOD)
    s.execute("component.activate", component="root")

    # Lower shelf: ct1.py rotates it 180 degrees about X; pivot so it lands at HEIGHT_2
    lower = s.execute("occurrence.copy", component="shelf")["occurrence"]
    pivot_z = (HEIGHT_1 + HEIGHT_2 - SHELF_T) / 2.0
    s.execute("occurrence.move", occurrence=lower, space="world", origin=[0, 0, pivot_z],
              axis=[1, 0, 0], angle="180 deg")


def stage_glass(s):
    s.execute("component.create", name="glass top")
    s.execute("solid.box", length=LENGTH, width=WIDTH, height=GLASS_T,
              corner=[-LENGTH / 2, -WIDTH / 2, HEIGHT - GLASS_T], name="glass", body_name="glass")
    s.execute("solid.chamfer", body="glass", distance=3, edges=[
        [0, WIDTH / 2, HEIGHT], [0, -WIDTH / 2, HEIGHT],
        [LENGTH / 2, 0, HEIGHT], [-LENGTH / 2, 0, HEIGHT],
    ])
    s.execute("appearance.assign", bodies=["glass"], appearance=GLASS)
    s.execute("component.activate", component="root")


def stage_finish(s):
    s.execute("browser.visibility", visible=False, folder="sketches")
    s.call("save", path=out(".solidcraft"))
    s.call("export", path=out(".step"), format="step")
    s.call("screenshot", path=out("_render.png"), view="iso",
           width=1600, height=1000)
    print(json.dumps(s.execute("inspect.interference"), indent=1)[:2000])


STAGES = {
    "new": stage_new,
    "leg": stage_leg,
    "place_legs": stage_place_legs,
    "shelf": stage_shelf,
    "glass": stage_glass,
    "finish": stage_finish,
}


if __name__ == "__main__":
    os.makedirs(BUILD_DIR, exist_ok=True)
    args = sys.argv[1:]
    for opt in ("--length", "--width"):
        if opt in args:
            i = args.index(opt)
            globals()[opt[2:].upper()] = int(args[i + 1])
            del args[i:i + 2]
    names = args or list(STAGES)
    with Session() as s:
        for name in names:
            print(f"[{name}]")
            STAGES[name](s)
