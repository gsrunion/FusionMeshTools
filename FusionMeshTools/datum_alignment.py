"""Native Fusion command for rigid 3-2-1 datum alignment."""
import traceback
import adsk.core
import adsk.fusion
from . import datum_math as math3
from .plane_from_group import reference_plane

COMMAND_ID='GR_321DatumAlignment'
PANELS=('ParaMeshModifyPanel','ParaMeshBaseModifyPanel','SolidModifyPanel')
_handlers=[]


def matrix(values):
    result=adsk.core.Matrix3D.create()
    if not result.setWithArray(values):raise RuntimeError('Invalid alignment matrix.')
    return result


def move_targets(design,targets,values):
    """Preflight all targets, then apply one world-space rigid transform."""
    occurrences=[];bodies=[]
    for target in targets:
        occurrence=adsk.fusion.Occurrence.cast(target)
        if occurrence:
            if occurrence.assemblyContext:
                raise ValueError('Select the top-level component occurrence, or select its bodies.')
            if occurrence.isGrounded:
                raise ValueError(f'{occurrence.name} is grounded. Unground it before alignment.')
            if occurrence.isGroundToParent and not occurrence.isVaildForEditInitialPosition:
                raise ValueError(f'{occurrence.name} cannot edit its initial position. Remove Ground to Parent first.')
            if not any(occurrence==old for old in occurrences):occurrences.append(occurrence)
        elif adsk.fusion.MeshBody.cast(target) or adsk.fusion.BRepBody.cast(target):
            native=target.nativeObject or target
            if any(native==(old.nativeObject or old) for old in bodies):
                raise ValueError('A body was selected more than once through different instances. Select the component instead.')
            if not target.assemblyContext and native.parentComponent!=design.rootComponent:
                raise ValueError('Select component bodies in assembly context from the root browser.')
            bodies.append(target)
        else:raise ValueError('Select components, mesh bodies, or BRep bodies to move.')
    if not occurrences and not bodies:raise ValueError('Select geometry to align.')
    for body in bodies:
        context=body.assemblyContext
        if context and any(context==occ or context.fullPathName.startswith(occ.fullPathName+'+') for occ in occurrences):
            raise ValueError('Select either a component or its bodies, not both.')
    transform=matrix(values)
    expected_positions=[]
    pending_position=False
    for occurrence in occurrences:
        expected=math3.multiply(values,list(occurrence.transform2.asArray()))
        if occurrence.isGroundToParent:
            marker=design.timeline.markerPosition
            try:
                if design.designType==adsk.fusion.DesignTypes.ParametricDesignType:
                    occurrence.timelineObject.rollTo(False)
                occurrence.initialTransform=matrix(expected)
            finally:
                if design.designType==adsk.fusion.DesignTypes.ParametricDesignType:
                    design.timeline.markerPosition=marker
        else:
            occurrence.transform2=matrix(expected)
            pending_position=True
        expected_positions.append((occurrence,expected))
        actual=list(occurrence.transform2.asArray())
        if max(abs(a-b) for a,b in zip(expected,actual))>1e-6:
            raise RuntimeError(f'{occurrence.name} could not be positioned. Check assembly joints or grounding.')
    for body in bodies:
        native=body.nativeObject or body
        context=body.assemblyContext
        local=transform
        if context:
            frame=context.transform2
            inverse=frame.copy();inverse.invert()
            local=matrix(math3.multiply(list(inverse.asArray()),math3.multiply(values,list(frame.asArray()))))
        moves=native.parentComponent.features.moveFeatures
        settings=moves.createInput2(adsk.core.ObjectCollection.createWithArray([native]))
        if not settings.defineAsFreeMove(local):raise RuntimeError('Cannot define body alignment.')
        feature=moves.add(settings)
        if feature:
            feature.name='3-2-1 Datum Alignment'
            if feature.healthState==adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState:
                raise RuntimeError(feature.errorOrWarningMessage)
    if pending_position and design.designType==adsk.fusion.DesignTypes.ParametricDesignType and design.snapshots.hasPendingSnapshot:
        design.snapshots.add()
    for occurrence,expected in expected_positions:
        if max(abs(a-b) for a,b in zip(expected,occurrence.transform2.asArray()))>1e-6:
            raise RuntimeError(f'{occurrence.name} did not retain the aligned position.')
    return len(occurrences),len(bodies)


class Execute(adsk.core.CommandEventHandler):
    def notify(self,args):
        try:
            app=adsk.core.Application.get();inputs=args.command.commandInputs
            entities=[inputs.itemById(key).selection(0).entity for key in ('primary','secondary','tertiary')]
            if any(entities[i]==entities[j] for i,j in ((0,1),(0,2),(1,2))):
                raise ValueError('Select three different datum planes.')
            planes=[reference_plane(e) for e in entities]
            values,origin,departures=math3.alignment(planes,inputs.itemById('flip_primary').value,inputs.itemById('flip_secondary').value)
            selection=inputs.itemById('targets')
            targets=[selection.selection(i).entity for i in range(selection.selectionCount)]
            design=adsk.fusion.Design.cast(app.activeProduct)
            components,bodies=move_targets(design,targets,values)
            app.userInterface.messageBox(f'Aligned {components} component(s), {bodies} body/bodies.\nPrimary → XY; secondary direction → XZ; tertiary position → YZ.\nOriginal datum intersection (mm): '+', '.join(f'{v*10:.5g}' for v in origin)+'\nDeparture from square, P/S, P/T, S/T (deg): '+', '.join(f'{v:.5g}' for v in departures),'3-2-1 Datum Alignment')
        except Exception as error:
            args.executeFailed=True;args.executeFailedMessage=str(error)
            adsk.core.Application.get().log(traceback.format_exc())


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self,args):
        inputs=args.command.commandInputs
        for key,label in (('primary','1. Primary → XY'),('secondary','2. Secondary → XZ'),('tertiary','3. Tertiary → YZ')):
            selection=inputs.addSelectionInput(key,label,'Select the datum construction plane or planar face')
            selection.addSelectionFilter('ConstructionPlanes');selection.addSelectionFilter('PlanarFaces');selection.setSelectionLimits(1,1)
        inputs.addBoolValueInput('flip_primary','Reverse primary Z direction',True,'',False)
        inputs.addBoolValueInput('flip_secondary','Reverse secondary Y direction',True,'',False)
        selection=inputs.addSelectionInput('targets','Geometry to move','Select top-level component occurrences or mesh/BRep bodies')
        for filter_name in ('Occurrences','MeshBodies','SolidBodies','SurfaceBodies'):selection.addSelectionFilter(filter_name)
        selection.setSelectionLimits(1,0)
        inputs.addTextBoxCommandInput('info','','Primary fixes Z and tilt; secondary fixes rotation about Z and Y position; tertiary fixes X position. Priority is preserved if planes are not square. One rigid transform; no scaling or mirroring. X follows the right-hand rule. Components grounded to parent move by editing their initial position. Body moves affect shared component instances. Root-level reference planes and sketches do not move unless owned by a selected component. Undo reverses the alignment.',7,True)
        handler=Execute();args.command.execute.add(handler);_handlers.append(handler)


def run():
    ui=adsk.core.Application.get().userInterface
    definition=ui.commandDefinitions.itemById(COMMAND_ID)
    if not definition:definition=ui.commandDefinitions.addButtonDefinition(COMMAND_ID,'3-2-1 Datum Alignment','Rigid plane datum alignment with primary, secondary and tertiary priority.')
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
