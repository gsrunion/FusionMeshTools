"""Run with python3 -m unittest discover -s <this folder>."""
import unittest
from FusionMeshTools import boundary_geometry as geo


class BoundaryTests(unittest.TestCase):
    def test_unwelded_stl_square(self):
        loops = geo.boundary_loops(
            [0,0,0, 1,0,0, 1,1,0, 0,0,0, 1,1,0, 0,1,0], list(range(6)))
        self.assertEqual([len(loop) for loop in loops], [4])
        self.assertEqual(len(geo.split_corners(loops[0])), 4)

    def test_hole_and_outer_loop(self):
        vertices = [(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0),
                    (-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)]
        triangles = []
        for i in range(4):
            j = (i+1) % 4
            triangles.extend([i,j,4+j, i,4+j,4+i])
        loops = geo.boundary_loops([x for p in vertices for x in p], triangles)
        self.assertEqual(sorted(map(len, loops)), [4,4])

    def test_closed_mesh_has_no_boundary(self):
        loops = geo.boundary_loops([0,0,0,1,0,0,0,1,0,0,0,1],
                                  [0,2,1,0,1,3,1,2,3,2,0,3])
        self.assertEqual(loops, [])

    def test_duplicate_triangles_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            geo.boundary_loops([0,0,0,1,0,0,0,1,0], [0,1,2,0,1,2])

    def test_nonmanifold_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Non-manifold'):
            geo.boundary_loops([0,0,0,1,0,0,0,1,0,0,-1,0,0,0,1],
                               [0,1,2,1,0,3,0,1,4])

    def test_simplification_keeps_bend_and_3d_coordinates(self):
        points = [(0,0,2),(.5,0,2),(1,0,2),(1,.5,3),(1,1,4)]
        self.assertEqual(geo.simplify(points, .001), [points[0],points[2],points[4]])


if __name__ == '__main__':
    unittest.main()
