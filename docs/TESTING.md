# Testing

## Automated tests

```sh
python3 -m unittest discover -s tests -v
python3 tools/build_release.py
```

The 15 tests cover boundary topology, seam welding, holes, duplicate/non-manifold triangles, simplification, plane fitting, triangulation invariance, eigenvectors, degeneracy, datum priority, and right-handed flips. They use only Python's standard library. CI runs them on Python 3.10, 3.12, and 3.13 and builds the release ZIP.

## Native Fusion checks

These require an interactive Fusion session. Use synthetic geometry or models you can share.

- Load the renamed add-in with no other copy running; verify four commands appear and stop removes them.
- Extract boundaries of a tilted square, disk, annulus, and nonplanar patch. Check XYZ placement, holes, endpoint closure, Fix, and Construction.
- Check optional source deletion retains successful curves and leaves failed input meshes intact.
- Project into a new sketch and an existing sketch. Check all generated points lie on the target plane, existing geometry stays unchanged, and edge-on failures leave no partial result.
- Project to a sketch in a rotated/translated component instance.
- Fit a known tilted plane and constrained parallel/perpendicular/coincident cases.
- Change the reference of a parametric parallel/coincident plane and verify the output follows.
- Select a group within an unsplit mesh. Check extraction restores source body count, group count, visibility, and placement.
- Move a mesh by 3-2-1 datums. Verify vertex positions, unchanged area, primary priority, and no reflection.
- Align Ground-to-Parent and free component occurrences. Recompute and verify positions persist.
- Move a body proxy in a rotated component and check world-space coordinates.
- Exercise invalid and overlapping selections; confirm Undo returns the original state.

During local development the core cases above were tested on Fusion 2705.1.30/macOS, including copies of the working surface meshes. The standalone packaging smoke test and synthetic screenshots are recorded in [examples](EXAMPLES.md). Windows/UI installation still needs independent validation. Automated CI does not cover native API behavior.
