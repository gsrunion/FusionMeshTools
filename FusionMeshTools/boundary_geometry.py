"""Dependency-free mesh boundary topology and curve segmentation. Units: cm."""
import math
from collections import Counter, defaultdict


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def distance(a, b):
    return norm(sub(a, b))


def segment_distance(p, a, b):
    v = sub(b, a)
    t = max(0., min(1., dot(sub(p, a), v) / max(dot(v, v), 1e-30)))
    return distance(p, tuple(x+t*y for x, y in zip(a, v)))


def boundary_loops(coordinates, indices, weld=1e-7):
    """Weld STL seam duplicates, reject ambiguous topology, order every perimeter."""
    points, mapping, buckets = [], [], defaultdict(list)
    for i in range(0, len(coordinates), 3):
        p = tuple(coordinates[i:i+3])
        key = tuple(math.floor(x/weld) for x in p)
        match = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in buckets[(key[0]+dx, key[1]+dy, key[2]+dz)]:
                        if distance(p, points[j]) <= weld:
                            match = j
                            break
        if match is None:
            match = len(points)
            points.append(p)
            buckets[key].append(match)
        mapping.append(match)
    edges, triangles = Counter(), set()
    for i in range(0, len(indices), 3):
        tri = tuple(mapping[j] for j in indices[i:i+3])
        if len(set(tri)) != 3:
            continue
        key = tuple(sorted(tri))
        if key in triangles:
            raise ValueError('Duplicate triangles found. Repair the mesh first.')
        triangles.add(key)
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edges[tuple(sorted((a, b)))] += 1
    if any(n > 2 for n in edges.values()):
        raise ValueError('Non-manifold mesh edges found. Repair the mesh first.')
    boundary = {edge for edge, count in edges.items() if count == 1}
    neighbors = defaultdict(list)
    for a, b in boundary:
        neighbors[a].append(b)
        neighbors[b].append(a)
    if any(len(v) != 2 for v in neighbors.values()):
        raise ValueError('Branching or touching boundaries found. Repair the mesh first.')
    loops = []
    while boundary:
        a, b = min(boundary)
        loop = [a]
        previous, current = a, b
        boundary.remove((a, b))
        while current != a:
            loop.append(current)
            nxt = next(j for j in neighbors[current] if j != previous)
            boundary.remove(tuple(sorted((current, nxt))))
            previous, current = current, nxt
        loops.append([points[j] for j in loop])
    return loops


def split_corners(loop, angle_degrees=35):
    corners = []
    n = len(loop)
    for i in range(n):
        u, v = sub(loop[i], loop[i-1]), sub(loop[(i+1) % n], loop[i])
        cosine = dot(u, v) / max(norm(u)*norm(v), 1e-30)
        if math.acos(max(-1., min(1., cosine))) >= math.radians(angle_degrees):
            corners.append(i)
    # Two spans avoid coincident spline/arc endpoints on smooth closed loops.
    if not corners:
        corners = [0, max(1, n//2)]
    elif len(corners) == 1:
        corners.append((corners[0]+n//2) % n)
        corners.sort()
    spans = []
    for i, start in enumerate(corners):
        end = corners[(i+1) % len(corners)]
        if end <= start:
            end += n
        spans.append([loop[j % n] for j in range(start, end+1)])
    return spans


def simplify(points, tolerance):
    keep, stack = {0, len(points)-1}, [(0, len(points)-1)]
    while stack:
        first, last = stack.pop()
        if last-first < 2:
            continue
        error, index = max((segment_distance(points[j], points[first], points[last]), j)
                           for j in range(first+1, last))
        if error > tolerance:
            keep.add(index)
            stack.extend(((first, index), (index, last)))
    return [points[i] for i in sorted(keep)]


def sampled_deviation(a, b):
    """Symmetric vertex-and-midpoint distance between stroked polylines."""
    def directed(source, target):
        samples = source + [tuple((x+y)/2 for x, y in zip(p, q)) for p, q in zip(source, source[1:])]
        segments = list(zip(target, target[1:]))
        return max(min(segment_distance(p, x, y) for x, y in segments) for p in samples)
    return max(directed(a, b), directed(b, a))
