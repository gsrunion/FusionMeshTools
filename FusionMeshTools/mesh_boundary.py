"""Create native 3D sketch curves from open mesh body perimeters."""
import math
import traceback
from collections import Counter
import adsk.core
import adsk.fusion
from . import boundary_geometry as geo

COMMAND_ID = 'GR_MeshBoundaryToCurves'
PANEL_IDS = ('ParaMeshModifyPanel', 'ParaMeshBaseModifyPanel')
_handlers = []


def point(p):
    return adsk.core.Point3D.create(*p)


def stroke(curve, tolerance):
    evaluator = curve.geometry.evaluator
    ok, start, end = evaluator.getParameterExtents()
    if not ok:
        raise RuntimeError('Cannot evaluate fitted curve.')
    ok, vertices = evaluator.getStrokes(start, end, tolerance / 8)
    if not ok:
        raise RuntimeError('Cannot sample fitted curve.')
    return [(p.x, p.y, p.z) for p in vertices]


def fit_span(sketch, points, tolerance, use_splines, depth=0):
    """Try a line, a circular arc, then a reduced fitted spline; otherwise polylines."""
    curves = sketch.sketchCurves
    reduced = geo.simplify(points, tolerance / 2)
    if len(reduced) == 2:
        curves.sketchLines.addByTwoPoints(point(points[0]), point(points[-1]))
        return Counter({'line': 1}), max(geo.segment_distance(p, points[0], points[-1]) for p in points)
    # An arc through three points is only retained when the sampled whole span fits.
    if len(points) >= 4:
        candidate = None
        try:
            candidate = curves.sketchArcs.addByThreePoints(point(points[0]), point(points[len(points)//2]), point(points[-1]))
            error = geo.sampled_deviation(points, stroke(candidate, tolerance))
            if error <= tolerance * .8:
                return Counter({'arc': 1}), error
        except RuntimeError:
            pass
        if candidate:
            candidate.deleteMe()
    if use_splines and 3 <= len(reduced) <= 100:
        candidate = None
        try:
            collection = adsk.core.ObjectCollection.create()
            for p in reduced:
                collection.add(point(p))
            candidate = curves.sketchFittedSplines.add(collection)
            error = geo.sampled_deviation(points, stroke(candidate, tolerance))
            if error <= tolerance * .8:
                return Counter({'spline': 1}), error
        except RuntimeError:
            pass
        if candidate:
            candidate.deleteMe()
    # Composite boundaries often need several primitives rather than one long spline.
    if len(points) > 6 and depth < 12:
        middle = len(points)//2
        left, error_left = fit_span(sketch, points[:middle+1], tolerance, use_splines, depth+1)
        right, error_right = fit_span(sketch, points[middle:], tolerance, use_splines, depth+1)
        return left + right, max(error_left, error_right)
    for a, b in zip(reduced, reduced[1:]):
        curves.sketchLines.addByTwoPoints(point(a), point(b))
    return Counter({'polyline segments': len(reduced)-1}), tolerance / 2


def freeze_sketch(sketch):
    for curve in sketch.sketchCurves:
        curve.isConstruction = True
        curve.isFixed = True
        curve.attributes.add('MeshToolCurve', 'generated', 'boundary')
    sketch.attributes.add('MeshBoundaryToCurves', 'frozen', 'true')


def create_boundary(body, tolerance=.005, corner_angle=35., use_splines=True):
    if not math.isfinite(tolerance) or tolerance < 1e-5:
        raise ValueError('Use a fit tolerance of at least 0.0001 mm.')
    body = body.nativeObject or body
    mesh = body.displayMesh
    loops = geo.boundary_loops(list(mesh.nodeCoordinatesAsDouble), list(mesh.nodeIndices))
    if not loops:
        raise ValueError('No open boundary. Split face groups into surface meshes first.')
    if sum(len(loop) for loop in loops) > 10000:
        raise ValueError('More than 10,000 boundary vertices. Reduce the mesh before extracting curves.')
    component = body.parentComponent
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = body.name + ' - Boundary Curves'
    counts, errors = Counter(), []
    try:
        sketch.isComputeDeferred = True
        for loop in loops:
            local = []
            for p in loop:
                q = sketch.modelToSketchSpace(point(p))
                local.append((q.x, q.y, q.z))
            for span in geo.split_corners(local, corner_angle):
                span_counts, error = fit_span(sketch, span, tolerance, use_splines)
                counts.update(span_counts)
                errors.append(error)
        sketch.isComputeDeferred = False
        sketch.attributes.add('MeshBoundaryToCurves', 'source', body.entityToken)
        sketch.attributes.add('MeshBoundaryToCurves', 'tolerance_cm', str(tolerance))
        freeze_sketch(sketch)
        return sketch, len(loops), dict(counts), max(errors, default=0.)
    except Exception:
        sketch.isComputeDeferred = False
        sketch.deleteMe()
        raise


class Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        try:
            inputs = args.command.commandInputs
            selection = inputs.itemById('meshes')
            bodies = []
            for i in range(selection.selectionCount):
                selected = selection.selection(i).entity
                native = selected.nativeObject or selected
                if not any(native == previous for previous in bodies):
                    bodies.append(native)
            tolerance = inputs.itemById('tolerance').value
            angle = math.degrees(inputs.itemById('corner').value)
            if not 1 <= angle <= 179:
                raise ValueError('Corner angle must be between 1 and 179 degrees.')
            report, successes = [], 0
            for body in bodies:
                name = body.name
                try:
                    sketch, loops, counts, error = create_boundary(body, tolerance, angle, inputs.itemById('splines').value)
                    successes += 1
                    detail = f'{name}: {loops} loop(s); ' + ', '.join(f'{n} {k}' for k, n in counts.items())
                    if inputs.itemById('delete_mesh').value:
                        try:
                            if not body.deleteMe():
                                raise RuntimeError('Fusion declined to delete the mesh.')
                            detail += '; source mesh deleted'
                        except Exception as error:
                            detail += f'; curves kept, mesh deletion failed: {error}'
                            app.log(traceback.format_exc())
                    report.append(detail)
                except Exception as error:
                    report.append(f'{name}: FAILED — {error}')
                    app.log(traceback.format_exc())
            summary = f'Created {successes} boundary sketch(es).\n\n' + '\n'.join(report)
            app.log('[Mesh Boundary to Curves]\n' + summary)
            if not successes:
                args.executeFailed = True
                args.executeFailedMessage = summary
            else:
                app.userInterface.messageBox(summary, 'Mesh Boundary to Curves')
        except Exception as error:
            args.executeFailed = True
            args.executeFailedMessage = str(error)
            app.log(traceback.format_exc())


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        inputs = args.command.commandInputs
        selection = inputs.addSelectionInput('meshes', 'Mesh surfaces', 'Select one or more open mesh bodies')
        selection.addSelectionFilter('MeshBodies')
        selection.setSelectionLimits(1, 0)
        inputs.addValueInput('tolerance', 'Fit tolerance', 'mm', adsk.core.ValueInput.createByString('0.05 mm'))
        inputs.addValueInput('corner', 'Corner turn angle', 'deg', adsk.core.ValueInput.createByString('35 deg'))
        inputs.addBoolValueInput('splines', 'Allow smooth splines', True, '', True)
        inputs.addBoolValueInput('delete_mesh', 'Delete source mesh after extraction', True, '', False)
        inputs.addTextBoxCommandInput('info', '', 'Extracts open perimeters including holes. Applies the Fix constraint to all generated curves. Delete source removes the entire selected mesh surface body only after successful extraction. Shared component instances are affected together. Curves are snapshots.', 6, True)
        handler = Execute()
        args.command.execute.add(handler)
        _handlers.append(handler)


def run():
    ui = adsk.core.Application.get().userInterface
    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if not definition:
        definition = ui.commandDefinitions.addButtonDefinition(COMMAND_ID, 'Mesh Boundary to Curves', 'Fit native sketch lines, arcs and 3D splines to open mesh boundaries.')
    handler = Created()
    definition.commandCreated.add(handler)
    _handlers.append(handler)
    for panel_id in PANEL_IDS:
        panel = ui.allToolbarPanels.itemById(panel_id)
        if panel and not panel.controls.itemById(COMMAND_ID):
            panel.controls.addCommand(definition).isPromoted = True


def stop():
    ui = adsk.core.Application.get().userInterface
    for panel_id in PANEL_IDS:
        panel = ui.allToolbarPanels.itemById(panel_id)
        control = panel.controls.itemById(COMMAND_ID) if panel else None
        if control:
            control.deleteMe()
    definition = ui.commandDefinitions.itemById(COMMAND_ID)
    if definition:
        definition.deleteMe()
    _handlers.clear()
