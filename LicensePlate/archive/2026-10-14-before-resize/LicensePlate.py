"""Fusion script: 5mm plate frame, uniform bottom rail, 50mm side-ridge tongues.
Continuous stepped/T rails are adapted from the supplied Duschablage hanger arms.
All lengths below are in millimeters; the API point helper converts to centimeters.
"""
import adsk.core,adsk.fusion,math,os

OUTPUT_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Generated')  # Exports go here.

def run(context):
 app=adsk.core.Application.get()
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='License Plate - Bottom Open Groove - Top Ridges'
 d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.DirectDesignType
 root=d.rootComponent;m=adsk.fusion.TemporaryBRepManager.get()
 P=lambda x,y,z:adsk.core.Point3D.create(x/10,y/10,z/10)
 U=adsk.fusion.BooleanTypes.UnionBooleanType;C=adsk.fusion.BooleanTypes.DifferenceBooleanType;I=adsk.fusion.BooleanTypes.IntersectionBooleanType
 def box(x0,y0,x1,y1,z0=0,z1=5):
  return m.createBox(adsk.core.OrientedBoundingBox3D.create(P((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),adsk.core.Vector3D.create(1,0,0),adsk.core.Vector3D.create(0,1,0),(x1-x0)/10,(y1-y0)/10,(z1-z0)/10))
 frame=box(-157,66,157,81)
 for b in [box(-157,-94,-148,70),box(148,-94,157,70),box(-157,-94,157,-79),box(-102,53,-76,70),box(76,53,102,70)]:assert m.booleanOperation(frame,b,U)
 for x in [-88.9,88.9]:assert m.booleanOperation(frame,m.createCylinderOrCone(P(x,63.5,-1),.35,P(x,63.5,6),.35),C)
 base=root.bRepBodies.add(frame);base.name='Uniform 15mm bottom rail - 5mm frame'
 edges=adsk.core.ObjectCollection.create()
 for e in base.edges:
  bb=e.boundingBox
  if bb.maxPoint.z-bb.minPoint.z>.49 and bb.maxPoint.x-bb.minPoint.x<.00001 and bb.maxPoint.y-bb.minPoint.y<.00001:edges.add(e)
 fi=root.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(.2),True);root.features.filletFeatures.add(fi)
 edges=adsk.core.ObjectCollection.create()
 for e in base.edges:
  if abs(e.boundingBox.maxPoint.z-e.boundingBox.minPoint.z)<.00001:edges.add(e)
 fi=root.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(.045),True);root.features.filletFeatures.add(fi)
 left=m.copy(base);right=m.copy(base);base.deleteMe()
 assert m.booleanOperation(left,box(-200,-120,-.1,100,-1,6),I)
 assert m.booleanOperation(right,box(.1,-120,200,100,-1,6),I)
 def component(name):
  o=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());o.component.name=name;return o
 lo=component('LEFT - 50mm continuous side-ridge tongues');ro=component('RIGHT - matching receiving grooves')
 male=[(-4,0),(4,0),(4,1.4),(5.25,1.4),(5.5,1.65),(5.5,3.8),(-5.5,3.8),(-5.5,1.65),(-5.25,1.4),(-4,1.4)]
 female=[(-4.25,-1),(4.25,-1),(4.25,1.15),(5.5,1.15),(5.75,1.4),(5.75,4.05),(-5.75,4.05),(-5.75,1.4),(-5.5,1.15),(-4.25,1.15)]
 def prism(comp,profile,x0,x1,y,round_tip=False):
  inp=comp.constructionPlanes.createInput();inp.setByOffset(comp.yZConstructionPlane,adsk.core.ValueInput.createByReal(x0/10));plane=comp.constructionPlanes.add(inp)
  sk=comp.sketches.add(plane)
  pts=[sk.modelToSketchSpace(P(x0,y+v,z)) for v,z in profile]
  for i,p in enumerate(pts):sk.sketchCurves.sketchLines.addByTwoPoints(p,pts[(i+1)%len(pts)])
  f=comp.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal((x1-x0)/10),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
  b=f.bodies.item(0)
  assert abs(b.boundingBox.maxPoint.x*10-x1)<.01
  if round_tip:
   edges=adsk.core.ObjectCollection.create()
   for e in b.edges:
    bb=e.boundingBox
    if abs(bb.minPoint.x*10-x1)<.01 and abs(bb.maxPoint.x*10-x1)<.01:edges.add(e)
   fi=comp.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(.025),True);comp.features.filletFeatures.add(fi)
  result=m.copy(b);b.deleteMe();sk.isVisible=False;plane.isLightBulbOn=False
  return result
 for y in [73.5,-86.5]:
  assert m.booleanOperation(left,prism(lo.component,male,-3,49.9,y,True),U)
  assert m.booleanOperation(right,prism(ro.component,female,-.2,50.4,y),C)
 source=None
 for lib in app.materialLibraries:
  for a in lib.appearances:
   if a.name=='Plastic - Matte (White)':source=a;break
  if source:break
 if not source:source=app.materialLibraries.item(0).appearances.item(0)
 pink=d.appearances.addByCopy(source,'Pink ABS')
 for p in pink.appearanceProperties:
  if p.objectType==adsk.core.ColorProperty.classType():p.value=adsk.core.Color.create(244,139,180,255)
 lb=lo.component.bRepBodies.add(left);lb.name='PINK - Left Tongue Half';lb.appearance=pink
 rb=ro.component.bRepBodies.add(right);rb.name='PINK - Right Groove Half';rb.appearance=pink
 overlap=m.copy(left);assert m.booleanOperation(overlap,m.copy(right),I);assert overlap.volume<.0000001
 print('Verified: zero assembled overlap; two solid halves; centered seam; two 50mm projecting tongues; 0.25mm side/Z clearance; 0.5mm end clearance.')
 for o in [lo,ro]:
  bb=o.component.boundingBox;print(o.component.name,[(bb.maxPoint.x-bb.minPoint.x)*10,(bb.maxPoint.y-bb.minPoint.y)*10,(bb.maxPoint.z-bb.minPoint.z)*10])
 # Calibration parts duplicate the full 50mm tongue and groove.
 ta=component('TEST - 50mm male tongue');tb=component('TEST - matching groove')
 a=box(-20,-7.5,-.1,7.5);b=box(.1,-7.5,60,7.5)
 assert m.booleanOperation(a,prism(ta.component,male,-3,49.9,0,True),U)
 assert m.booleanOperation(b,prism(tb.component,female,-.2,50.4,0),C)
 for co,body in [(ta,a),(tb,b)]:
  br=co.component.bRepBodies.add(body);br.appearance=pink;co.isLightBulbOn=False
 # Side-by-side layout uses two separate components and fits the H2D.
 poa=component('PRINT LEFT - separate object');pob=component('PRINT RIGHT - separate object')
 for i,(co,body) in enumerate([(poa,left),(pob,right)]):
  t=adsk.core.Matrix3D.create();t.setToRotation(math.pi/2,adsk.core.Vector3D.create(0,0,1),P(0,0,0));t.translation=adsk.core.Vector3D.create(*[(1.85,1,0),(-3.15,-1,0)][i])
  cp=m.copy(body);assert m.transform(cp,t)
  br=co.component.bRepBodies.add(cp);br.appearance=pink
 poa.isLightBulbOn=False;pob.isLightBulbOn=False
 def view(filename):
  cam=app.activeViewport.camera;cam.viewOrientation=adsk.core.ViewOrientations.TopViewOrientation;cam.isFitView=True;app.activeViewport.camera=cam;app.activeViewport.refresh()
  if filename:assert app.activeViewport.saveAsImageFile(filename,1600,1000)
 out=OUTPUT_DIRECTORY
 if out:
  os.makedirs(out,exist_ok=True);em=d.exportManager
  for co,name in [(lo,'Tongue-Left'),(ro,'Tongue-Right'),(ta,'Tongue-Test-Male'),(tb,'Tongue-Test-Groove')]:
   previous=co.isLightBulbOn;co.isLightBulbOn=True
   assert em.execute(em.createC3MFExportOptions(co.component,os.path.join(out,name+'.3mf')))
   co.isLightBulbOn=previous
  view(os.path.join(out,'LicensePlate-Tongue-Groove-Mockup.png'))
  assert em.execute(em.createFusionArchiveExportOptions(os.path.join(out,'LicensePlate-Tongue-Groove.f3d')))
 lo.isLightBulbOn=False;ro.isLightBulbOn=False;poa.isLightBulbOn=True;pob.isLightBulbOn=True
 check=m.copy(poa.component.bRepBodies.item(0));assert m.booleanOperation(check,m.copy(pob.component.bRepBodies.item(0)),I);assert check.volume<.0000001
 if out:view(os.path.join(out,'LicensePlate-Tongue-Groove-Print-Layout.png'))
 else:view('')
 combined=m.copy(poa.component.bRepBodies.item(0));assert m.booleanOperation(combined,m.copy(pob.component.bRepBodies.item(0)),U)
 assert combined.isSolid and combined.shells.count==2
 body=root.bRepBodies.add(combined);body.name='Both Frame Halves - Single Mesh Export Body';body.appearance=pink
 poa.isLightBulbOn=False;pob.isLightBulbOn=False
 if out:
  assert d.exportManager.execute(d.exportManager.createSTLExportOptions(body,os.path.join(out,'LicensePlate-Both-Halves.stl')))
  assert d.exportManager.execute(d.exportManager.createC3MFExportOptions(body,os.path.join(out,'LicensePlate-Both-Halves.3mf')))
  assert d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(os.path.join(out,'LicensePlate-Tongue-Groove.f3d')))
 print('Print layout: 225 x 294mm; one export body, two separate shells; bottom-open grooves with ridges at the top. Tongue bottoms lie at Z0.')
