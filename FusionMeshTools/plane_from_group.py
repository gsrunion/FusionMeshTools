"""Fit construction planes to mesh face groups with optional reference constraints."""
import json
import math
import traceback
import adsk.core
import adsk.fusion
from . import plane_fit as fit

COMMAND_ID='GR_PlaneFromFaceGroup'
PANELS=('ParaMeshModifyPanel','ParaMeshBaseModifyPanel')
_handlers=[]


def mesh_data(entity):
    """Read selected group via temporary keep-original separation, then clean up."""
    group=adsk.fusion.FaceGroup.cast(entity)
    body=group.parentBody if group else adsk.fusion.MeshBody.cast(entity)
    if not body: raise ValueError('Select a mesh face group or a single-group mesh body.')
    occurrence=body.assemblyContext
    body=body.nativeObject or body
    group=(group.nativeObject or group) if group else None
    component=body.parentComponent
    name=body.name
    if not group and body.faceGroups.count>1:
        raise ValueError('This mesh contains multiple groups. Select the desired face group in the canvas.')
    if not group or body.faceGroups.count==1:
        mesh=body.displayMesh
        coords,indices=list(mesh.nodeCoordinatesAsDouble),list(mesh.nodeIndices)
    else:
        area,centroid=group.area,group.centroid
        previous={b.entityToken for b in component.meshBodies}
        visible=body.isLightBulbOn
        separate=component.features.meshSeparateFeatures
        settings=separate.createInput(adsk.core.ObjectCollection.createWithArray([group]))
        settings.isKeepBody=True; settings.isMultipleBodies=True
        feature=None
        try:
            feature=separate.add(settings)
            added=[b for b in component.meshBodies if b.entityToken not in previous]
            # MeshBody.area and FaceGroup.area can differ after separation due to
            # Fusion's mesh precision. Compare like-for-like group measurements.
            candidates=[b for b in added if b.faceGroups.count==1 and abs(b.faceGroups.item(0).area-area)<=max(area*1e-7,1e-10)
                        and b.faceGroups.item(0).centroid.distanceTo(centroid)<1e-6]
            if len(candidates)!=1: raise RuntimeError('Cannot uniquely isolate the selected face group.')
            mesh=candidates[0].displayMesh
            coords,indices=list(mesh.nodeCoordinatesAsDouble),list(mesh.nodeIndices)
        finally:
            if feature:
                if not feature.deleteMe(): raise RuntimeError('Cannot clean up temporary separation.')
            else:
                for b in list(component.meshBodies):
                    if b.entityToken not in previous and not b.deleteMe():
                        raise RuntimeError('Cannot clean up temporary mesh.')
            body.isLightBulbOn=visible
    if occurrence:
        transform=occurrence.transform2
        for i in range(0,len(coords),3):
            p=adsk.core.Point3D.create(*coords[i:i+3]); p.transformBy(transform)
            coords[i:i+3]=[p.x,p.y,p.z]
    return name,coords,indices


def reference_plane(entity):
    geometry=entity.geometry
    plane=adsk.core.Plane.cast(geometry)
    if not plane: raise ValueError('Reference must be a planar face or construction plane.')
    return list(plane.origin.asArray()),list(plane.normal.asArray())


def create_plane(root,name,coordinates,indices,mode='Best fit',reference=None):
    ref=reference_plane(reference) if reference else None
    origin,normal,rms,maximum=fit.fit(coordinates,indices,mode,ref)
    planes=root.constructionPlanes
    settings=planes.createInput()
    helper=None
    try:
        if mode in ('Parallel','Coincident'):
            offset=fit.dot(fit.sub(origin,ref[0]),fit.unit(ref[1])) if mode=='Parallel' else 0.
            if not settings.setByOffset(reference,adsk.core.ValueInput.createByReal(offset)):
                raise RuntimeError('Cannot define reference offset plane.')
        elif mode=='Perpendicular':
            helper=root.sketches.add(reference)
            helper.name=name+' - Plane Fit Support'
            direction=fit.unit(fit.cross(normal,fit.unit(ref[1])))
            # Project centroid onto reference; line intersection defines the perpendicular plane.
            height=fit.dot(fit.sub(origin,ref[0]),fit.unit(ref[1]))
            base=[origin[i]-height*fit.unit(ref[1])[i] for i in range(3)]
            a=helper.modelToSketchSpace(adsk.core.Point3D.create(*base))
            b=helper.modelToSketchSpace(adsk.core.Point3D.create(*[base[i]+direction[i] for i in range(3)]))
            line=helper.sketchCurves.sketchLines.addByTwoPoints(a,b)
            line.isConstruction=True; line.isFixed=True
            helper.attributes.add('MeshToolCurve','support','plane')
            if not settings.setByAngle(line,adsk.core.ValueInput.createByString('90 deg'),reference):
                raise RuntimeError('Cannot define perpendicular plane.')
        else:
            helper=root.sketches.add(root.xYConstructionPlane)
            helper.name=name+' - Plane Fit Support'
            axis=min(([1,0,0],[0,1,0],[0,0,1]),key=lambda v:abs(fit.dot(v,normal)))
            u=fit.unit(fit.cross(normal,axis)); v=fit.cross(normal,u)
            size=max(.1,math.sqrt(sum((x-origin[i%3])**2 for i,x in enumerate(coordinates))/max(len(coordinates)//3,1)))
            points=[]
            for p in (origin,[origin[i]+size*u[i] for i in range(3)],[origin[i]+size*v[i] for i in range(3)]):
                sp=helper.sketchPoints.add(helper.modelToSketchSpace(adsk.core.Point3D.create(*p))); sp.isFixed=True; points.append(sp)
            if not settings.setByThreePoints(*points): raise RuntimeError('Cannot define fitted plane.')
        plane=planes.add(settings)
        plane.name=name+' - '+mode+' Plane'
        # Verify actual creation against the computed solution before reporting success.
        actual=plane.geometry
        if abs(fit.dot(actual.normal.asArray(),normal))<1-1e-7 or abs(fit.dot(fit.sub(actual.origin.asArray(),origin),normal))>1e-6:
            plane.deleteMe()
            raise RuntimeError('Fusion created a plane inconsistent with the fitted solution.')
        plane.attributes.add('PlaneFromFaceGroup','fit',json.dumps({'mode':mode,'rms_cm':rms,'max_cm':maximum}))
        if helper: helper.isLightBulbOn=False
        return plane,rms,maximum
    except Exception:
        if helper and helper.isValid: helper.deleteMe()
        raise


class Execute(adsk.core.CommandEventHandler):
    def notify(self,args):
        try:
            app=adsk.core.Application.get(); inputs=args.command.commandInputs
            source=inputs.itemById('source').selection(0).entity
            mode=inputs.itemById('mode').selectedItem.name
            ref_input=inputs.itemById('reference')
            reference=ref_input.selection(0).entity if ref_input.selectionCount and mode!='Best fit' else None
            if mode!='Best fit' and reference is None: raise ValueError('Select reference planar geometry for this constraint.')
            name,coords,indices=mesh_data(source)
            design=adsk.fusion.Design.cast(app.activeProduct)
            plane,rms,maximum=create_plane(design.rootComponent,name,coords,indices,mode,reference)
            app.userInterface.messageBox(f'{plane.name}\nArea-weighted RMS: {rms*10:.6g} mm\nMaximum vertex deviation: {maximum*10:.6g} mm','Plane from Face Group')
        except Exception as error:
            args.executeFailed=True; args.executeFailedMessage=str(error)
            adsk.core.Application.get().log(traceback.format_exc())


class Created(adsk.core.CommandCreatedEventHandler):
    def notify(self,args):
        inputs=args.command.commandInputs
        source=inputs.addSelectionInput('source','Mesh face group','Select a mesh face group, or a separated single-group mesh body')
        source.addSelectionFilter('FaceGroups'); source.addSelectionFilter('MeshBodies'); source.setSelectionLimits(1,1)
        mode=inputs.addDropDownCommandInput('mode','Constraint',adsk.core.DropDownStyles.TextListDropDownStyle)
        for name in ('Best fit','Parallel','Perpendicular','Coincident'): mode.listItems.add(name,name=='Best fit')
        reference=inputs.addSelectionInput('reference','Reference plane / face','Select optional construction plane or planar BRep face')
        reference.addSelectionFilter('ConstructionPlanes'); reference.addSelectionFilter('PlanarFaces'); reference.setSelectionLimits(0,1)
        inputs.addTextBoxCommandInput('info','','Area-weighted statistical plane fit. Parallel keeps the best-fit offset; Perpendicular finds the best-fit orientation at 90 degrees to the reference; Coincident uses the reference plane exactly. Reference constraints are native Fusion features. Mesh fitting is a snapshot; it does not refit after mesh edits. Output is in the root component. Hidden support sketches define free/perpendicular planes.',6,True)
        handler=Execute(); args.command.execute.add(handler); _handlers.append(handler)


def run():
    ui=adsk.core.Application.get().userInterface
    definition=ui.commandDefinitions.itemById(COMMAND_ID)
    if not definition: definition=ui.commandDefinitions.addButtonDefinition(COMMAND_ID,'Plane from Face Group','Area-weighted best-fit construction plane with reference constraints.')
    handler=Created(); definition.commandCreated.add(handler); _handlers.append(handler)
    for pid in PANELS:
        panel=ui.allToolbarPanels.itemById(pid)
        if panel and not panel.controls.itemById(COMMAND_ID): panel.controls.addCommand(definition).isPromoted=True


def stop():
    ui=adsk.core.Application.get().userInterface
    for pid in PANELS:
        panel=ui.allToolbarPanels.itemById(pid)
        control=panel.controls.itemById(COMMAND_ID) if panel else None
        if control: control.deleteMe()
    definition=ui.commandDefinitions.itemById(COMMAND_ID)
    if definition: definition.deleteMe()
    _handlers.clear()
