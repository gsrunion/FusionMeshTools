"""Orthographic mesh face-group perimeter projection into a native sketch."""
import math
import traceback
from collections import Counter
import adsk.core
import adsk.fusion
from .plane_from_group import mesh_data
from . import boundary_geometry as geo
from .mesh_boundary import fit_span

COMMAND_ID='GR_ProjectMeshFaceGroup'
PANELS=('ParaMeshModifyPanel','ParaMeshBaseModifyPanel','SketchCreatePanel')
_handlers=[]


def project_data(name,coordinates,indices,target,tolerance=.005,corner_angle=35.,use_splines=True):
    if not math.isfinite(tolerance) or tolerance<1e-5:
        raise ValueError('Use a fit tolerance of at least 0.0001 mm.')
    if not 1<=corner_angle<=179:raise ValueError('Corner angle must be between 1 and 179 degrees.')
    loops=geo.boundary_loops(coordinates,indices)
    if not loops:raise ValueError('The selected mesh has no open perimeter. Select a face group rather than a closed body.')
    if sum(map(len,loops))>10000:raise ValueError('More than 10,000 perimeter vertices. Reduce the mesh first.')
    selected_sketch=adsk.fusion.Sketch.cast(target)
    created=not bool(selected_sketch)
    if selected_sketch:
        context_sketch=selected_sketch
        sketch=selected_sketch.nativeObject or selected_sketch
    else:
        if not adsk.core.Plane.cast(target.geometry):raise ValueError('Select a sketch, construction plane, or planar face.')
        design=adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        sketch=design.rootComponent.sketches.add(target)
        sketch.name=name+' - Projected Face Group'
        context_sketch=sketch
    previous={curve.entityToken for curve in sketch.sketchCurves}
    deferred=sketch.isComputeDeferred
    counts=Counter()
    try:
        projected=[]
        for loop in loops:
            points=[]
            for xyz in loop:
                p=context_sketch.modelToSketchSpace(adsk.core.Point3D.create(*xyz))
                q=(p.x,p.y,0.)
                if not points or geo.distance(points[-1],q)>1e-7:points.append(q)
            if len(points)>1 and geo.distance(points[0],points[-1])<1e-7:points.pop()
            area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2
            if len(points)<3 or area<1e-12:
                raise ValueError('A boundary collapses edge-on on this sketch plane. Choose another projection plane.')
            projected.append(points)
        sketch.isComputeDeferred=True
        for points in projected:
            for span in geo.split_corners(points,corner_angle):
                result,_=fit_span(sketch,span,tolerance,use_splines)
                counts.update(result)
        sketch.isComputeDeferred=deferred
        added=[c for c in sketch.sketchCurves if c.entityToken not in previous]
        for curve in added:
            curve.isConstruction=True
            curve.isFixed=True
            curve.attributes.add('MeshToolCurve','generated','projection')
        sketch.attributes.add('MeshFaceGroupProjection','source_name',name)
        return sketch,len(projected),dict(counts),len(added)
    except Exception:
        sketch.isComputeDeferred=deferred
        if created:
            sketch.deleteMe()
        else:
            for curve in reversed(list(sketch.sketchCurves)):
                if curve.entityToken not in previous:curve.deleteMe()
        raise


class Execute(adsk.core.CommandEventHandler):
    def notify(self,args):
        try:
            inputs=args.command.commandInputs
            source=inputs.itemById('source').selection(0).entity
            target=inputs.itemById('target').selection(0).entity
            # Capture target token because temporary mesh separation can invalidate handles.
            token=target.entityToken
            name,coords,indices=mesh_data(source)
            app=adsk.core.Application.get();design=adsk.fusion.Design.cast(app.activeProduct)
            if not target.isValid:
                resolved=design.findEntityByToken(token)
                if not resolved:raise RuntimeError('Target sketch or plane is no longer available.')
                target=resolved[0]
            sketch,loops,counts,curves=project_data(name,coords,indices,target,inputs.itemById('tolerance').value,
                 math.degrees(inputs.itemById('corner').value),inputs.itemById('splines').value)
            app.userInterface.messageBox(f'Projected {loops} boundary loop(s) into {sketch.name}.\nCreated and fixed {curves} curves: '+', '.join(f'{n} {kind}' for kind,n in counts.items()),'Project Mesh Face Group')
        except Exception as error:
            args.executeFailed=True;args.executeFailedMessage=str(error)
            adsk.core.Application.get().log(traceback.format_exc())


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self,args):
        inputs=args.command.commandInputs
        source=inputs.addSelectionInput('source','Mesh face group','Select a face group, or a separated single-group mesh body')
        source.addSelectionFilter('FaceGroups');source.addSelectionFilter('MeshBodies');source.setSelectionLimits(1,1)
        target=inputs.addSelectionInput('target','Target sketch / plane','Select an existing sketch, or a planar face/construction plane to create a sketch')
        for filter_name in ('Sketches','ConstructionPlanes','PlanarFaces'):target.addSelectionFilter(filter_name)
        target.setSelectionLimits(1,1)
        inputs.addValueInput('tolerance','Fit tolerance','mm',adsk.core.ValueInput.createByString('0.05 mm'))
        inputs.addValueInput('corner','Corner turn angle','deg',adsk.core.ValueInput.createByString('35 deg'))
        inputs.addBoolValueInput('splines','Allow smooth splines',True,'',True)
        inputs.addTextBoxCommandInput('info','','Projects face-group perimeter loops and holes perpendicular to the target sketch plane. Creates fixed 2D sketch curves. Fits lines/arcs/splines; the mesh is retained. Existing sketch geometry is left unchanged. This is a snapshot boundary projection, not a live reference or a silhouette union of overlapping surfaces. Choose a plane/face to create a new sketch, or select a sketch in the browser.',6,True)
        handler=Execute();args.command.execute.add(handler);_handlers.append(handler)


def run():
    ui=adsk.core.Application.get().userInterface
    definition=ui.commandDefinitions.itemById(COMMAND_ID)
    if not definition:definition=ui.commandDefinitions.addButtonDefinition(COMMAND_ID,'Project Mesh Face Group','Project mesh face-group boundary curves onto a sketch plane.')
    handler=Created();definition.commandCreated.add(handler);_handlers.append(handler)
    for pid in PANELS:
        panel=ui.allToolbarPanels.itemById(pid)
        if panel and not panel.controls.itemById(COMMAND_ID):panel.controls.addCommand(definition).isPromoted=True


def stop():
    ui=adsk.core.Application.get().userInterface
    for pid in PANELS:
        panel=ui.allToolbarPanels.itemById(pid)
        control=panel.controls.itemById(COMMAND_ID) if panel else None
        if control:control.deleteMe()
    definition=ui.commandDefinitions.itemById(COMMAND_ID)
    if definition:definition.deleteMe()
    _handlers.clear()
