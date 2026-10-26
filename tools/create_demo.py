"""Run run(context) inside Fusion to regenerate synthetic documentation images."""
import math
from pathlib import Path
import sys


def run(context):
    import adsk.core
    import adsk.fusion

    root = Path(__file__).resolve().parents[1]
    added_path = str(root) not in sys.path
    if added_path:
        sys.path.insert(0, str(root))
    from FusionMeshTools.mesh_boundary import create_boundary
    from FusionMeshTools.project_mesh_group import project_data
    from FusionMeshTools.plane_from_group import create_plane

    app = adsk.core.Application.get()
    original = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    images = root / 'docs' / 'images'
    images.mkdir(exist_ok=True)
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        component = design.rootComponent
        vertices, triangles = [], []
        count = 96
        for radius in (3., 1.25):
            for i in range(count):
                angle = i * 2 * math.pi / count
                x, y = radius * math.cos(angle), radius * math.sin(angle)
                vertices.append((x, y, 1.5 + .25*x))
        for i in range(count):
            j = (i+1) % count
            triangles.extend((i, j, count+j, i, count+j, count+i))
        coordinates = [x for p in vertices for x in p]
        body = component.meshBodies.addByTriangleMeshData(coordinates, triangles, [], [])
        body.name = 'Synthetic tilted annulus'
        boundary, loops, _, _ = create_boundary(body)
        boundary.arePointsShown = False
        assert loops == 2
        assert all(c.isFixed and c.isConstruction for c in boundary.sketchCurves)
        projected, loops, _, _ = project_data('Synthetic annulus', coordinates, triangles, component.xYConstructionPlane)
        projected.arePointsShown = False
        assert loops == 2
        assert all(c.isFixed and c.isConstruction for c in projected.sketchCurves)
        plane, rms, maximum = create_plane(component, 'Synthetic annulus', coordinates, triangles)
        assert maximum < 1e-5
        plane.isLightBulbOn = False
        projected.isLightBulbOn = False

        def view(filename, eye, target, up):
            viewport = app.activeViewport
            camera = viewport.camera
            camera.isPerspective = False
            camera.eye = adsk.core.Point3D.create(*eye)
            camera.target = adsk.core.Point3D.create(*target)
            camera.upVector = adsk.core.Vector3D.create(*up)
            camera.isSmoothTransition = False
            camera.isFitView = True
            viewport.camera = camera
            camera = viewport.camera
            ok, width, height = camera.getExtents()
            if ok:
                camera.isFitView = False
                camera.setExtents(width * 1.35, height * 1.35)
                viewport.camera = camera
            viewport.refresh()
            adsk.doEvents()
            if not viewport.saveAsImageFile(str(images / filename), 1400, 900):
                raise RuntimeError('Cannot save documentation image.')

        view('mesh-and-boundary.png', (9,-12,10), (0,0,1.5), (0,0,1))
        body.isLightBulbOn = False
        view('boundary-curves.png', (9,-12,10), (0,0,1.5), (0,0,1))
        boundary.isLightBulbOn = False
        projected.isLightBulbOn = True
        view('projected-curves.png', (0,0,15), (0,0,0), (0,1,0))
        print('Standalone package native smoke test passed: two perimeter loops, fixed construction output, planar fit.')
        print('Generated three documentation images from a synthetic annulus.')
    finally:
        document.close(False)
        if original:
            original.activate()
        if added_path:
            sys.path.remove(str(root))
