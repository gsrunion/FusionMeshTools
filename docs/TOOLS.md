# Command details

## Mesh Boundary to Curves

Select one or more open mesh surface bodies. Default fit tolerance is **0.05 mm** and corner turn angle is **35°**. A lower corner angle preserves more changes of direction as separate spans. Smooth splines are optional.

The command welds seam vertices within 0.000001 mm, counts triangle-edge incidence, traces all perimeter loops, and splits them at sharp corners. Each span tries a line, a circular arc, and a reduced fitted spline. Failed fits subdivide before falling back to simplified lines. Smooth-curve checks use bidirectional vertex/midpoint sampling against curve strokes: the tolerance is not a certified continuous Hausdorff bound or a guarantee of recovering original CAD dimensions.

Each body produces a sketch in its owning component. All new curves are fixed construction geometry. Closed meshes have no open perimeter; separate groups into mesh surfaces first with Fusion's native Separate tool. Duplicate triangles, non-manifold edges, and touching/branching boundaries are rejected. A body is limited to 10,000 perimeter vertices. Separate bodies can create duplicate coincident boundaries in different sketches.

**Delete source mesh after extraction** defaults to off. It removes the entire selected mesh surface body after successful extraction. Failed extractions retain their mesh; deletion failures keep the successful sketch and report the error.

## Project Mesh Face Group

Select a face group, or a separated single-group mesh body. Select an existing target sketch, or a construction plane/planar BRep face for a new sketch.

The perimeter is converted into target sketch coordinates and its Z coordinate is dropped, producing orthographic projection perpendicular to the sketch plane. Outer boundaries and holes are included. All newly added curves are fixed construction geometry. Existing target curves keep their properties.

This projects the perimeter, not every triangle edge or the silhouette union of overlapping patches. Folded/nonplanar boundaries may overlap after projection. Edge-on collapsed loops are rejected. Projection into a shared sketch appears in every component instance.

## Plane from Face Group

Select a face group or separated single-group mesh body, then a constraint:

| Mode | Definition |
| --- | --- |
| Best fit | Orthogonal least-squares plane through the triangle-area centroid. |
| Parallel | Reference normal, with the least-squares offset through the mesh area centroid. |
| Perpendicular | Best-fit normal constrained to 90° from the reference, through the area centroid. |
| Coincident | Exactly the reference plane, with mesh deviation measured against it. |

The fit integrates triangle-area moments rather than equally weighting STL vertices. Refining triangulation without changing the underlying surface does not change the statistical fit. Output reports area-weighted RMS distance and maximum vertex distance in millimeters. Curved groups can still yield a plane: inspect its deviations.

Outputs are root-component construction planes. Free fits use a hidden support sketch with fixed points. Perpendicular planes use a hidden fixed construction line on the reference plus a native 90° plane feature. Parallel/coincident planes use native offset features. Reference relationships remain associative in parametric designs; the mesh fit itself does not update. Direct-mode results are snapshots.

For an unsplit multi-group mesh, the tool temporarily separates the selected group with Keep Body, reads its triangles, and removes the temporary result. Source geometry and visibility are retained. This depends on the preview MeshSeparate API. Face-group area/centroid matching identifies the extracted patch; ambiguous matches are rejected.

## 3-2-1 Datum Alignment

Select primary, secondary, and tertiary construction planes or planar BRep faces, then the top-level component occurrences or mesh/BRep bodies to move.

1. Primary defines Z and tilt and maps to XY.
2. The component of the secondary normal perpendicular to Z defines Y and remaining rotation about Z.
3. The original three-plane intersection maps to the origin, setting the last translation.

Primary and secondary direction flips are available. X follows the right-hand rule. No scaling or mirroring is applied. Nonorthogonal input planes retain primary priority: angular mismatch is reported rather than averaged away. Degenerate/unstable datum sets are rejected.

Top-level components move with their contents. Select bodies to move individual mesh/BRep geometry; body edits affect all component instances. Do not select both a component and its bodies. Nested occurrences must be moved through a top-level component or by body selection. Root-level reference planes/sketches stay where they were unless part of a selected component.

Pinned occurrences require ungrounding. Ground-to-parent occurrences move by editing their initial insertion position and retain Ground to Parent; this earlier timeline change can affect downstream features. Free occurrences use their placement plus Capture Position. Joints can prevent alignment; final positions are verified. Alignment is a snapshot.
