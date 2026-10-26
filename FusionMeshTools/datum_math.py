"""Priority 3-2-1 plane datum frame; rigid transforms only."""
import math
from .plane_fit import dot,sub,cross,unit


def alignment(planes,flip_primary=False,flip_secondary=False):
    if len(planes)!=3: raise ValueError('Select three datum planes.')
    origins=[p[0] for p in planes]
    normals=[unit(p[1]) for p in planes]
    z=[v*(-1 if flip_primary else 1) for v in normals[0]]
    secondary=[v*(-1 if flip_secondary else 1) for v in normals[1]]
    projected=[secondary[i]-dot(secondary,z)*z[i] for i in range(3)]
    if dot(projected,projected)<1e-10:
        raise ValueError('Primary and secondary planes are parallel or nearly parallel.')
    y=unit(projected);x=unit(cross(y,z))
    determinant=dot(normals[0],cross(normals[1],normals[2]))
    if abs(determinant)<1e-5:
        raise ValueError('The three planes do not define a stable datum intersection.')
    distances=[dot(n,p) for n,p in zip(normals,origins)]
    terms=[cross(normals[1],normals[2]),cross(normals[2],normals[0]),cross(normals[0],normals[1])]
    origin=[sum(distances[j]*terms[j][i] for j in range(3))/determinant for i in range(3)]
    rows=[x,y,z]
    matrix=[]
    for row in rows: matrix.extend(row+[-dot(row,origin)])
    matrix.extend([0.,0.,0.,1.])
    departures=[math.degrees(math.asin(min(1.,abs(dot(normals[a],normals[b]))))) for a,b in ((0,1),(0,2),(1,2))]
    return matrix,origin,departures


def multiply(a,b):
    return [sum(a[i*4+k]*b[k*4+j] for k in range(4)) for i in range(4) for j in range(4)]


def transform_point(matrix,p):
    return [sum(matrix[i*4+j]*p[j] for j in range(3))+matrix[i*4+3] for i in range(3)]
