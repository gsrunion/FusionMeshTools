import math
import unittest
from FusionMeshTools import plane_fit as fit


class PlaneFitTests(unittest.TestCase):
    coordinates=[0,0,2,2,0,3,2,2,3,0,2,2]
    indices=[0,1,2,0,2,3]

    def test_tilted_plane(self):
        origin,normal,rms,maximum=fit.fit(self.coordinates,self.indices)
        self.assertAlmostEqual(abs(fit.dot(normal,fit.unit([-.5,0,1]))),1.)
        self.assertLess(maximum,1e-12)
        self.assertLess(rms,1e-7)

    def test_constraints(self):
        reference=([0,0,0],[0,0,1])
        origin,normal,rms,maximum=fit.fit(self.coordinates,self.indices,'Parallel',reference)
        self.assertAlmostEqual(origin[2],2.5)
        self.assertAlmostEqual(abs(normal[2]),1.)
        self.assertAlmostEqual(rms,math.sqrt(1/12))
        origin,normal,_,_=fit.fit(self.coordinates,self.indices,'Perpendicular',reference)
        self.assertAlmostEqual(normal[2],0.)
        origin,normal,_,_=fit.fit(self.coordinates,self.indices,'Coincident',reference)
        self.assertEqual(origin,[0,0,0])

    def test_triangulation_density_does_not_change_fit(self):
        coords=[0,0,0,2,0,0,0,2,0,0,0,1]
        a=fit.fit(coords,[0,1,2,0,1,3])
        # Subdivide only the first triangle into three around its centroid.
        refined=coords+[2/3,2/3,0]
        b=fit.fit(refined,[0,1,4,1,2,4,2,0,4,0,1,3])
        for x,y in zip(a[0],b[0]):self.assertAlmostEqual(x,y)
        self.assertAlmostEqual(abs(fit.dot(a[1],b[1])),1.)
        self.assertAlmostEqual(a[2],b[2])

    def test_eigenvectors_satisfy_eigen_equation(self):
        matrix=[[4,1,2],[1,3,-1],[2,-1,6]]
        for value,vector in fit.eigensystem(matrix):
            for i in range(3):
                self.assertAlmostEqual(sum(matrix[i][j]*vector[j] for j in range(3)),value*vector[i])

    def test_degenerate_mesh_rejected(self):
        with self.assertRaises(ValueError):fit.fit([0,0,0,1,0,0,2,0,0],[0,1,2])


if __name__=='__main__':unittest.main()
