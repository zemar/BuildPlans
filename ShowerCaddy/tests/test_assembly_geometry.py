"""Dimension and fit regressions. Run with Python; Fusion is not needed."""
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
adsk = ModuleType('adsk')
adsk.core = ModuleType('adsk.core')
adsk.fusion = ModuleType('adsk.fusion')
with patch.dict(sys.modules, {'adsk': adsk, 'adsk.core': adsk.core, 'adsk.fusion': adsk.fusion}):
    spec = importlib.util.spec_from_file_location('caddy', ROOT/'ShowerCaddy.py')
    caddy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(caddy)


class AssemblyGeometry(unittest.TestCase):
    def test_overall_dimensions(self):
        self.assertEqual(caddy.validate(), 305)
        self.assertEqual(caddy.HOOK_WIDTH, 25)
        self.assertEqual(caddy.HOOK_THICKNESS, 10)
        self.assertEqual(caddy.HOOK_RISE+caddy.HOOK_THICKNESS, 315)

    def test_taper_arcs_join_with_common_tangent(self):
        r, theta = caddy.taper_geometry()
        w, h = caddy.ROOT_WEB_WIDTH, caddy.ROOT_TAPER_HEIGHT
        # First arc travels half the lateral/vertical taper; second is mirrored.
        self.assertAlmostEqual(r*(1-math.cos(theta)), w/2)
        self.assertAlmostEqual(r*math.sin(theta), h/2)
        self.assertEqual(h, 40)
        # Tangent at the first arc's end equals the reversed second arc's start.
        joint = (caddy.HOOK_WIDTH+w/2, caddy.SIDE_HEIGHT+h/2)
        center1 = (caddy.HOOK_WIDTH+w-r, caddy.SIDE_HEIGHT)
        center2 = (caddy.HOOK_WIDTH+r, caddy.SIDE_HEIGHT+h)
        radial1 = tuple((joint[i]-center1[i])/r for i in range(2))
        radial2 = tuple((joint[i]-center2[i])/r for i in range(2))
        for a,b in zip(radial1,radial2):
            self.assertAlmostEqual(a,-b)
        self.assertGreater(r, 20)  # Broad R25 blend, not a sharp triangle.

    def test_four_aligned_mounts_with_edge_margin(self):
        points = caddy.mount_positions()
        self.assertEqual(len(points), 4)
        for x,z in points:
            nut_radius = caddy.NUT_ACROSS_FLATS/math.sqrt(3)
            self.assertGreater(min(x,caddy.BASKET_WIDTH-x), nut_radius+2)
            self.assertGreater(z-caddy.ARM_BOTTOM,nut_radius+2)
            self.assertGreater(caddy.SIDE_HEIGHT-10-z,nut_radius+2)

    def test_m4_hardware_engagement_and_closed_glass_side(self):
        # M4x16 bolt and 1 mm washer, head seated against inner mounting pad.
        insertion = 16-1-caddy.MOUNT_PAD_THICKNESS-caddy.ASSEMBLY_GAP
        self.assertGreater(insertion,caddy.NUT_POCKET_DEPTH)
        self.assertLess(insertion,caddy.BOLT_BLIND_DEPTH)
        self.assertGreaterEqual(caddy.HOOK_THICKNESS-caddy.BOLT_BLIND_DEPTH,1.5)

    def test_arm_basket_gap_and_hook_throat(self):
        front = -caddy.ASSEMBLY_GAP
        rear = front-caddy.HOOK_THICKNESS
        return_front = rear-caddy.HOOK_CLEARANCE
        self.assertLessEqual(front,0)
        self.assertAlmostEqual(rear-return_front,25.5)
        self.assertGreaterEqual(0-rear,10)

    def test_panel_recess_backing_and_clearance(self):
        data,scale,width=caddy.load_inlay()
        self.assertGreaterEqual(caddy.WALL_THICKNESS-caddy.PANEL_THICKNESS-caddy.PANEL_ADHESIVE_GAP,1)
        self.assertGreater(caddy.PANEL_THICKNESS-caddy.INLAY_DEPTH,1)
        self.assertGreater(caddy.PANEL_CLEARANCE,0)
        self.assertLess(caddy.INLAY_HEIGHT+2*caddy.PANEL_BORDER+2*caddy.PANEL_CLEARANCE,
                        caddy.SIDE_HEIGHT-2*caddy.FLOOR_THICKNESS)
        self.assertLess(width+2*caddy.PANEL_BORDER,caddy.BASKET_WIDTH)
        self.assertEqual(set(p['color'] for p in data['polygons']),set(caddy.INLAY_COLORS))

    def test_invalid_pocket_depth_rejected(self):
        with patch.object(caddy,'PANEL_THICKNESS',3):
            with self.assertRaises(ValueError):
                caddy.validate()

    def test_invalid_blind_hole_rejected(self):
        with patch.object(caddy,'BOLT_BLIND_DEPTH',11):
            with self.assertRaises(ValueError):
                caddy.validate()


if __name__ == '__main__':
    unittest.main()
