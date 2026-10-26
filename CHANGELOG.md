# Changelog

## 0.8.1 — 2026-10-26

First standalone experimental source package, preserving the locally developed tools:

- Mesh Boundary to Curves, with fixed construction output and optional mesh deletion.
- Project Mesh Face Group into a sketch or onto a plane/planar face.
- Area-weighted Plane from Face Group with parallel, perpendicular, and coincident reference modes.
- Priority 3-2-1 Datum Alignment for mesh/BRep bodies and component occurrences.

The standalone add-in is named FusionMeshTools. Removed obsolete conversion code from this package. Startup loading is opt-in. Algorithm tests run outside Fusion; native API operations require Fusion.
