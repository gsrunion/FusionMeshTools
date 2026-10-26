# FusionMeshTools

Experimental mesh reconstruction helpers for **Autodesk Fusion**. Extract usable sketch curves, fit datum planes, project mesh face groups, and align geometry to a 3-2-1 datum frame.

**Status: experimental.** Face-group extraction depends on Autodesk's preview MeshSeparate API. Autodesk advises against distributing programs based on preview APIs; this repository shares experimental source for evaluation, not a stable supported product. Future Fusion releases may require changes. This project is independent of Autodesk.

## Tools

| Command | What it does |
| --- | --- |
| **Mesh Boundary to Curves** | Fits lines, arcs, and 3D splines to the open perimeters and holes of mesh surface bodies. |
| **Project Mesh Face Group** | Projects a face-group perimeter into an existing sketch, or onto a plane/planar face in a new sketch. |
| **Plane from Face Group** | Fits an area-weighted least-squares plane, optionally parallel, perpendicular, or coincident with reference geometry. |
| **3-2-1 Datum Alignment** | Rigidly aligns selected bodies or components using primary, secondary, and tertiary datum priority. |

Generated sketch curves are **fixed construction geometry**. Existing unrelated curves in a projection target sketch keep their properties. Construction curves do not form sketch profiles; toggle Construction off for curves you want to use as profile geometry.

## Install

1. Download the installable `FusionMeshTools-v0.8.1.zip` from the repository's Releases page when a release is available. For a source checkout, use the inner `FusionMeshTools` folder containing `FusionMeshTools.py` and `FusionMeshTools.manifest`.
2. Extract the ZIP to a permanent location. Keep the `FusionMeshTools` folder intact.
3. In Fusion, open **Scripts and Add-Ins**, add an existing add-in, and choose that folder.
4. Select **FusionMeshTools** and run it. Enable **Run on Startup** if desired.
5. Find the commands under **Design → Mesh → Modify**. Datum Alignment is also available under Solid → Modify; projection is also registered in the sketch Create panel when available. Registered commands can be found with Fusion's command search.

Alternatively, copy the add-in folder into Fusion's user AddIns directory:

| OS | Directory |
| --- | --- |
| macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |
| Windows | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` |

Restart Fusion if a copied add-in is not listed. No `pip install` or external Python environment is needed inside Fusion.

**Upgrading from the earlier local SplitFaceGroups add-in:** stop it and disable its startup loading before running FusionMeshTools. They use the same add-in ID and command IDs; run only one copy. Your earlier sketches and planes remain in the design.

## Example workflow

1. Import a mesh and generate face groups using Fusion's native mesh tools.
2. Fit a plane to a likely planar group. Inspect its reported RMS and maximum deviation before accepting it as a datum.
3. Fit the secondary and tertiary datum planes, using reference constraints when useful.
4. Use **3-2-1 Datum Alignment** to position the mesh component relative to the origin.
5. Use **Project Mesh Face Group** to obtain planar construction curves, or separate surface patches with Fusion's native Separate tool and use **Mesh Boundary to Curves** for 3D perimeter curves.

These tools create reference geometry. They do not automatically rebuild, stitch, or thicken BRep surfaces.

See [command details and limitations](docs/TOOLS.md), [screenshots](docs/EXAMPLES.md), and [testing](docs/TESTING.md).

## Compatibility and behavior

- Developed and tested on macOS with Fusion build **2705.1.30**. Windows is declared in the manifest but has not been tested.
- Use a Fusion build exposing `meshSeparateFeatures` for selections within an unsplit multi-group mesh. Already separated single-group bodies bypass that API.
- Fitted curves and mesh fits are snapshots, not associative mesh references. In parametric designs, native plane-to-reference constraints remain associative.
- Commands modify the active design. Use Undo to reverse them. Mesh deletion is optional and defaults to off.
- A native body edit affects all instances of its component. Select component occurrences for independent instance alignment.
- Algorithm tests run outside Fusion; command/UI tests require Fusion. CI does not validate the native CAD API.

## Development

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 tools/build_release.py
```

The release builder creates `dist/FusionMeshTools-v0.8.1.zip` and a SHA-256 checksum. It excludes tests, caches, editor settings, private models, and obsolete commands.

See [contribution guidelines](CONTRIBUTING.md) and [the local publishing checklist](docs/PUBLISHING.md).

## License

[MIT](LICENSE). Copyright © 2026 G. Runion.
