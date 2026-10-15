#!/usr/bin/env python3
"""
    CT3 - a flat-pack coffee table for CNC routing, built in SolidCraft over MCP.

    Every part is a 2D profile cut from one sheet of plywood: a top, two legs,
    a shelf and four wedges. The legs go through the top with through-tenons,
    the shelf goes through the legs and is locked with knock-in wedges, so the
    table needs no hardware or glue. All inside corners get dogbones for the
    router bit, and each part's cutting profile is exported as a DXF.

    Start SolidCraft with a control port so you can watch it build:
        solidcraft --control 7878
    then:
        python ct3_solidcraft.py [new|top|legs|shelf|wedges|finish]

    Copyright 2026 Gustav Näslund, CERN OHL v.1.2 (see ct1.py)
"""

import math
import os
import sys

from sc import Session

BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")

# Material and machining. Measure the actual sheet: plywood is rarely exactly nominal.
PLY_T = 18.0        # sheet thickness
BIT_D = 6.35        # router bit diameter (1/4")
CLEAR = 0.2         # joint clearance per side
DOG_R = BIT_D / 2 + 0.1   # dogbone radius

# Table
LENGTH = 1100
WIDTH = 600
HEIGHT = 450
TOP_R = 80          # top corner radius

# Legs
LEG_X = 441         # leg centre plane, gives 100 mm top overhang at the ends
LEG_W_BOT = 520
LEG_W_TOP = 420
ARCH_W = 360        # arched opening between the feet
ARCH_H = 90
TENON_U = 110       # leg tenons and shelf tenons sit at +-TENON_U across the table
LEG_TENON_W = 80
HANDLE_W = 120
HANDLE_H = 36
HANDLE_Z = 348

# Shelf
SHELF_Z = 150       # underside of the shelf
SHELF_W = 440
SHELF_TENON_W = 100
SHELF_TENON_OUT = 55    # how far the tenons stick out past the legs
SLOT_W = 22         # wedge slot length along the tenon

# Wedges
WEDGE_H = 110
WEDGE_W_BOT = 14
WEDGE_W_TOP = 30

BIRCH = "#e2c79a"
WEDGE_COLOR = "#6b4429"


# ---------------------------------------------------------------------------
# 2D profile builder
# ---------------------------------------------------------------------------

def _unit(dx, dy):
    d = math.hypot(dx, dy)
    return dx / d, dy / d


def profile(items):
    """Turn a closed outline into line and arc segments.

    items: ("v", (x, y)) a sharp corner, ("v", (x, y), "round", R) a rounded convex
    corner, ("v", (x, y), "dog", r) a dogbone on a 90 degree inside corner, and
    ("a", (x, y)) between two plain corners to make that edge an arc through (x, y).
    Returns [("line", p, q) | ("arc", p, q, through)].
    """
    verts, arcs = [], {}
    for it in items:
        if it[0] == "v":
            verts.append(it[1:])
        else:
            arcs[len(verts) - 1] = it[1]
    n = len(verts)
    entry, exit_, corner_arcs = [None] * n, [None] * n, [None] * n
    for i, v in enumerate(verts):
        c = v[0]
        prev, nxt = verts[i - 1][0], verts[(i + 1) % n][0]
        if len(v) == 1:
            entry[i] = exit_[i] = c
            continue
        assert (i - 1) % n not in arcs and i not in arcs, "treated corners need straight edges"
        e1 = _unit(c[0] - prev[0], c[1] - prev[1])
        e2 = _unit(nxt[0] - c[0], nxt[1] - c[1])
        kind, r = v[1], v[2]
        if kind == "dog":
            assert abs(e1[0] * e2[0] + e1[1] * e2[1]) < 1e-9, "dogbones only on square corners"
            t = r * math.sqrt(2)
            through = c
        else:
            theta = math.acos(max(-1.0, min(1.0, e1[0] * e2[0] + e1[1] * e2[1])))
            t = r * math.tan(theta / 2)
            cross = e1[0] * e2[1] - e1[1] * e2[0]
            nrm = (-e1[1], e1[0]) if cross > 0 else (e1[1], -e1[0])
            start = (c[0] - t * e1[0], c[1] - t * e1[1])
            centre = (start[0] + r * nrm[0], start[1] + r * nrm[1])
            u = _unit(c[0] - centre[0], c[1] - centre[1])
            through = (centre[0] + r * u[0], centre[1] + r * u[1])
        entry[i] = (c[0] - t * e1[0], c[1] - t * e1[1])
        exit_[i] = (c[0] + t * e2[0], c[1] + t * e2[1])
        corner_arcs[i] = through

    segs = []
    for i in range(n):
        if corner_arcs[i] is not None:
            segs.append(("arc", entry[i], exit_[i], corner_arcs[i]))
        j = (i + 1) % n
        if i in arcs:
            segs.append(("arc", exit_[i], entry[j], arcs[i]))
        else:
            segs.append(("line", exit_[i], entry[j]))
    return segs


def rect_hole(cx, cy, w, h):
    """A rectangular hole with dogbones in all four corners."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    return profile([("v", (x0, y0), "dog", DOG_R), ("v", (x1, y0), "dog", DOG_R),
                    ("v", (x1, y1), "dog", DOG_R), ("v", (x0, y1), "dog", DOG_R)])


def draw(s, segs, to_sketch=lambda p: p):
    for seg in segs:
        pts = [list(to_sketch(p)) for p in seg[1:]]
        if seg[0] == "line":
            s.execute("sketch.line", points=pts)
        else:
            s.execute("sketch.arc.three_point", start=pts[0], end=pts[1], through=pts[2])


# The XZ sketch plane maps sketch (u, v) to world (X, -Z)
xz = lambda p: (p[0], -p[1])


def round_edges(s, body, keep, radius):
    """Round the edges a CNC roundover bit would do; skip quietly if SolidCraft can't."""
    topo = s.call("body_topology", body=body)
    edges = [e["mid"] for e in topo["edges"] if keep(e)]
    try:
        s.execute("solid.fillet", body=body, edges=edges, radius=radius)
        print(f"  rounded {len(edges)} edges r{radius}")
    except RuntimeError as e:
        print(f"  roundover skipped: {str(e)[:150]}")


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

def stage_new(s):
    s.call("new_design", name="CT3 coffee table")


def stage_top(s):
    s.execute("component.create", name="top")
    z0 = HEIGHT - PLY_T
    L, W = LENGTH / 2, WIDTH / 2
    s.execute("sketch.create", plane="XY", offset=z0, name="top profile")
    draw(s, profile([("v", (-L, -W), "round", TOP_R), ("v", (L, -W), "round", TOP_R),
                     ("v", (L, W), "round", TOP_R), ("v", (-L, W), "round", TOP_R)]))
    for x in (-LEG_X, LEG_X):
        for y in (-TENON_U, TENON_U):
            draw(s, rect_hole(x, y, PLY_T + 2 * CLEAR, LEG_TENON_W + 2 * CLEAR))
    s.execute("sketch.export_dxf", path=os.path.join(BUILD_DIR, "ct3_top.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=PLY_T, profiles=[{"point": [0, 0]}], name="top", body_name="top")
    round_edges(s, "top", lambda e: abs(e["mid"][2] - HEIGHT) < 1e-6
                and abs(abs(e["mid"][0]) - LEG_X) > 20, 3)
    s.execute("appearance.assign", bodies=["top"], color=BIRCH)
    s.execute("component.activate", component="root")


def stage_legs(s):
    """One leg drawn in XZ (across the table is X here), placed twice turned 90 degrees."""
    s.execute("component.create", name="leg")
    zt = HEIGHT - PLY_T
    b, t = LEG_W_BOT / 2, LEG_W_TOP / 2
    a = ARCH_W / 2
    u1, u0 = TENON_U + LEG_TENON_W / 2, TENON_U - LEG_TENON_W / 2
    outline = profile([
        ("v", (-b, 0), "round", 10), ("v", (-a, 0)), ("a", (0, ARCH_H)), ("v", (a, 0)),
        ("v", (b, 0), "round", 10), ("v", (t, zt)),
        ("v", (u1, zt), "dog", DOG_R), ("v", (u1, HEIGHT)), ("v", (u0, HEIGHT)), ("v", (u0, zt), "dog", DOG_R),
        ("v", (-u0, zt), "dog", DOG_R), ("v", (-u0, HEIGHT)), ("v", (-u1, HEIGHT)), ("v", (-u1, zt), "dog", DOG_R),
        ("v", (-t, zt)),
    ])
    hx, hr = HANDLE_W / 2 - HANDLE_H / 2, HANDLE_H / 2
    handle = profile([("v", (-hx, HANDLE_Z - hr)), ("v", (hx, HANDLE_Z - hr)), ("a", (hx + hr, HANDLE_Z)),
                      ("v", (hx, HANDLE_Z + hr)), ("v", (-hx, HANDLE_Z + hr)), ("a", (-hx - hr, HANDLE_Z))])

    s.execute("sketch.create", plane="XZ", name="leg profile")
    draw(s, outline, xz)
    draw(s, handle, xz)
    for u in (-TENON_U, TENON_U):
        draw(s, rect_hole(u, SHELF_Z + PLY_T / 2, SHELF_TENON_W + 2 * CLEAR, PLY_T + 2 * CLEAR), xz)
    s.execute("sketch.export_dxf", path=os.path.join(BUILD_DIR, "ct3_leg.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=PLY_T, direction="symmetric",
              profiles=[{"point": list(xz((-b + 40, 50)))}], name="leg", body_name="leg")
    s.execute("appearance.assign", bodies=["leg"], color=BIRCH)
    s.execute("component.activate", component="root")

    place(s, "leg", [dict(axis=[0, 0, 1], angle="90 deg", translate=[x, 0, 0]) for x in (-LEG_X, LEG_X)])


def stage_shelf(s):
    s.execute("component.create", name="shelf")
    xi = LEG_X - PLY_T / 2                       # leg inner face
    xo = LEG_X + PLY_T / 2 + SHELF_TENON_OUT     # tenon end
    w = SHELF_W / 2
    t0, t1 = TENON_U - SHELF_TENON_W / 2, TENON_U + SHELF_TENON_W / 2

    def side(sign):
        """Tenon corners on one end, walking up the +x end or down the -x end."""
        pts = []
        for y0, y1 in ((-t1, -t0), (t0, t1)):
            pts += [("v", (xi, y0), "dog", DOG_R), ("v", (xo, y0), "round", 6),
                    ("v", (xo, y1), "round", 6), ("v", (xi, y1), "dog", DOG_R)]
        return [(it[0], (sign * it[1][0], sign * it[1][1])) + it[2:] for it in pts]

    outline = profile([("v", (-xi, -w), "round", 20), ("v", (xi, -w), "round", 20)] + side(1)
                      + [("v", (xi, w), "round", 20), ("v", (-xi, w), "round", 20)] + side(-1))

    s.execute("sketch.create", plane="XY", offset=SHELF_Z, name="shelf profile")
    draw(s, outline)
    # Wedge slots: start 2 mm inside the leg's outer face so the wedge bears on the leg
    slot_x = LEG_X + PLY_T / 2 - 2 + SLOT_W / 2
    for x in (-slot_x, slot_x):
        for y in (-TENON_U, TENON_U):
            draw(s, rect_hole(x, y, SLOT_W, PLY_T + 2 * CLEAR))
    s.execute("sketch.export_dxf", path=os.path.join(BUILD_DIR, "ct3_shelf.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=PLY_T, profiles=[{"point": [0, 0]}], name="shelf", body_name="shelf")
    # No modelled roundover here: SolidCraft 0.12 can't blend this outline (the
    # chain ends on the tenons). Run the roundover bit on the top edge anyway.
    s.execute("appearance.assign", bodies=["shelf"], color=BIRCH)
    s.execute("component.activate", component="root")


def stage_wedges(s):
    """Tapered wedges, flat face against the leg, seated where they are 20 mm wide at the shelf top."""
    s.execute("component.create", name="wedge")
    s.execute("sketch.create", plane="XZ", name="wedge profile")
    draw(s, profile([("v", (0, 0), "round", 3), ("v", (WEDGE_W_BOT, 0), "round", 3),
                     ("v", (WEDGE_W_TOP, WEDGE_H), "round", 6), ("v", (0, WEDGE_H), "round", 6)]), xz)
    s.execute("sketch.export_dxf", path=os.path.join(BUILD_DIR, "ct3_wedge.dxf"))
    s.execute("sketch.finish")
    s.execute("solid.extrude", distance=PLY_T, direction="symmetric", name="wedge", body_name="wedge")
    s.execute("appearance.assign", bodies=["wedge"], color=WEDGE_COLOR)
    s.execute("component.activate", component="root")

    seated_w = SLOT_W - 2
    z0 = SHELF_Z + PLY_T - (seated_w - WEDGE_W_BOT) / (WEDGE_W_TOP - WEDGE_W_BOT) * WEDGE_H
    xf = LEG_X + PLY_T / 2
    moves = []
    for y in (-TENON_U, TENON_U):
        moves.append(dict(translate=[xf, y, z0]))
        moves.append(dict(axis=[0, 0, 1], angle="180 deg", translate=[-xf, y, z0]))
    place(s, "wedge", moves)


def place(s, component, moves):
    """Place a component once per move, copying it while it is still unmoved."""
    comps = s.execute("component.list")["components"]
    occs = [o["id"] for o in next(c for c in comps if c["name"] == component)["occurrences"]]
    while len(occs) < len(moves):
        occs.append(s.execute("occurrence.copy", component=component)["occurrence"])
    for occ, m in zip(occs, moves):
        s.execute("occurrence.move", occurrence=occ, space="world", origin=[0, 0, 0], **m)


def stage_finish(s):
    s.execute("browser.visibility", visible=False, folder="sketches")
    s.call("save", path=os.path.join(BUILD_DIR, "ct3.solidcraft"))
    s.call("export", path=os.path.join(BUILD_DIR, "ct3.step"), format="step")
    s.call("screenshot", path=os.path.join(BUILD_DIR, "ct3_render.png"), view="iso",
           width=1600, height=1000)
    r = s.execute("inspect.interference")
    print(f"  interference: {r.get('count')} clashes in {r.get('checked')} pairs")
    for i in r.get("interferences", []):
        print(f"    {i['a']} | {i['b']}: {i['volume_mm3']:.1f} mm3")
    for u in r.get("unchecked", []):
        print(f"    unchecked: {u['a']} | {u['b']}")


STAGES = {
    "new": stage_new,
    "top": stage_top,
    "legs": stage_legs,
    "shelf": stage_shelf,
    "wedges": stage_wedges,
    "finish": stage_finish,
}


if __name__ == "__main__":
    os.makedirs(BUILD_DIR, exist_ok=True)
    names = sys.argv[1:] or list(STAGES)
    with Session() as s:
        for name in names:
            print(f"[{name}]")
            STAGES[name](s)
