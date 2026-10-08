"""Dimension and mesh checks outside Fusion; no CAD or physical-fit claims."""
import ast
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'Drawer1.py'


def load_design():
    tree = ast.parse(SOURCE.read_text())
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.Import) and any(a.name.startswith('adsk') for a in node.names))]
    namespace = {'__file__': str(SOURCE)}
    exec(compile(tree, str(SOURCE), 'exec'), namespace)
    return namespace


def box_stl(width, length, height, origin=(0, 0, 0)):
    """Binary cuboid mesh with an optional translation, for export checks."""
    vertices = [(x + origin[0], y + origin[1], z + origin[2])
                for x, y, z in ((0, 0, 0), (width, 0, 0), (width, length, 0),
                                (0, length, 0), (0, 0, height), (width, 0, height),
                                (width, length, height), (0, length, height))]
    faces = ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
             (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
             (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7))
    data = bytearray(80)
    data.extend(struct.pack('<I', len(faces)))
    for face in faces:
        coordinates = [value for i in face for value in vertices[i]]
        data.extend(struct.pack('<12fH', 0, 0, 0, *coordinates, 0))
    return data


class LayoutTests(unittest.TestCase):
    def test_four_complete_bin_dimensions(self):
        design = load_design()
        width, depth, bins = design['layout']()
        self.assertAlmostEqual(width, 242.475)
        self.assertAlmostEqual(depth, 525.05)
        self.assertAlmostEqual(design['BIN_WIDTH'], 121.0375)
        self.assertAlmostEqual(design['BIN_WIDTH'] - 2 * design['WALL'], 116.2375)
        self.assertAlmostEqual(design['HEIGHT'], 65)
        self.assertAlmostEqual(design['HEIGHT'] - design['FLOOR'], 63)
        expected = {
            'Long_Left': (360.4, 355.6),
            'Long_Right': (309.6, 304.8),
            'Short_Left': (164.25, 159.45),
            'Short_Right': (215.05, 210.25),
        }
        self.assertEqual({name for name, x, y, length in bins}, set(expected))
        self.assertEqual(len(bins), 4)
        for name, x, y, length in bins:
            exterior, clear = expected[name]
            self.assertAlmostEqual(length, exterior, msg=name)
            self.assertAlmostEqual(length - 2 * design['WALL'], clear, msg=name)
        self.assertGreaterEqual(expected['Long_Left'][1], design['TOOL_LENGTH'])
        self.assertGreater(design['LONG_BAY_WIDTH'], design['TOOL_WIDTH'])

    def test_independent_bins_fit_drawer_without_overlap(self):
        design = load_design()
        width, depth, bins = design['layout']()
        bin_width = design['BIN_WIDTH']
        rectangles = {name: (x, y, x + bin_width, y + length)
                      for name, x, y, length in bins}
        for name, (x0, y0, x1, y1) in rectangles.items():
            self.assertGreaterEqual(x0, 0, name)
            self.assertGreaterEqual(y0, 0, name)
            self.assertLessEqual(x1, width + 1e-8, name)
            self.assertLessEqual(y1, depth + 1e-8, name)
        for i, first in enumerate(bins):
            for second in bins[i + 1:]:
                a, b = rectangles[first[0]], rectangles[second[0]]
                self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or
                                a[3] <= b[1] or b[3] <= a[1],
                                (first[0], second[0]))
        for side in ('Left', 'Right'):
            long = rectangles['Long_' + side]
            short = rectangles['Short_' + side]
            self.assertAlmostEqual(short[1] - long[3], 0.4)
            self.assertAlmostEqual(short[3], depth)
        self.assertAlmostEqual(rectangles['Long_Right'][0] - rectangles['Long_Left'][2], 0.4)
        self.assertAlmostEqual(design['DRAWER_WIDTH'] - width, 2)
        self.assertAlmostEqual(design['DRAWER_DEPTH'] - depth, 2)
        self.assertLess(design['HEIGHT'], design['DRAWER_HEIGHT'])

    def test_oversize_whole_bin_exports_flat_at_origin(self):
        design = load_design()
        width, length, height = 121.0375, 360.4, 65
        self.assertGreater(length, 320)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'long_bin.stl'
            path.write_bytes(box_stl(width, length, height, origin=(17, -25, 6)))
            size = design['normalize_binary_stl'](path)
            for actual, expected in zip(size, (width, length, height)):
                self.assertAlmostEqual(actual, expected, places=4)
            data = path.read_bytes()
            count = struct.unpack_from('<I', data, 80)[0]
            vertices = [struct.unpack_from('<3f', data, 84 + i * 50 + j * 4)
                        for i in range(count) for j in (3, 6, 9)]
            for axis, expected in enumerate((width, length, height)):
                self.assertAlmostEqual(min(v[axis] for v in vertices), 0)
                self.assertAlmostEqual(max(v[axis] for v in vertices), expected, places=4)

    def test_invalid_meshes_are_rejected(self):
        design = load_design()
        nonfinite = box_stl(10, 20, 30)
        struct.pack_into('<f', nonfinite, 84 + 12, float('nan'))
        cases = {
            'truncated': b'incomplete',
            'empty': bytes(84),
            'nonfinite': nonfinite,
            'zero_height': box_stl(10, 20, 0),
        }
        with TemporaryDirectory() as directory:
            for name, data in cases.items():
                with self.subTest(name=name):
                    path = Path(directory) / (name + '.stl')
                    path.write_bytes(data)
                    with self.assertRaises((RuntimeError, ValueError)):
                        design['normalize_binary_stl'](path)


if __name__ == '__main__':
    unittest.main()
