#!.venv/bin/python3
# -*- coding: utf-8 -*-

"""
    Copyright 2018 Gustav Näslund

    This documentation describes Open Hardware and is licensed under the
    CERN OHL v.1.2.

    You may redistribute and modify this documentation under the terms of the
    CERN OHL v.1.2. (http://ohwr.org/cernohl). This documentation is distributed
    WITHOUT ANY EXPRESS OR IMPLIED WARRANTY, INCLUDING OF MERCHANTABILITY,
    SATISFACTORY QUALITY AND FITNESS FOR A PARTICULAR PURPOSE.
    Please see the CERN OHL v.1.2 for applicable conditions
"""

import math
import os
import cadquery as cq


def make_coffee_table():
    if not os.path.exists("build"):
        os.makedirs("build")

    # Basic dimensions
    length = 1000
    width = 700
    height = 500 
    height_1 = 340
    height_2 = 160

    # Material dimensions
    glass_t = 10
    shelf_t = 18
    leg_t = 36

    # Shared parameters
    ins_d = 3
    ins_l = 50
    cx = 200
    
    cl_side = 2
    cl_below = 3
    
    leg = make_leg(height, height_1, height_2, cx, leg_t, shelf_t, glass_t, cl_side, cl_below, ins_d, ins_l)
    glass = make_glass_top(length, width, glass_t)
    shelf = make_shelf(length, width, shelf_t, cx, ins_d, ins_l, leg_t)

    table = cq.Assembly() \
                .add(glass, loc=cq.Location((0, 0, height), (1, 0, 0), 0), name="glass top", color=cq.Color(0, 0, 1, 0.2)) \
                .add(leg, loc=cq.Location((length/2, width/2, height), (0, 0, 1), -135), name="leg 1", color=cq.Color("brown")) \
                .add(leg, loc=cq.Location((length/2, -width/2, height), (0, 0, 1), 135), name="leg 2", color=cq.Color("brown")) \
                .add(leg, loc=cq.Location((-length/2, -width/2, height), (0, 0, 1), 45), name="leg 3", color=cq.Color("brown")) \
                .add(leg, loc=cq.Location((-length/2, width/2, height), (0, 0, 1), -45), name="leg 4", color=cq.Color("brown")) \
                .add(shelf, loc=cq.Location((0, 0, height_1), (1, 0, 0), 0),name="upper shelf", color=cq.Color("brown")) \
                .add(shelf, loc=cq.Location((0, 0, height_2 - shelf_t), (1, 0, 0), 180),name="lower shelf", color=cq.Color("brown"))
    table.export("build/ct1.step")

    # Dont show_object
    try:
        show_object(table)
    except NameError:
        print("show_object only exists when running in CQ-editor")


def make_glass_top(length, width, t):
	return cq.Workplane('XY', origin=(0, 0, -t)) \
	    .box(length, width, t, centered=(True, True, False)) \
	    .faces("+Z").edges().chamfer(3)


def make_leg(height, height_1, height_2, cx, leg_t, shelf_t, glass_t, cl_side, cl_below, ins_d, ins_l):
    corner_protection = 16
    s1 = -20
    s2 = -8
    s3 = -10
    s4 = -35

    x0 = cx + ins_l / 2.0 + corner_protection
    x1 = cx - ins_l / 2.0 + corner_protection
    x2 = x1 - 25
    x3 = 100
    x4 = 80
    x5 = x3 - 55

    y0 = height
    y2 = height_1 - shelf_t + ins_d
    y1 = y2 - 12
    y3 = y2 - ins_d
    y5 = height_2 - ins_d
    y4 = y5 + ins_d
    y6 = y5 + 12
    y7 = y0 - 30

    m = cq.Workplane("XZ", origin = (-corner_protection, leg_t / 2, -height)).moveTo(0, y0).lineTo(x4, y0).sagittaArc((x2, y1), s1) \
        .lineTo(x1, y1).lineTo(x1, y2).lineTo(x0, y2).lineTo(x0, y3).sagittaArc((x0, y4), s2) \
        .lineTo(x0, y5).lineTo(x1, y5).lineTo(x1, y6).lineTo(x2, y6).sagittaArc((x3, 0), s3) \
        .lineTo(x5, 0).sagittaArc((0, y7), s4) \
        .close().extrude(leg_t)
    m = m.edges("|Y").edges(cq.NearestToPointSelector((0-corner_protection, 0, y7-height))).fillet(100)
    m = m.edges("|Y").edges(cq.NearestToPointSelector((x2-corner_protection, 0, y1-height))).fillet(20)
    m = m.edges("|Y").edges(cq.NearestToPointSelector((x1-corner_protection, 0, y1-height))).fillet(8)
    m = m.edges("|Y").edges(cq.NearestToPointSelector((x1-corner_protection, 0, y6-height))).fillet(8)
    m = m.edges("|Y").edges(cq.NearestToPointSelector((x2-corner_protection, 0, y6-height))).fillet(20)
    m = m.edges("%CIRCLE").fillet(7)

    # Create recess for glass    
    recess_length = math.sqrt(2 * (cx + cl_side)**2)
    recess_depth = glass_t + cl_below
    glass_recess = cq.Workplane('XY').box(recess_length, recess_length, recess_depth, centered=(True, True, False)) \
        .rotate((0,0,0), (0,0,1), 45).translate((cx, 0, -recess_depth))
    m = m.cut(glass_recess)

    # Export Section DXF before drilling the hole
    cq.exporters.export(m.section(leg_t / 2), "build/ct1_leg.dxf")
    
    # Create hole
    hole = cq.Workplane("XY", origin=(cx, 0, -height)).circle(4).extrude(height)
    m = m.cut(hole)

    return m


def make_shelf(length, width, shelf_t, cx, ins_d, ins_l, leg_t):
    r3 = 80
    s1 = -40
    s2 = -100
    s3 = 40

    x2 = (length - 0.85 * math.sqrt(cx**2 / 2)) / 2.0
    x1 = x2 - r3
    y1 = (width - 0.85 * math.sqrt(cx**2 / 2)) / 2.0
    y2 = y1 - r3

    p0 = (-x1,  y1, 0)
    p2 = (x1,  y1, 0)
    p4 = (x2,  y2, 0)
    p6 = (x2, -y2, 0)
    p8 = (x1, -y1, 0)
    p10 = (-x1, -y1, 0)
    p12 = (-x2, -y2, 0)
    p14 = (-x2,  y2, 0)

    m = cq.Workplane("XY", origin=(0, 0, -shelf_t)).moveTo(-x1, y1).sagittaArc(p2, s1) \
        .radiusArc(p4, s2).sagittaArc(p6, s3).radiusArc(p8, s2) \
        .sagittaArc(p10, s1).radiusArc(p12, s2) \
        .sagittaArc(p14, s3).radiusArc(p0, s2) \
        .close().extrude(shelf_t) \
        .edges("|Z").fillet(20)
    
    # Create a copy without fillets for creating the section view
    m_temp = m
    m = m.faces("|Z").edges().fillet(4)

    hole_x = length / 2.0 - math.sqrt(cx**2 / 2)
    hole_y = width / 2.0 - math.sqrt(cx**2 / 2)

    hole_pos = [(hole_x, hole_y, 45), (hole_x, -hole_y, -45), (-hole_x, -hole_y, 45), (-hole_x, hole_y, -45)]
    
    for x, y, angle in hole_pos:
        hole = cq.Workplane("XY", origin=(x, y, -shelf_t)).circle(9 / 2.0).extrude(shelf_t)
        m = m.cut(hole)
        m_temp = m_temp.cut(hole)
        leg_recess = cq.Workplane('XY').box(ins_l, leg_t, ins_d, centered=(True, True, False)) \
            .rotate((0,0,0), (0,0,1), angle).translate((x, y, -shelf_t)).edges("|Z").fillet(7.0)
        m = m.cut(leg_recess)
        m_temp = m_temp.cut(leg_recess)

    cq.exporters.export(m_temp.section(ins_d), "build/ct1_shelf.dxf")

    return m

make_coffee_table()
