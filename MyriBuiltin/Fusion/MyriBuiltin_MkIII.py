"""Myri Built-in MkIII — standalone Fusion 360 script.

In Fusion's Scripts and Add-Ins dialog, create a Python script named
MyriBuiltin_MkIII, replace its .py contents with this file, then run it.
Creates a NEW unsaved direct-modeling design on every run (no timeline).
Snapshot of MyriBuiltin_MkIII.rb; no Ruby is required. Keep textures/ beside this file.
Walnut and purpleheart use the original project images. Other materials use
the source palette colors, matching the earlier successful render.
Coordinates/dimensions are inches; Fusion API geometry uses centimeters.
X is right, negative Y projects into the room, Z is up.
Material colors, wood textures, and metadata are included. Physical material
properties, the photo figure, and simulated light washes are omitted.
Birch plywood uses the source color; veneer layers are not modeled.
Each run appends progress and errors to MyriBuiltin_MkIII.log beside this script.

API references:
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/TemporaryBRepManager_Sample.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/LoftFeatureSample_Sample.htm
"""
import json
import math
import logging
from pathlib import Path
import platform
import sys
import time
import traceback

import adsk.core
import adsk.fusion

INCH = 2.54
SHOW_MATTRESS = True
SHOW_LIGHTING = True
DATA = json.loads(r'''{
  "assemblies": [
    {
      "name": "D1 Desk lower surround",
      "shop_built": true,
      "parts": [
        {
          "name": "D1 Desk lower surround left side",
          "origin": [
            0,
            -13.0,
            0
          ],
          "size": [
            0.75,
            13.0,
            48.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D1 Desk lower surround right side",
          "origin": [
            44.875,
            -13.0,
            0
          ],
          "size": [
            0.75,
            13.0,
            48.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D1 Desk lower surround top",
          "origin": [
            0.75,
            -13.0,
            48.0
          ],
          "size": [
            44.125,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D1 Desk lower surround back",
          "origin": [
            0.5,
            -1.0,
            0
          ],
          "size": [
            44.625,
            0.25,
            48.25
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "D1 Desk lower surround top mounting brace",
          "origin": [
            0.75,
            -0.75,
            45.0
          ],
          "size": [
            44.125,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        }
      ]
    },
    {
      "name": "D2 Desk drawer pedestal",
      "shop_built": true,
      "parts": [
        {
          "name": "D2 Desk drawer pedestal left side",
          "origin": [
            1,
            -23.0,
            0
          ],
          "size": [
            0.75,
            22,
            29.25
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 21.0,
            "height": 0.25
          }
        },
        {
          "name": "D2 Desk drawer pedestal right side",
          "origin": [
            15.25,
            -23.0,
            0
          ],
          "size": [
            0.75,
            22,
            29.25
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 21.0,
            "height": 0.25
          }
        },
        {
          "name": "D2 Desk drawer pedestal top",
          "origin": [
            1.75,
            -23.0,
            28.5
          ],
          "size": [
            13.5,
            22,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "y",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 21.0,
            "height": 0.25
          }
        },
        {
          "name": "D2 Desk drawer pedestal bottom",
          "origin": [
            1.75,
            -23.0,
            0
          ],
          "size": [
            13.5,
            22,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "y",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 21.0,
            "height": 0.25
          }
        },
        {
          "name": "D2 Desk drawer pedestal back",
          "origin": [
            1.5,
            -2.0,
            0.5
          ],
          "size": [
            14.0,
            0.25,
            28.25
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "D2 Desk drawer pedestal top mounting brace",
          "origin": [
            1.75,
            -1.75,
            25.5
          ],
          "size": [
            13.5,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "Desk file drawer front",
          "origin": [
            1.875,
            -23.75,
            0.875
          ],
          "size": [
            13.25,
            0.75,
            13.6875
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Desk file drawer bottom",
          "origin": [
            2.5,
            -22.75,
            1.875
          ],
          "size": [
            12.0,
            20.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 1"
        },
        {
          "name": "Desk file drawer side 1",
          "origin": [
            2.25,
            -23.0,
            1.375
          ],
          "size": [
            0.5,
            21.0,
            12.6875
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 1"
        },
        {
          "name": "Desk file drawer side 2",
          "origin": [
            14.25,
            -23.0,
            1.375
          ],
          "size": [
            0.5,
            21.0,
            12.6875
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 2"
        },
        {
          "name": "Desk file drawer end 1",
          "origin": [
            2.75,
            -23.0,
            1.375
          ],
          "size": [
            11.5,
            0.5,
            12.6875
          ],
          "material": "baltic_birch_plywood",
          "grain": "z",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 1"
        },
        {
          "name": "Desk file drawer end 2",
          "origin": [
            2.75,
            -2.5,
            1.375
          ],
          "size": [
            11.5,
            0.5,
            12.6875
          ],
          "material": "baltic_birch_plywood",
          "grain": "z",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 2"
        },
        {
          "name": "Desk drawer 2 front",
          "origin": [
            1.875,
            -23.75,
            14.6875
          ],
          "size": [
            13.25,
            0.75,
            6.78125
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Desk drawer 2 bottom",
          "origin": [
            2.5,
            -22.75,
            15.6875
          ],
          "size": [
            12.0,
            20.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 1"
        },
        {
          "name": "Desk drawer 2 side 1",
          "origin": [
            2.25,
            -23.0,
            15.1875
          ],
          "size": [
            0.5,
            21.0,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 3"
        },
        {
          "name": "Desk drawer 2 side 2",
          "origin": [
            14.25,
            -23.0,
            15.1875
          ],
          "size": [
            0.5,
            21.0,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 4"
        },
        {
          "name": "Desk drawer 2 end 1",
          "origin": [
            2.75,
            -23.0,
            15.1875
          ],
          "size": [
            11.5,
            0.5,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 3"
        },
        {
          "name": "Desk drawer 2 end 2",
          "origin": [
            2.75,
            -2.5,
            15.1875
          ],
          "size": [
            11.5,
            0.5,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 4"
        },
        {
          "name": "Desk drawer 3 front",
          "origin": [
            1.875,
            -23.75,
            21.59375
          ],
          "size": [
            13.25,
            0.75,
            6.78125
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Desk drawer 3 bottom",
          "origin": [
            2.5,
            -22.75,
            22.59375
          ],
          "size": [
            12.0,
            20.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 1"
        },
        {
          "name": "Desk drawer 3 side 1",
          "origin": [
            2.25,
            -23.0,
            22.09375
          ],
          "size": [
            0.5,
            21.0,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 3"
        },
        {
          "name": "Desk drawer 3 side 2",
          "origin": [
            14.25,
            -23.0,
            22.09375
          ],
          "size": [
            0.5,
            21.0,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 4"
        },
        {
          "name": "Desk drawer 3 end 1",
          "origin": [
            2.75,
            -23.0,
            22.09375
          ],
          "size": [
            11.5,
            0.5,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 3"
        },
        {
          "name": "Desk drawer 3 end 2",
          "origin": [
            2.75,
            -2.5,
            22.09375
          ],
          "size": [
            11.5,
            0.5,
            5.78125
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 4"
        },
        {
          "name": "D2 Desk drawer pedestal left side purpleheart frame",
          "origin": [
            1,
            -23.75,
            0.0
          ],
          "size": [
            0.75,
            0.75,
            29.25
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "D2 Desk drawer pedestal right side purpleheart frame",
          "origin": [
            15.25,
            -23.75,
            0.0
          ],
          "size": [
            0.75,
            0.75,
            29.25
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "D2 Desk drawer pedestal bottom purpleheart frame",
          "origin": [
            1.75,
            -23.75,
            0
          ],
          "size": [
            13.5,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "D2 Desk drawer pedestal top purpleheart frame",
          "origin": [
            1.75,
            -23.75,
            28.5
          ],
          "size": [
            13.5,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    },
    {
      "name": "D3 Desk full-width upper",
      "shop_built": true,
      "parts": [
        {
          "name": "D3 Desk full-width upper left side",
          "origin": [
            0,
            -13.0,
            48.75
          ],
          "size": [
            0.75,
            13.0,
            46.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D3 Desk full-width upper right side",
          "origin": [
            44.875,
            -13.0,
            48.75
          ],
          "size": [
            0.75,
            13.0,
            46.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D3 Desk full-width upper top",
          "origin": [
            0.75,
            -13.0,
            94.75
          ],
          "size": [
            44.125,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "D3 Desk full-width upper shelf 1",
          "origin": [
            0.75,
            -13.0,
            72
          ],
          "size": [
            44.125,
            12.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "D3 Desk full-width upper back",
          "origin": [
            0.5,
            -1.0,
            48.75
          ],
          "size": [
            44.625,
            0.25,
            46.25
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "D3 Desk full-width upper top mounting brace",
          "origin": [
            0.75,
            -0.75,
            91.75
          ],
          "size": [
            44.125,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "D3 Desk full-width upper shelf 1 purpleheart frame",
          "origin": [
            0.75,
            -13.75,
            72
          ],
          "size": [
            44.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    },
    {
      "name": "N1 Nightstand drawers",
      "shop_built": true,
      "parts": [
        {
          "name": "N1 Nightstand drawers left side",
          "origin": [
            104.375,
            -13.0,
            0
          ],
          "size": [
            0.75,
            13.0,
            28.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N1 Nightstand drawers right side",
          "origin": [
            127.25,
            -13.0,
            0
          ],
          "size": [
            0.75,
            13.0,
            28.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N1 Nightstand drawers top",
          "origin": [
            105.125,
            -13.0,
            28.0
          ],
          "size": [
            22.125,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N1 Nightstand drawers bottom",
          "origin": [
            105.125,
            -13.0,
            0
          ],
          "size": [
            22.125,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N1 Nightstand drawers back",
          "origin": [
            104.875,
            -1.0,
            0.5
          ],
          "size": [
            22.625,
            0.25,
            27.75
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "N1 Nightstand drawers top mounting brace",
          "origin": [
            105.125,
            -0.75,
            25.0
          ],
          "size": [
            22.125,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "Nightstand drawer front 1",
          "origin": [
            105.25,
            -13.75,
            0.875
          ],
          "size": [
            21.875,
            0.75,
            8.916666666666666
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Nightstand drawer 1 bottom",
          "origin": [
            105.875,
            -12.75,
            1.875
          ],
          "size": [
            20.625,
            11.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 2"
        },
        {
          "name": "Nightstand drawer 1 side 1",
          "origin": [
            105.625,
            -13.0,
            1.375
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 5"
        },
        {
          "name": "Nightstand drawer 1 side 2",
          "origin": [
            126.25,
            -13.0,
            1.375
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 6"
        },
        {
          "name": "Nightstand drawer 1 end 1",
          "origin": [
            106.125,
            -13.0,
            1.375
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 5"
        },
        {
          "name": "Nightstand drawer 1 end 2",
          "origin": [
            106.125,
            -1.5,
            1.375
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 6"
        },
        {
          "name": "Nightstand drawer front 2",
          "origin": [
            105.25,
            -13.75,
            9.916666666666666
          ],
          "size": [
            21.875,
            0.75,
            8.916666666666666
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Nightstand drawer 2 bottom",
          "origin": [
            105.875,
            -12.75,
            10.916666666666666
          ],
          "size": [
            20.625,
            11.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 2"
        },
        {
          "name": "Nightstand drawer 2 side 1",
          "origin": [
            105.625,
            -13.0,
            10.416666666666666
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 5"
        },
        {
          "name": "Nightstand drawer 2 side 2",
          "origin": [
            126.25,
            -13.0,
            10.416666666666666
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 6"
        },
        {
          "name": "Nightstand drawer 2 end 1",
          "origin": [
            106.125,
            -13.0,
            10.416666666666666
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 5"
        },
        {
          "name": "Nightstand drawer 2 end 2",
          "origin": [
            106.125,
            -1.5,
            10.416666666666666
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 6"
        },
        {
          "name": "Nightstand drawer front 3",
          "origin": [
            105.25,
            -13.75,
            18.958333333333332
          ],
          "size": [
            21.875,
            0.75,
            8.916666666666666
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Nightstand drawer 3 bottom",
          "origin": [
            105.875,
            -12.75,
            19.958333333333332
          ],
          "size": [
            20.625,
            11.5,
            0.5
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "bottom",
          "definition_name": "Drawer box bottom 2"
        },
        {
          "name": "Nightstand drawer 3 side 1",
          "origin": [
            105.625,
            -13.0,
            19.458333333333332
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "high"
          },
          "definition_name": "Drawer box side 5"
        },
        {
          "name": "Nightstand drawer 3 side 2",
          "origin": [
            126.25,
            -13.0,
            19.458333333333332
          ],
          "size": [
            0.5,
            12.0,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "y",
          "drawer_box_role": "side",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "x",
            "edge": "low"
          },
          "definition_name": "Drawer box side 6"
        },
        {
          "name": "Nightstand drawer 3 end 1",
          "origin": [
            106.125,
            -13.0,
            19.458333333333332
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "high"
          },
          "definition_name": "Drawer box end 5"
        },
        {
          "name": "Nightstand drawer 3 end 2",
          "origin": [
            106.125,
            -1.5,
            19.458333333333332
          ],
          "size": [
            20.125,
            0.5,
            7.916666666666666
          ],
          "material": "baltic_birch_plywood",
          "grain": "x",
          "drawer_box_role": "end",
          "dado": {
            "depth": 0.25,
            "bottom": 0.5,
            "height": 0.5,
            "axis": "y",
            "edge": "low"
          },
          "definition_name": "Drawer box end 6"
        },
        {
          "name": "N1 Nightstand drawers bottom purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            0
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "N1 Nightstand drawers top purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            28.0
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    },
    {
      "name": "N2 Nightstand open shelves",
      "shop_built": true,
      "parts": [
        {
          "name": "N2 Nightstand open shelves left side",
          "origin": [
            104.375,
            -13.0,
            28.75
          ],
          "size": [
            0.75,
            13.0,
            66.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N2 Nightstand open shelves right side",
          "origin": [
            127.25,
            -13.0,
            28.75
          ],
          "size": [
            0.75,
            13.0,
            66.75
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N2 Nightstand open shelves top",
          "origin": [
            105.125,
            -13.0,
            94.75
          ],
          "size": [
            22.125,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "N2 Nightstand open shelves shelf 1",
          "origin": [
            105.125,
            -13.0,
            45
          ],
          "size": [
            22.125,
            12.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves shelf 2",
          "origin": [
            105.125,
            -13.0,
            61.5
          ],
          "size": [
            22.125,
            12.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves shelf 3",
          "origin": [
            105.125,
            -13.0,
            78
          ],
          "size": [
            22.125,
            12.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves back",
          "origin": [
            104.875,
            -1.0,
            28.75
          ],
          "size": [
            22.625,
            0.25,
            66.25
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "N2 Nightstand open shelves top mounting brace",
          "origin": [
            105.125,
            -0.75,
            91.75
          ],
          "size": [
            22.125,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves shelf 1 purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            45
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves shelf 2 purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            61.5
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves shelf 3 purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            78
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "N2 Nightstand open shelves top purpleheart frame",
          "origin": [
            105.125,
            -13.75,
            94.75
          ],
          "size": [
            22.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    },
    {
      "name": "B1 Bridge cabinet",
      "shop_built": true,
      "parts": [
        {
          "name": "B1 Bridge cabinet left side",
          "origin": [
            45.625,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B1 Bridge cabinet right side",
          "origin": [
            64.45833333333333,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B1 Bridge cabinet top",
          "origin": [
            46.375,
            -13.0,
            94.75
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B1 Bridge cabinet bottom",
          "origin": [
            46.375,
            -13.0,
            72
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B1 Bridge cabinet back",
          "origin": [
            46.125,
            -1.0,
            72.5
          ],
          "size": [
            18.583333333333332,
            0.25,
            22.5
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "B1 Bridge cabinet top mounting brace",
          "origin": [
            46.375,
            -0.75,
            91.75
          ],
          "size": [
            18.083333333333332,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "Bridge door 1",
          "origin": [
            46.5,
            -13.75,
            72.875
          ],
          "size": [
            17.833333333333332,
            0.75,
            21.75
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        }
      ]
    },
    {
      "name": "B2 Bridge cabinet",
      "shop_built": true,
      "parts": [
        {
          "name": "B2 Bridge cabinet left side",
          "origin": [
            65.20833333333333,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B2 Bridge cabinet right side",
          "origin": [
            84.04166666666666,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B2 Bridge cabinet top",
          "origin": [
            65.95833333333333,
            -13.0,
            94.75
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B2 Bridge cabinet bottom",
          "origin": [
            65.95833333333333,
            -13.0,
            72
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B2 Bridge cabinet back",
          "origin": [
            65.70833333333333,
            -1.0,
            72.5
          ],
          "size": [
            18.583333333333332,
            0.25,
            22.5
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "B2 Bridge cabinet top mounting brace",
          "origin": [
            65.95833333333333,
            -0.75,
            91.75
          ],
          "size": [
            18.083333333333332,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "Bridge door 2",
          "origin": [
            66.08333333333333,
            -13.75,
            72.875
          ],
          "size": [
            17.833333333333332,
            0.75,
            21.75
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        }
      ]
    },
    {
      "name": "B3 Bridge cabinet",
      "shop_built": true,
      "parts": [
        {
          "name": "B3 Bridge cabinet left side",
          "origin": [
            84.79166666666666,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B3 Bridge cabinet right side",
          "origin": [
            103.62499999999999,
            -13.0,
            72
          ],
          "size": [
            0.75,
            13.0,
            23.5
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B3 Bridge cabinet top",
          "origin": [
            85.54166666666666,
            -13.0,
            94.75
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B3 Bridge cabinet bottom",
          "origin": [
            85.54166666666666,
            -13.0,
            72
          ],
          "size": [
            18.083333333333332,
            13.0,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "B3 Bridge cabinet back",
          "origin": [
            85.29166666666666,
            -1.0,
            72.5
          ],
          "size": [
            18.583333333333332,
            0.25,
            22.5
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "B3 Bridge cabinet top mounting brace",
          "origin": [
            85.54166666666666,
            -0.75,
            91.75
          ],
          "size": [
            18.083333333333332,
            0.75,
            3.0
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "Bridge door 3",
          "origin": [
            85.66666666666666,
            -13.75,
            72.875
          ],
          "size": [
            17.833333333333332,
            0.75,
            21.75
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        }
      ]
    },
    {
      "name": "H1 Open headboard carcass",
      "shop_built": true,
      "parts": [
        {
          "name": "H1 Open headboard carcass back",
          "origin": [
            46.125,
            -1.0,
            0.5
          ],
          "size": [
            57.75,
            0.25,
            71.0
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "H1 Open headboard carcass top mounting brace",
          "origin": [
            46.375,
            -0.75,
            68.25
          ],
          "size": [
            57.25,
            0.75,
            3
          ],
          "material": "walnut_plywood",
          "grain": "x"
        },
        {
          "name": "H1 Open headboard carcass top cap",
          "origin": [
            45.625,
            -13,
            71.25
          ],
          "size": [
            58.75,
            13,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "H1 Open headboard carcass bottom",
          "origin": [
            46.375,
            -13,
            0
          ],
          "size": [
            57.25,
            13,
            0.75
          ],
          "material": "walnut_plywood",
          "grain": "x",
          "dado": {
            "axis": "z",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "Headboard purpleheart bed attachment cross brace",
          "origin": [
            46.375,
            -2.5,
            8
          ],
          "size": [
            57.25,
            0.75,
            8
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "H1 Open headboard carcass side 1",
          "origin": [
            45.625,
            -13,
            0
          ],
          "size": [
            0.75,
            13,
            71.25
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "high",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "H1 Open headboard carcass side 2",
          "origin": [
            103.625,
            -13,
            0
          ],
          "size": [
            0.75,
            13,
            71.25
          ],
          "material": "walnut_plywood",
          "grain": "z",
          "dado": {
            "axis": "x",
            "slot_axis": "y",
            "edge": "low",
            "depth": 0.25,
            "bottom": 12.0,
            "height": 0.25
          }
        },
        {
          "name": "H1 Open headboard carcass purpleheart bottom frame",
          "origin": [
            46.375,
            -13.75,
            0
          ],
          "size": [
            57.25,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    },
    {
      "name": "I1 Site-installed top, trim and lighting",
      "shop_built": false,
      "parts": [
        {
          "name": "Desk top",
          "origin": [
            0.75,
            -24,
            29.25
          ],
          "size": [
            44.125,
            23.0,
            1.5
          ],
          "material": "walnut_solid",
          "grain": "x"
        },
        {
          "name": "Desk LED",
          "origin": [
            2.5,
            -2.15,
            47.75
          ],
          "size": [
            42,
            0.4,
            0.25
          ],
          "material": "led",
          "grain": "x"
        },
        {
          "name": "Nightstand LED",
          "origin": [
            105.875,
            -2.15,
            44.75
          ],
          "size": [
            20.625,
            0.4,
            0.25
          ],
          "material": "led",
          "grain": "x"
        }
      ]
    },
    {
      "name": "D5 Desk right support panel",
      "shop_built": true,
      "parts": [
        {
          "name": "Desk right walnut plywood support",
          "origin": [
            44.125,
            -23.25,
            0
          ],
          "size": [
            0.75,
            22.25,
            29.25
          ],
          "material": "walnut_plywood",
          "grain": "z"
        },
        {
          "name": "Desk right support purpleheart face frame",
          "origin": [
            44.125,
            -24.0,
            0.0
          ],
          "size": [
            0.75,
            0.75,
            29.25
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        }
      ]
    },
    {
      "name": "F1 Bed left rail and ledge",
      "shop_built": true,
      "parts": [
        {
          "name": "Bed left rail",
          "origin": [
            46.5,
            -78.5,
            8
          ],
          "size": [
            1.5,
            76,
            8
          ],
          "material": "walnut_solid",
          "grain": "y"
        },
        {
          "name": "Bed left slat ledge",
          "origin": [
            48,
            -78.5,
            14.25
          ],
          "size": [
            1,
            74.5,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "y"
        }
      ]
    },
    {
      "name": "F2 Bed right rail and ledge",
      "shop_built": true,
      "parts": [
        {
          "name": "Bed right rail",
          "origin": [
            102,
            -78.5,
            8
          ],
          "size": [
            1.5,
            76,
            8
          ],
          "material": "walnut_solid",
          "grain": "y"
        },
        {
          "name": "Bed right slat ledge",
          "origin": [
            101,
            -78.5,
            14.25
          ],
          "size": [
            1,
            74.5,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "y"
        }
      ]
    },
    {
      "name": "F3 Bed foot assembly",
      "shop_built": true,
      "parts": [
        {
          "name": "Bed footboard",
          "origin": [
            46.5,
            -80,
            8
          ],
          "size": [
            57.0,
            1.5,
            8
          ],
          "material": "walnut_solid",
          "grain": "x"
        },
        {
          "name": "Bed front left leg",
          "origin": [
            46.5,
            -80,
            0
          ],
          "size": [
            3,
            1.5,
            8
          ],
          "material": "walnut_solid",
          "grain": "z",
          "taper_inset": [
            0.5,
            0.25
          ]
        },
        {
          "name": "Bed front right leg",
          "origin": [
            100.5,
            -80,
            0
          ],
          "size": [
            3,
            1.5,
            8
          ],
          "material": "walnut_solid",
          "grain": "z",
          "taper_inset": [
            0.5,
            0.25
          ]
        }
      ]
    },
    {
      "name": "I2 Bed parts - assemble in room",
      "shop_built": false,
      "parts": [
        {
          "name": "Bed head rail",
          "origin": [
            48,
            -4,
            8
          ],
          "size": [
            54,
            1.5,
            8
          ],
          "material": "walnut_solid",
          "grain": "x"
        },
        {
          "name": "Bed center slat ledge",
          "origin": [
            74.25,
            -78.5,
            14.0
          ],
          "size": [
            3.0,
            74.5,
            1.5
          ],
          "material": "walnut_solid",
          "grain": "y"
        },
        {
          "name": "Full mattress",
          "origin": [
            48,
            -78,
            15.5
          ],
          "size": [
            54,
            75,
            10
          ],
          "material": "linen",
          "grain": "y"
        },
        {
          "name": "Bed bridge LED",
          "origin": [
            47.5,
            -2.15,
            71.0
          ],
          "size": [
            55,
            0.4,
            0.25
          ],
          "material": "led",
          "grain": "x"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -78.5,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -73.03846153846153,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -67.57692307692308,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -62.11538461538461,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -56.65384615384615,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -51.19230769230769,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -45.730769230769226,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -40.26923076923077,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -34.80769230769231,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -29.346153846153847,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -23.884615384615387,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -18.42307692307692,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -12.961538461538453,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        },
        {
          "name": "Maple solid bed slat",
          "origin": [
            48,
            -7.5,
            15.0
          ],
          "size": [
            54,
            3.5,
            0.5
          ],
          "material": "maple_solid",
          "grain": "x",
          "definition_name": "Maple solid bed slat"
        }
      ]
    },
    {
      "name": "I3 Shared face frames - fit after installation",
      "shop_built": false,
      "parts": [
        {
          "name": "Shared purpleheart stile 1",
          "origin": [
            44.875,
            -13.75,
            0.0
          ],
          "size": [
            1.5,
            0.75,
            95.5
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Shared purpleheart stile 2",
          "origin": [
            103.625,
            -13.75,
            0.0
          ],
          "size": [
            1.5,
            0.75,
            95.5
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Bed bridge purpleheart stile 1",
          "origin": [
            64.45833333333333,
            -13.75,
            72.75
          ],
          "size": [
            1.5,
            0.75,
            22.0
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Bed bridge purpleheart stile 2",
          "origin": [
            84.04166666666666,
            -13.75,
            72.75
          ],
          "size": [
            1.5,
            0.75,
            22.0
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Far left continuous purpleheart stile",
          "origin": [
            0,
            -13.75,
            0
          ],
          "size": [
            0.75,
            0.75,
            95.5
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        },
        {
          "name": "Far right continuous purpleheart stile",
          "origin": [
            127.25,
            -13.75,
            0
          ],
          "size": [
            0.75,
            0.75,
            95.5
          ],
          "material": "purpleheart_solid",
          "grain": "z"
        }
      ]
    },
    {
      "name": "I4 Shared horizontal face frames - fit after installation",
      "shop_built": false,
      "parts": [
        {
          "name": "Desk continuous horizontal purpleheart face frame",
          "origin": [
            0.75,
            -13.75,
            48.0
          ],
          "size": [
            44.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Desk top continuous horizontal purpleheart face frame",
          "origin": [
            0.75,
            -13.75,
            94.75
          ],
          "size": [
            44.125,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Bed continuous horizontal purpleheart face frame",
          "origin": [
            46.375,
            -13.75,
            71.25
          ],
          "size": [
            57.25,
            0.75,
            1.5
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        },
        {
          "name": "Bed top continuous horizontal purpleheart face frame",
          "origin": [
            46.375,
            -13.75,
            94.75
          ],
          "size": [
            57.25,
            0.75,
            0.75
          ],
          "material": "purpleheart_solid",
          "grain": "x"
        }
      ]
    }
  ],
  "palette": {
    "walnut_solid": [
      107,
      70,
      45
    ],
    "walnut_plywood": [
      107,
      70,
      45
    ],
    "baltic_birch_plywood": [
      224,
      207,
      169
    ],
    "maple_solid": [
      181,
      151,
      114
    ],
    "purpleheart_solid": [
      105,
      50,
      90
    ],
    "linen": [
      227,
      214,
      189
    ],
    "wall": [
      214,
      207,
      191
    ],
    "floor": [
      168,
      125,
      79
    ],
    "led": [
      255,
      158,
      46
    ]
  }
}''')


def box(manager, origin, size):
    center = adsk.core.Point3D.create(*[(o + s / 2) * INCH for o, s in zip(origin, size)])
    bounds = adsk.core.OrientedBoundingBox3D.create(
        center, adsk.core.Vector3D.create(1, 0, 0),
        adsk.core.Vector3D.create(0, 1, 0), *[s * INCH for s in size])
    result = manager.createBox(bounds)
    if not result:
        raise RuntimeError('Could not create box')
    return result


def tapered_leg(component, part):
    w, d, h = part['size']
    ix, iy = part['taper_inset']
    profiles = []
    sketches = []
    for z, x0, y0, x1, y1 in [(0, ix, iy, w-ix, d-iy), (h, 0, 0, w, d)]:
        plane_input = component.constructionPlanes.createInput()
        plane_input.setByOffset(component.xYConstructionPlane, adsk.core.ValueInput.createByReal(z * INCH))
        plane = component.constructionPlanes.add(plane_input)
        sketch = component.sketches.add(plane)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(x0 * INCH, y0 * INCH, 0),
            adsk.core.Point3D.create(x1 * INCH, y1 * INCH, 0))
        profiles.append(sketch.profiles.item(0))
        sketches.append(sketch)
        plane.isLightBulbOn = False
    lofts = component.features.loftFeatures
    request = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    for profile in profiles:
        request.loftSections.add(profile)
    feature = lofts.add(request)
    for sketch in sketches:
        sketch.isLightBulbOn = False
    return feature.bodies.item(0)


def expected_volume(part):
    w, d, h = part['size']
    volume = w * d * h
    if part.get('taper_inset'):
        ix, iy = part['taper_inset']
        # Exact integral of the linearly varying rectangular cross section.
        volume = h * (w*d - w*iy - d*ix + 4*ix*iy/3)
    elif part.get('dado'):
        dado = part['dado']
        axes = 'xyz'
        a = axes.index(dado['axis'])
        b = axes.index(dado.get('slot_axis', 'z'))
        c = next(i for i in range(3) if i not in (a, b))
        volume -= dado['depth'] * dado['height'] * part['size'][c]
    return volume * INCH**3


def make_body(component, part, manager):
    if part.get('corner_radius'):
        raise ValueError('Unexpected rounded part; update the converter before building')
    if part.get('taper_inset'):
        body = tapered_leg(component, part)
    else:
        temporary = box(manager, [0, 0, 0], part['size'])
        if part.get('dado'):
            dado = part['dado']
            a = 'xyz'.index(dado['axis'])
            b = 'xyz'.index(dado.get('slot_axis', 'z'))
            c = next(i for i in range(3) if i not in (a, b))
            origin = [0, 0, 0]
            size = list(part['size'])
            eps = 0.001
            origin[a] = size[a] - dado['depth'] if dado['edge'] == 'high' else -eps
            size[a] = dado['depth'] + eps
            origin[b], size[b] = dado['bottom'], dado['height']
            origin[c], size[c] = -eps, size[c] + 2*eps
            cutter = box(manager, origin, size)
            if not manager.booleanOperation(temporary, cutter, adsk.fusion.BooleanTypes.DifferenceBooleanType):
                raise RuntimeError('Dado subtraction failed: ' + part['name'])
        body = component.bRepBodies.add(temporary)
    if not body or not body.isSolid:
        raise RuntimeError('Invalid solid: ' + part['name'])
    if not math.isclose(body.volume, expected_volume(part), rel_tol=1e-5, abs_tol=1e-5):
        raise RuntimeError('Volume mismatch: ' + part['name'])
    body.name = part['name']
    return body


WOOD_IMAGES = {
    'walnut_solid': ('walnut_solid.png', 'u'),
    'walnut_plywood': ('walnut_plywood.png', 'v'),
    'purpleheart_solid': ('purpleheart_solid.png', 'u'),
}
WOOD_SPECIES = {'walnut_solid', 'walnut_plywood', 'purpleheart_solid',
                'maple_solid', 'baltic_birch_plywood'}


def make_appearances(app, design):
    """Restore the image-based appearance setup from the successful render."""
    logger = logging.getLogger('MyriBuiltin_MkIII')
    result = {}
    for name, rgb in DATA['palette'].items():
        appearance = design.appearances.add('MkIII ' + name)
        if not appearance:
            raise RuntimeError('Could not create appearance: ' + name)
        appearance.color = adsk.core.Color.create(*rgb, 255)
        appearance.roughness = 0.4 if name in WOOD_SPECIES else 0.65
        if name in WOOD_IMAGES:
            path = Path(__file__).resolve().parent / 'textures' / WOOD_IMAGES[name][0]
            if not path.is_file():
                raise FileNotFoundError('Missing wood texture: ' + str(path))
            appearance.colorTexture = str(path)
            if not appearance.colorTexture:
                raise RuntimeError('Fusion did not retain texture: ' + str(path))
            # Keep Fusion's default image scale, as in the successful render.
            logger.info('Appearance %s: image=%s', name, path)
        else:
            logger.info('Appearance %s: RGB=%s', name, rgb)
        result[name] = appearance
    return result, []


def orient_texture(body, part):
    if part['material'] not in WOOD_SPECIES:
        return
    control = body.textureMapControl
    if not control:
        return
    vector = adsk.core.Vector3D.create
    axes = {'x': vector(1, 0, 0), 'y': vector(0, 1, 0), 'z': vector(0, 0, 1)}
    grain = axes[part['grain']]
    other = axes['z'] if part['grain'] != 'z' else axes['x']
    mapping3d = adsk.core.TextureMapControl3D.cast(control)
    if mapping3d:
        z = grain
        x = other
        y = z.crossProduct(x)
    else:
        projected = adsk.core.ProjectedTextureMapControl.cast(control)
        if not projected:
            return
        projected.projectedTextureMapType = adsk.core.ProjectedTextureMapTypes.BoxTextureMapProjection
        direction = WOOD_IMAGES.get(part['material'], ('', 'u'))[1]
        x, y = (grain, other) if direction == 'u' else (other, grain)
        z = x.crossProduct(y)
    transform = adsk.core.Matrix3D.create()
    transform.setWithCoordinateSystem(adsk.core.Point3D.create(0, 0, 0), x, y, z)
    control.transform = transform


def run(context):
    log_path = Path(__file__).resolve().with_suffix('.log')
    logger = logging.getLogger('MyriBuiltin_MkIII')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    # Fusion can reload the script in the same Python process.
    for old_handler in list(logger.handlers):
        logger.removeHandler(old_handler)
        old_handler.close()
    try:
        handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    except OSError:
        adsk.core.Application.get().userInterface.messageBox(
            'Cannot create troubleshooting log: {}\n\n{}'.format(log_path, traceback.format_exc()))
        return
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    started = time.monotonic()
    ui = None
    current = 'initialization'
    count = 0
    try:
        logger.info('=== RUN START ===')
        logger.info('Script=%s | Python=%s | OS=%s', __file__, sys.version, platform.platform())
        logger.info('Options: SHOW_MATTRESS=%s SHOW_LIGHTING=%s', SHOW_MATTRESS, SHOW_LIGHTING)
        app = adsk.core.Application.get()
        ui = app.userInterface
        logger.info('Fusion version=%s', getattr(app, 'version', 'unknown'))
        logger.info('Creating new document')
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name = 'MyriBuiltin_MkIII'
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent
        # Fusion names the root component from the document; it is not writable.
        logger.info('Document created: %s', doc.name)
        warnings = []
        current = 'material appearance setup'
        try:
            appearances, material_warnings = make_appearances(app, design)
            warnings.extend(material_warnings)
            if not appearances:
                warnings.append('No compatible color appearance found; material names are stored as attributes.')
        except Exception as error:
            logger.exception('Material appearance setup failed')
            raise RuntimeError('Could not create material appearances; see log') from error
        for warning in warnings:
            logger.warning(warning)
        logger.info('Created %d material appearances', len(appearances))
        manager = adsk.fusion.TemporaryBRepManager.get()
        count = 0
        for assembly in DATA['assemblies']:
            current = assembly['name']
            logger.info('Assembly: %s (%d parts)', current, len(assembly['parts']))
            occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            group = occurrence.component
            group.name = assembly['name']
            group.attributes.add('MyriBuiltin_MkIII', 'shop_built', json.dumps(assembly['shop_built']))
            for part in assembly['parts']:
                current = part['name']
                logger.info('Part %d START: %s | data=%s', count + 1, current, json.dumps(part, sort_keys=True))
                transform = adsk.core.Matrix3D.create()
                transform.translation = adsk.core.Vector3D.create(*[n * INCH for n in part['origin']])
                occurrence = group.occurrences.addNewComponent(transform)
                component = occurrence.component
                component.name = current
                logger.debug('Creating geometry: %s', current)
                body = make_body(component, part, manager)
                logger.debug('Geometry OK: volume_cm3=%.9f expected_cm3=%.9f', body.volume, expected_volume(part))
                for key, value in part.items():
                    component.attributes.add('MyriBuiltin_MkIII', key, json.dumps(value))
                appearance = appearances[part['material']]
                if appearance:
                    body.appearance = appearance
                    assigned = body.appearance
                    if not assigned or assigned.id != appearance.id:
                        raise RuntimeError('Appearance assignment did not persist: ' + current)
                    logger.info('Appearance applied: %s | material=%s | appearance=%s | texture=%s',
                                current, part['material'], assigned.name, assigned.hasTexture)
                    try:
                        orient_texture(body, part)
                    except Exception:
                        logger.exception('Texture mapping failed for %s', current)
                        warning = 'Some grain orientations could not be applied; see the log.'
                        if warning not in warnings:
                            warnings.append(warning)
                occurrence.isLightBulbOn = not (
                    (part['material'] == 'linen' and not SHOW_MATTRESS) or
                    (part['material'] == 'led' and not SHOW_LIGHTING))
                count += 1
                logger.info('Part %d COMPLETE: %s', count, current)
            adsk.doEvents()
        current = 'viewport fit'
        app.activeViewport.fit()
        logger.info('BUILD COMPLETE: %d parts in %d assemblies', count, len(DATA['assemblies']))
        ui.messageBox('Created {} parts in {} assemblies.\nSave this new design as an .f3d file.{}\n\nLog: {}'.format(
            count, len(DATA['assemblies']), '\n\n' + '\n'.join(warnings) if warnings else '', log_path))
    except Exception:
        logger.exception('BUILD FAILED at %s after %d completed parts', current, count)
        if ui:
            ui.messageBox('MkIII build failed at {}.\nThe new document may be incomplete.\nLog: {}\n\n{}'.format(
                current, log_path, traceback.format_exc()))
    finally:
        logger.info('=== RUN END: %.2f seconds; %d completed parts ===', time.monotonic() - started, count)
        handler.flush()
        logger.removeHandler(handler)
        handler.close()
