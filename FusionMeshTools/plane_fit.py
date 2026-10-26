"""Area-integrated least-squares plane fitting, without external dependencies."""
import math


def dot(a,b): return sum(x*y for x,y in zip(a,b))
def sub(a,b): return [x-y for x,y in zip(a,b)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(a):
    length=math.sqrt(dot(a,a))
    if length < 1e-15: raise ValueError('Degenerate direction.')
    return [x/length for x in a]


def eigensystem(matrix):
    a=[list(row) for row in matrix]
    vectors=[[float(i==j) for j in range(3)] for i in range(3)]
    scale=max(abs(x) for row in a for x in row)
    for _ in range(60):
        p,q=max(((0,1),(0,2),(1,2)),key=lambda pair:abs(a[pair[0]][pair[1]]))
        if abs(a[p][q]) <= max(scale*1e-14,1e-30): break
        angle=.5*math.atan2(2*a[p][q],a[q][q]-a[p][p])
        c,s=math.cos(angle),math.sin(angle)
        # R columns: (c,-s), (s,c); update A = R^T A R.
        r=[[float(i==j) for j in range(3)] for i in range(3)]
        r[p][p]=r[q][q]=c; r[p][q]=s; r[q][p]=-s
        ar=[[sum(a[i][k]*r[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        a=[[sum(r[k][i]*ar[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
        vectors=[[sum(vectors[i][k]*r[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return sorted((a[j][j],unit([vectors[i][j] for i in range(3)])) for j in range(3))


def statistics(coordinates, indices):
    vertices=[coordinates[i:i+3] for i in range(0,len(coordinates),3)]
    if not vertices: raise ValueError('Empty mesh.')
    anchor=vertices[0]
    total=0.; first=[0.]*3; second=[[0.]*3 for _ in range(3)]
    used=set()
    for k in range(0,len(indices),3):
        ids=indices[k:k+3]
        a,b,c=[sub(vertices[i],anchor) for i in ids]
        area=math.sqrt(dot(cross(sub(b,a),sub(c,a)),cross(sub(b,a),sub(c,a))))/2
        if area <= 1e-20: continue
        used.update(ids); total+=area
        sums=[a[i]+b[i]+c[i] for i in range(3)]
        for i in range(3):
            first[i]+=area*sums[i]/3
            for j in range(3):
                second[i][j]+=area*(a[i]*a[j]+b[i]*b[j]+c[i]*c[j]+sums[i]*sums[j])/12
    if total <= 1e-20: raise ValueError('Mesh has no nondegenerate triangles.')
    mean=[x/total for x in first]
    covariance=[[second[i][j]/total-mean[i]*mean[j] for j in range(3)] for i in range(3)]
    return [mean[i]+anchor[i] for i in range(3)],covariance,[vertices[i] for i in used]


def fit(coordinates,indices,mode='Best fit',reference=None):
    centroid,covariance,vertices=statistics(coordinates,indices)
    eigen=eigensystem(covariance)
    if eigen[1][0] <= max(eigen[2][0]*1e-12,1e-20):
        raise ValueError('Mesh is too narrow or degenerate to define a plane.')
    normal=eigen[0][1]; origin=centroid[:]
    if mode != 'Best fit':
        if reference is None: raise ValueError('Select a reference plane or planar face.')
        ref_origin,ref_normal=reference
        r=unit(ref_normal)
        if mode in ('Parallel','Coincident'):
            normal=r
            if mode=='Coincident': origin=list(ref_origin)
        elif mode=='Perpendicular':
            helper=min(([1,0,0],[0,1,0],[0,0,1]),key=lambda v:abs(dot(v,r)))
            u=unit(cross(r,helper)); v=unit(cross(r,u))
            quadratic=lambda x,y:sum(x[i]*covariance[i][j]*y[j] for i in range(3) for j in range(3))
            aa,bb,cc=quadratic(u,u),quadratic(u,v),quadratic(v,v)
            angle=.5*math.atan2(2*bb,aa-cc)+math.pi/2
            normal=unit([math.cos(angle)*u[i]+math.sin(angle)*v[i] for i in range(3)])
        else: raise ValueError('Unknown constraint mode.')
    if normal[max(range(3),key=lambda i:abs(normal[i]))] < 0: normal=[-x for x in normal]
    variance=sum(normal[i]*covariance[i][j]*normal[j] for i in range(3) for j in range(3))
    displacement=dot(normal,sub(centroid,origin))
    rms=math.sqrt(max(0.,variance)+displacement**2)
    maximum=max(abs(dot(normal,sub(p,origin))) for p in vertices)
    return origin,normal,rms,maximum
