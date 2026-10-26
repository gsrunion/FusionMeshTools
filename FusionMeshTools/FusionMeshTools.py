"""FusionMeshTools: experimental mesh reconstruction helpers for Autodesk Fusion."""
import traceback
import adsk.core
from . import mesh_boundary
from . import plane_from_group
from . import datum_alignment
from . import project_mesh_group


def run(context):
    try:
        mesh_boundary.run()
        plane_from_group.run()
        datum_alignment.run()
        project_mesh_group.run()
    except Exception:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


def stop(context):
    project_mesh_group.stop()
    datum_alignment.stop()
    plane_from_group.stop()
    mesh_boundary.stop()
