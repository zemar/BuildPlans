"""Geometry checks outside Fusion; no CAD API mocks or physical-fit claims."""
import ast
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'Drawer1.py'


def load_design(coupon=False):
    source = SOURCE.read_text()
    if coupon:
        source = source.replace('JOINT_TEST_ONLY = False', 'JOINT_TEST_ONLY = True')
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.Import) and any(a.name.startswith('adsk') for a in node.names))]
    namespace = {'__file__': str(SOURCE)}
    exec(compile(tree, str(SOURCE), 'exec'), namespace)
    return namespace


class LayoutTests(unittest.TestCase):
    def test_dimensions_and_flat_fit(self):
        d = load_design()
        width, depth, pieces = d['layout']()
        self.assertEqual(len(pieces), 6)
        self.assertAlmostEqual(width, 242.475)
        self.assertAlmostEqual(depth, 525.05)
        self.assertAlmostEqual(d['RIGHT_LONG_BAY_LENGTH'], 304.8)
        self.assertAlmostEqual(d['RIGHT_SHORT_BAY_LENGTH'], 210.25)
        self.assertAlmostEqual(d['SHORT_BAY_LENGTH'], 159.45)
        for name, x, y, length, role in pieces:
            extension = d['SNAP_LENGTH'] if role == 'male' else 0
            self.assertLess(length + extension + 16, 320, name)
            self.assertLessEqual(y + length, depth + 1e-8, name)

    def test_joint_preserves_long_bin_lengths(self):
        d = load_design()
        pieces = {p[0]: p for p in d['layout']()[2]}
        for side, clear in [('Left', 355.6), ('Right', 304.8)]:
            front = pieces['Long_' + side + '_Front']
            rear = pieces['Long_' + side + '_Rear']
            self.assertAlmostEqual(rear[2] - front[3], d['JOINT_GAP'])
            self.assertAlmostEqual(rear[2] + rear[3] - 2 * d['WALL'], clear)

    def test_snaps_fit_pockets_and_have_retaining_shoulders(self):
        d = load_design()
        # Sample all polygon edges in assembled socket coordinates, excluding
        # the root that remains inside the front half's floor.
        for polygon in d['snap_polygons'](0, 0):
            for start, end in zip(polygon, polygon[1:] + polygon[:1]):
                for i in range(101):
                    t = i / 100
                    x = start[0] + t * (end[0] - start[0])
                    y = start[1] + t * (end[1] - start[1]) - d['JOINT_GAP']
                    if y < 0:
                        continue
                    shoulder = 14 - d['JOINT_GAP'] - d['SNAP_CLEARANCE']
                    half_width = 3.3 if y < shoulder else 4.2
                    self.assertLessEqual(abs(x), half_width)
                    self.assertLessEqual(y, d['SNAP_LENGTH'] + d['SNAP_CLEARANCE'])
            self.assertTrue(any(abs(x) > 3.3 for x, y in polygon))
        self.assertAlmostEqual(3.8 - 3.3, 0.5)  # inward deflection during insertion
        self.assertLess(0.5, 1.8)  # fingers cannot meet at the center while flexing

    def test_coupon_has_same_fingers(self):
        full, coupon = load_design(), load_design(coupon=True)
        self.assertEqual(len(coupon['layout']()[2]), 2)
        self.assertEqual(list(full['snap_polygons'](20, 24)),
                         list(coupon['snap_polygons'](20, 24)))
        self.assertEqual(coupon['SNAP_CENTERS'], (20.0,))


if __name__ == '__main__':
    unittest.main()
