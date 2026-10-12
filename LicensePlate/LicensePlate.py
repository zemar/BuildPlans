"""Recreate the Leafy Panda 5 mm ABS frame and two-object print layout in Fusion.

Load this folder in Fusion's Scripts and Add-Ins dialog and run LicensePlate.
Creates new documents without changing or saving existing documents.
The panda contours are embedded; no reference files or third-party packages are required.
Uses Fusion's installed Brush Script MT, Apple Chancery or Snell Roundhand font.
The final active document contains two separated multipart frame components.
The assembly document also includes hidden male/socket calibration coupons.
Dimensions are millimeters in the design; Fusion API coordinates are centimeters.
"""

import adsk.core, adsk.fusion, math

def _build_frame(_context):
 app=adsk.core.Application.get()
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
 doc.name='Leafy Panda - US Plate Frame v5 - 5mm'
 d=adsk.fusion.Design.cast(app.activeProduct)
 d.designType=adsk.fusion.DesignTypes.DirectDesignType
 root=d.rootComponent

 m=adsk.fusion.TemporaryBRepManager.get()
 P=lambda x,y,z:adsk.core.Point3D.create(x/10,y/10,z/10)
 def box(x0,y0,x1,y1,z0=0,z1=5):
  return m.createBox(adsk.core.OrientedBoundingBox3D.create(P((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),adsk.core.Vector3D.create(1,0,0),adsk.core.Vector3D.create(0,1,0),(x1-x0)/10,(y1-y0)/10,(z1-z0)/10))
 U=adsk.fusion.BooleanTypes.UnionBooleanType
 C=adsk.fusion.BooleanTypes.DifferenceBooleanType
 frame=box(-157,66,157,81)
 for b in [box(-157,-94,-148,70),box(148,-94,157,70),box(-157,-94,157,-79),box(-102,-83,102,-53),box(-102,53,-76,70),box(76,53,102,70)]:
  assert m.booleanOperation(frame,b,U)
 for x in [-88.9,88.9]:
  for y in [-63.5,63.5]:
   cut=m.createCylinderOrCone(P(x,y,-1),3.5/10,P(x,y,6),3.5/10)
   assert m.booleanOperation(frame,cut,C)
 base=root.bRepBodies.add(frame);base.name='01 PINK - Frame 3.2mm'
 source=None
 for lib in app.materialLibraries:
  for a in lib.appearances:
   if a.name=='Plastic - Matte (White)':source=a;break
  if source:break
 if not source: source=app.materialLibraries.item(0).appearances.item(0)
 def appearance(name,r,g,b):
  a=d.appearances.addByCopy(source,name)
  for p in a.appearanceProperties:
   if p.objectType==adsk.core.ColorProperty.classType():
    p.value=adsk.core.Color.create(r,g,b,255)
  return a
 pink=appearance('Leafy Blush Pink',244,139,180)
 black=appearance('Panda Ink Black',15,15,18)
 base.appearance=pink
 # Round all planar corners first, then every upper and lower rim.
 es=adsk.core.ObjectCollection.create()
 for e in base.edges:
  bb=e.boundingBox
  if bb.maxPoint.z-bb.minPoint.z>.31 and bb.maxPoint.x-bb.minPoint.x<.00001 and bb.maxPoint.y-bb.minPoint.y<.00001:es.add(e)
 fi=root.features.filletFeatures.createInput()
 fi.edgeSetInputs.addConstantRadiusEdgeSet(es,adsk.core.ValueInput.createByReal(.2),True)
 root.features.filletFeatures.add(fi)
 es=adsk.core.ObjectCollection.create()
 for e in base.edges:
  if abs(e.boundingBox.maxPoint.z-e.boundingBox.minPoint.z)<.00001:es.add(e)
 fi=root.features.filletFeatures.createInput()
 fi.edgeSetInputs.addConstantRadiusEdgeSet(es,adsk.core.ValueInput.createByReal(.045),True)
 root.features.filletFeatures.add(fi)
 print('Rounded planar corners R2mm and all frame rims R0.45mm')
 plane=root.constructionPlanes.createInput();plane.setByOffset(root.xYConstructionPlane,adsk.core.ValueInput.createByReal(.5))
 plane=root.constructionPlanes.add(plane)
 def extrude(sk,name):
  profiles=adsk.core.ObjectCollection.create()
  for p in sk.profiles:profiles.add(p)
  inp=root.features.extrudeFeatures.createInput(profiles,adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
  inp.setDistanceExtent(False,adsk.core.ValueInput.createByReal(.06))
  f=root.features.extrudeFeatures.add(inp)
  for b in f.bodies:b.name=name;b.appearance=black
  sk.isVisible=False
 sk=root.sketches.add(plane);sk.name='Leafy script'
 fonts=list(app.fontNames)
 font=next((f for f in ['Brush Script MT','Apple Chancery','Snell Roundhand'] if f in fonts),'Arial')
 print('Selected script font:',font)
 ti=sk.sketchTexts.createInput2('Leafy',1.68)
 ti.fontName=font
 ti.setAsMultiLine(P(-80,-77.5,0),P(0,-63.5,0),adsk.core.HorizontalAlignments.CenterHorizontalAlignment,adsk.core.VerticalAlignments.MiddleVerticalAlignment,0)
 t=sk.sketchTexts.add(ti)
 t.explode()
 print('Text profiles',sk.profiles.count)
 inner=set()
 for p in sk.profiles:
  for loop in p.profileLoops:
   if not loop.isOuter:
    inner.add(frozenset(c.sketchEntity.entityToken for c in loop.profileCurves))
 for p in sk.profiles:
  outer=next(loop for loop in p.profileLoops if loop.isOuter)
  if frozenset(c.sketchEntity.entityToken for c in outer.profileCurves) in inner:continue
  f=root.features.extrudeFeatures.addSimple(p,adsk.core.ValueInput.createByReal(.06),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
  for body in f.bodies:body.name='03 BLACK - Leafy script';body.appearance=black
 sk.isVisible=False;plane.isLightBulbOn=False
 app.activeViewport.fit()
 print('Frame dimensions 314 x 175 x 5 mm; holes 177.8 x 127 mm, diameter 7 mm; tag openings 46 x 26 mm nominal; relief 0.6 mm')
 print('Bodies',root.bRepBodies.count,'export methods',[x for x in dir(d.exportManager) if 'create' in x])


import adsk.core,adsk.fusion

def _add_panda(_context):
 app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct);root=d.rootComponent
 plane=root.constructionPlanes.item(0)
 P=lambda x,y,z:adsk.core.Point3D.create(x/10,y/10,z/10)
 black=d.appearances.itemByName('Panda Ink Black')
 # Trace the supplied panda picture into black solid regions.
 contours=__import__('json').loads(__import__('zlib').decompress(__import__('base64').b64decode(
  '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'
 )))
 sk=root.sketches.add(plane);sk.name='Reference panda traced artwork'
 sk.isComputeDeferred=True
 for loop in contours:
  for i,xy in enumerate(loop):
   end=loop[(i+1)%len(loop)]
   sk.sketchCurves.sketchLines.addByTwoPoints(P(40+xy[0]*34/38,-90.5+(xy[1]-40)*34/38,0),P(40+end[0]*34/38,-90.5+(end[1]-40)*34/38,0))
 sk.isComputeDeferred=False
 inner=set()
 for p in sk.profiles:
  for loop in p.profileLoops:
   if not loop.isOuter:inner.add(frozenset(c.sketchEntity.entityToken for c in loop.profileCurves))
 count=0
 for p in sk.profiles:
  outer=next(loop for loop in p.profileLoops if loop.isOuter)
  if frozenset(c.sketchEntity.entityToken for c in outer.profileCurves) in inner:continue
  f=root.features.extrudeFeatures.addSimple(p,adsk.core.ValueInput.createByReal(.06),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
  for body in f.bodies:body.name='02 BLACK - Reference panda';body.appearance=black;count+=1
 sk.isVisible=False
 print('Reference panda solid regions',count)


import adsk.core,adsk.fusion

def _build_snap_assembly(_context):
 app=adsk.core.Application.get()
 sourceDoc=next(doc for doc in reversed(list(app.documents)) if doc.name=='Leafy Panda - US Plate Frame v5 - 5mm')
 sourceDoc.activate()
 src=adsk.fusion.Design.cast(app.activeProduct)
 originals=[(b.name,adsk.fusion.TemporaryBRepManager.get().copy(b),b.appearance) for b in src.rootComponent.bRepBodies]
 pinkSource=src.appearances.itemByName('Leafy Blush Pink');blackSource=src.appearances.itemByName('Panda Ink Black')
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='Leafy Panda - ABS Snap Assembly Center Split 5mm'
 d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.DirectDesignType
 pink=d.appearances.addByCopy(pinkSource,'Leafy Blush Pink');black=d.appearances.addByCopy(blackSource,'Panda Ink Black')
 root=d.rootComponent;m=adsk.fusion.TemporaryBRepManager.get();P=lambda x,y,z:adsk.core.Point3D.create(x/10,y/10,z/10)
 U=adsk.fusion.BooleanTypes.UnionBooleanType;C=adsk.fusion.BooleanTypes.DifferenceBooleanType;I=adsk.fusion.BooleanTypes.IntersectionBooleanType
 def box(x0,y0,x1,y1,z0=0,z1=5):
  return m.createBox(adsk.core.OrientedBoundingBox3D.create(P((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),adsk.core.Vector3D.create(1,0,0),adsk.core.Vector3D.create(0,1,0),(x1-x0)/10,(y1-y0)/10,(z1-z0)/10))
 def comp(name):
  o=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());o.component.name=name;return o
 lo=comp('A - LEFT - male snaps');ro=comp('B - RIGHT - captured sockets')
 lb=m.copy(originals[0][1]);rb=m.copy(originals[0][1]);seam=0
 assert m.booleanOperation(lb,box(-200,-120,seam-.1,100,-1,6),I)
 assert m.booleanOperation(rb,box(seam+.1,-120,200,100,-1,6),I)
 def fork(comp,target,s,y):
  # Two 1.6mm wide arms flex in the print plane. Their hooks are relieved at rest.
  pi=comp.constructionPlanes.createInput();pi.setByOffset(comp.xYConstructionPlane,adsk.core.ValueInput.createByReal(.175));plane=comp.constructionPlanes.add(pi)
  for sign in [-1,1]:
   pts=[(-5,2),(20,2),(20,3.3),(17,4.3),(15.5,4.3),(15.5,3.6),(-5,3.6)]
   pts=[(s+x,y+sign*v) for x,v in pts]
   sk=comp.sketches.add(plane)
   for i,(x,v) in enumerate(pts):
    nx,nv=pts[(i+1)%len(pts)];sk.sketchCurves.sketchLines.addByTwoPoints(P(x,v,0),P(nx,nv,0))
   f=comp.features.extrudeFeatures.addSimple(sk.profiles.item(0),adsk.core.ValueInput.createByReal(.15),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
   arm=f.bodies.item(0)
   # Round the arm outline to remove sharp notch corners.
   es=adsk.core.ObjectCollection.create()
   for e in arm.edges:
    bb=e.boundingBox
    if bb.maxPoint.z-bb.minPoint.z>.14:es.add(e)
   fi=comp.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(es,adsk.core.ValueInput.createByReal(.02),True)
   comp.features.filletFeatures.add(fi)
   assert m.booleanOperation(target,m.copy(arm),U)
   arm.deleteMe();sk.isVisible=False
  plane.isLightBulbOn=False
 def socket(target,s,y):
  # Roof and floor capture the fork in Z; the widened pocket receives both hooks.
  assert m.booleanOperation(target,box(s-.3,y-3.85,s+15.2,y+3.85,1.5,3.5),C)
  assert m.booleanOperation(target,box(s+15.2,y-4.55,s+20.55,y+4.55,1.5,3.5),C)
  # Front access holes allow pressing both hooks inward with a small tool.
  for sign in [-1,1]:
   yy=y+sign*3.8
   assert m.booleanOperation(target,box(s+15.4,yy-.65,s+19.3,yy+.65,-1,1.6),C)
 for y in [73.5,-73.5]:fork(lo.component,lb,seam,y);socket(rb,seam,y)
 lbody=lo.component.bRepBodies.add(lb);lbody.name='PINK - left structural half';lbody.appearance=pink
 rbody=ro.component.bRepBodies.add(rb);rbody.name='PINK - right structural half';rbody.appearance=pink
 # Generous root fillets on each spring arm where it enters the frame.
 es=adsk.core.ObjectCollection.create()
 for e in lbody.edges:
  bb=e.boundingBox
  if abs(bb.minPoint.x*10-(seam-.1))<.01 and abs(bb.maxPoint.x-bb.minPoint.x)<.00001 and bb.maxPoint.z-bb.minPoint.z>.14:
   if any(abs(abs(bb.minPoint.y*10-y)-v)<.03 for y in [73.5,-73.5] for v in [2,3.6]):es.add(e)
 print('Root edges',es.count)
 if es.count:
  fi=lo.component.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(es,adsk.core.ValueInput.createByReal(.06),True);lo.component.features.filletFeatures.add(fi)
 for name,b,appearance in originals[1:]:
  assert b.boundingBox.maxPoint.x*10<seam or b.boundingBox.minPoint.x*10>seam
  destination=lo if b.boundingBox.maxPoint.x*10<seam else ro
  body=destination.component.bRepBodies.add(b);body.name=name;body.appearance=black
 # Small coupon duplicates the actual joint, with the same thickness and clearances.
 ca=comp('TEST A - male');cb=comp('TEST B - socket')
 a=box(-30,-7.5,-.1,7.5);b=box(.1,-7.5,30,7.5)
 fork(ca.component,a,0,0);socket(b,0,0)
 ba=ca.component.bRepBodies.add(a);ba.name='Test male';ba.appearance=pink
 bb=cb.component.bRepBodies.add(b);bb.name='Test socket';bb.appearance=pink
 es=adsk.core.ObjectCollection.create()
 for e in ba.edges:
  bounds=e.boundingBox
  if abs(bounds.minPoint.x*10+.1)<.01 and abs(bounds.maxPoint.x-bounds.minPoint.x)<.00001 and bounds.maxPoint.z-bounds.minPoint.z>.14:es.add(e)
 fi=ca.component.features.filletFeatures.createInput();fi.edgeSetInputs.addConstantRadiusEdgeSet(es,adsk.core.ValueInput.createByReal(.06),True);ca.component.features.filletFeatures.add(fi)
 ca.isLightBulbOn=False;cb.isLightBulbOn=False
 for co in [lo,ro]:
  bb=co.component.boundingBox
  print(co.component.name,'size mm',round((bb.maxPoint.x-bb.minPoint.x)*10,2),round((bb.maxPoint.y-bb.minPoint.y)*10,2))
 print('Arm length 20 mm, in-plane width 1.6 mm, thickness 1.5 mm; throat clearance 0.25 mm per side, Z clearance 0.25 mm; hook deflection about 0.45 mm')
 app.activeViewport.fit()


import adsk.core,adsk.fusion,math

def _arrange_print_objects(_context):
 app=adsk.core.Application.get()
 source=next(doc for doc in reversed(list(app.documents)) if doc.name=='Leafy Panda - ABS Snap Assembly Center Split 5mm');source.activate()
 src=adsk.fusion.Design.cast(app.activeProduct);m=adsk.fusion.TemporaryBRepManager.get()
 saved=[]
 for i in [0,1]:
  comp=src.rootComponent.occurrences.item(i).component
  saved.append([(b.name,m.copy(b)) for b in comp.bRepBodies])
 ps=src.appearances.itemByName('Leafy Blush Pink');bs=src.appearances.itemByName('Panda Ink Black')
 doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='Leafy Panda - Two Objects Print Layout 5mm'
 d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.DirectDesignType
 pink=d.appearances.addByCopy(ps,'Leafy Blush Pink');black=d.appearances.addByCopy(bs,'Panda Ink Black')
 r=d.rootComponent;parts=[]
 for i,bodies in enumerate(saved):
  o=r.occurrences.addNewComponent(adsk.core.Matrix3D.create());o.component.name=['LEFT - Leafy - snap tongues','RIGHT - Panda - sockets'][i]
  tr=adsk.core.Matrix3D.create();tr.setToRotation(math.pi/2,adsk.core.Vector3D.create(0,0,1),adsk.core.Point3D.create(0,0,0))
  tr.translation=adsk.core.Vector3D.create(*([(1.85,1,0),(-3.15,-1,0)][i]))
  for name,b in bodies:
   assert m.transform(b,tr)
   body=o.component.bRepBodies.add(b);body.name=name;body.appearance=pink if name.startswith('PINK') else black
  parts.append(o)
 a=m.copy(next(b for b in parts[0].component.bRepBodies if b.name.startswith('PINK')))
 bb=next(b for b in parts[1].component.bRepBodies if b.name.startswith('PINK'))
 assert m.booleanOperation(a,m.copy(bb),adsk.fusion.BooleanTypes.IntersectionBooleanType)
 assert a.volume<.0000001
 bounds=r.boundingBox
 print('Print arrangement mm:',(bounds.maxPoint.x-bounds.minPoint.x)*10,(bounds.maxPoint.y-bounds.minPoint.y)*10,'collision volume',a.volume)
 cam=app.activeViewport.camera;cam.viewOrientation=adsk.core.ViewOrientations.TopViewOrientation;cam.isFitView=True;app.activeViewport.camera=cam;app.activeViewport.refresh()


def run(context):
    _build_frame(context)
    _add_panda(context)
    _build_snap_assembly(context)
    _arrange_print_objects(context)
    print('Leafy Panda recreated: 5 mm frame, centered snap seam, two printable objects.')
