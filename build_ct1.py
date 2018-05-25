#!/usr/bin/env python2
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


import os
from cqparts.display import display
from ct1 import CoffeTable

def work_dir():
    # This is needed for when the script is executed from within Freecad
    return os.path.dirname(os.path.realpath(__file__))


def export_drawings_models(table):
    dir2d = os.path.join(work_dir(), "build/2d")

    print("Exporting part SVG 2D-views")
    if not os.path.isdir(dir2d):
        os.makedirs(dir2d)
    table.find('leg_0').local_obj.exportSvg(os.path.join(dir2d, "ct1_leg.svg"), view_vector=(0, 1, 0))
    table.find('shelf_0').local_obj.exportSvg(os.path.join(dir2d, "ct1_shelf.svg"), view_vector=(0, 0, -1))
    table.find('glass_top').local_obj.exportSvg(os.path.join(dir2d, "ct1_glass_top.svg"), view_vector=(0, 0, 1))

    # Not possible with cqparts right now
    #print("Exporting assembly 2D-views")
    #table.exporter("svg")("2d_TOP_ct1.svg", view_vector=(0, 0, -1))
    #table.exporter("svg")("2d_FRONT_ct1.svg", view_vector=(0, 1, 0))
    #table.exporter("svg")("2d_LEFT_ct1.svg", view_vector=(1, 0, 0))


def export_step_models(table):
    dir3d = os.path.join(work_dir(), "build/3d")
    print("Exporting part STEP 3D-models")
    if not os.path.isdir(dir3d):
        os.makedirs(dir3d)
    table.find('leg_0').exporter("step")(os.path.join(dir3d, "ct1_leg.step"))
    table.find('shelf_0').exporter("step")(os.path.join(dir3d, "ct1_shelf.step"))
    table.find('glass_top').exporter("step")(os.path.join(dir3d, "ct1_glass_top.step"))

    # Not possible with cqparts right now
    #print("Exporting assembly 3D-model")
    #table.exporter("step")("3d_ct1.step")


def export_gltf_models(table):
    dirgltf = os.path.join(work_dir(), "build/gltf")
    print("Exporting assembly GLTF-model")
    if not os.path.isdir(dirgltf):
        os.makedirs(dirgltf)
    table.exporter('gltf')(os.path.join(dirgltf, "ct1.gltf"))


table = CoffeTable()
print(table.tree_str(name="ct1"))

export_drawings_models(table)
export_step_models(table)
export_gltf_models(table)

#display(table)
