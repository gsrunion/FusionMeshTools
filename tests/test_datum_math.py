import unittest
from FusionMeshTools import datum_math as math3
from FusionMeshTools import plane_fit as fit

class DatumTests(unittest.TestCase):
    def test_intersection_to_origin_and_rigid_axes(self):
        point=[3,4,5]
        planes=[(point,[0,1,0]),(point,[1,0,0]),(point,[0,0,1])]
        matrix,origin,_=math3.alignment(planes)
        self.assertEqual(origin,point)
        self.assertEqual(math3.transform_point(matrix,point),[0,0,0])
        rows=[matrix[i*4:i*4+3] for i in range(3)]
        self.assertAlmostEqual(fit.dot(rows[0],fit.cross(rows[1],rows[2])),1.)

    def test_primary_priority_for_nonorthogonal_planes(self):
        point=[7,-2,4]
        planes=[(point,[0,0,1]),(point,[0,1,.05]),(point,[1,.04,.02])]
        matrix,origin,departures=math3.alignment(planes)
        self.assertEqual(matrix[8:11],[0,0,1])
        self.assertEqual(matrix[4:7],[0,1,0])
        self.assertGreater(max(departures),0.)
        self.assertLess(max(abs(x) for x in math3.transform_point(matrix,point)),1e-12)

    def test_flips_preserve_right_handedness(self):
        planes=[([0,0,0],[0,0,1]),([0,0,0],[0,1,0]),([0,0,0],[1,0,0])]
        for primary in (False,True):
            for secondary in (False,True):
                matrix,_,_=math3.alignment(planes,primary,secondary)
                rows=[matrix[i*4:i*4+3] for i in range(3)]
                self.assertAlmostEqual(fit.dot(rows[0],fit.cross(rows[1],rows[2])),1.)
                self.assertAlmostEqual(rows[2][2],-1 if primary else 1)
                self.assertAlmostEqual(rows[1][1],-1 if secondary else 1)

    def test_parallel_datums_rejected(self):
        with self.assertRaises(ValueError):
            math3.alignment([([0,0,0],[0,0,1]),([0,0,0],[0,0,1]),([0,0,0],[1,0,0])])


if __name__=='__main__':unittest.main()
