"""Lily plaque: 300 x 150 x 15 mm, flush bronze lettering, wood rope border.
Run in Autodesk Fusion (Scripts and Add-Ins). No packages or artwork files needed.
Dimensions are mm; Fusion geometry is cm internally. XY is the plaque face,
Z=0 rear, Z=15 front. Feet support a 15-degree backward lean from vertical.
Select each named parent component for Save as Mesh; retain plaque color bodies.
"""
from pathlib import Path
import base64,json,logging,math,time,traceback,zlib
WIDTH_MM=300.0
HEIGHT_MM=150.0
TOTAL_THICKNESS_MM=15.0
INLAY_THICKNESS_MM=0.6
FRAME_MM=12.0
ROPE_STRAND_RADIUS_MM=3.2
ROPE_TWIST_RADIUS_MM=1.8
ROPE_PITCH_MM=18.0
ROPE_BACKING_MM=9.0
ROPE_SURFACE_BASE_MM=10.0
BASE_EDGE_RADIUS_MM=0.0
ANGLE_DEG=15.0
CHANNEL_CENTERS=(75.0,225.0)
CHANNEL_START=-1.0
CHANNEL_END=75.0
FOOT_WIDTH_MM=15.0
TONGUE_NECK_MM=11.0
TONGUE_HEAD_MM=15.0
TONGUE_STEP_MM=1.5
TONGUE_DEPTH_MM=3.6
JOINT_CLEARANCE_MM=.30
JOINT_RADIUS_MM=.40
RAIL_START_MM=5.0
RAIL_END_MM=CHANNEL_END
WEB_BACK_CLEARANCE_MM=.4
FOOT_TOP_EDGE_RADIUS_MM=.5
ROOT=Path(__file__).resolve().parent
LOG_PATH=ROOT/'LilyPlaque.log'
PALETTE=(('Black PLA',(18,18,20)),('Wood PLA',(158,105,57)),('Metallic bronze PLA',(177,119,57)))

def make_appearance(app, design, name, rgb):
    import adsk.core
    title = 'Lily Plaque '+name
    existing = design.appearances.itemByName(title)
    if existing:
        return existing
    library = app.materialLibraries.itemById('BA5EE55E-9982-449B-9D66-9F036540E140')
    seed = library.appearances.itemById('Prism-129') if library else None
    if not seed:
        raise RuntimeError('Fusion generic appearance is unavailable.')
    finish = design.appearances.addByCopy(seed,title)
    for key in ('opaque_albedo','generic_diffuse'):
        prop = adsk.core.ColorProperty.cast(finish.appearanceProperties.itemById(key))
        if prop:
            prop.hasConnectedTexture = False
            prop.value = adsk.core.Color.create(*rgb,255)
            return finish
    raise RuntimeError('Appearance has no editable base color: '+name)

def round_profile_corners(poly, corner_indices, radius, segments=8):
    """Replace selected convex profile corners with sampled circular arcs."""
    rounded = []
    tangent_distances = {}
    for i, corner in enumerate(poly):
        if i not in corner_indices:
            rounded.append(corner)
            continue
        previous = poly[i-1]
        following = poly[(i+1)%len(poly)]
        to_previous = (previous[0]-corner[0], previous[1]-corner[1])
        to_following = (following[0]-corner[0], following[1]-corner[1])
        previous_length = math.hypot(*to_previous)
        following_length = math.hypot(*to_following)
        u = (to_previous[0]/previous_length, to_previous[1]/previous_length)
        v = (to_following[0]/following_length, to_following[1]/following_length)
        angle = math.acos(max(-1.0, min(1.0, u[0]*v[0]+u[1]*v[1])))
        if not 0 < angle < math.pi:
            raise ValueError('Foot top edge requires a convex profile corner.')
        tangent = radius/math.tan(angle/2)
        if tangent >= min(previous_length, following_length):
            raise ValueError('Foot top edge radius does not fit its profile.')
        tangent_distances[i] = tangent
        start = (corner[0]+u[0]*tangent, corner[1]+u[1]*tangent)
        end = (corner[0]+v[0]*tangent, corner[1]+v[1]*tangent)
        bisector = (u[0]+v[0], u[1]+v[1])
        bisector_length = math.hypot(*bisector)
        center_distance = radius/math.sin(angle/2)
        center = (corner[0]+bisector[0]/bisector_length*center_distance,
                  corner[1]+bisector[1]/bisector_length*center_distance)
        start_angle = math.atan2(start[1]-center[1], start[0]-center[0])
        end_angle = math.atan2(end[1]-center[1], end[0]-center[0])
        incoming = (corner[0]-previous[0], corner[1]-previous[1])
        outgoing = (following[0]-corner[0], following[1]-corner[1])
        direction = 1 if incoming[0]*outgoing[1]-incoming[1]*outgoing[0] > 0 else -1
        sweep = (end_angle-start_angle) % (2*math.pi) if direction > 0 else -(
            (start_angle-end_angle) % (2*math.pi))
        for step in range(segments+1):
            if step == 0:
                rounded.append(start)
            elif step == segments:
                rounded.append(end)
            else:
                angle_at = start_angle+sweep*step/segments
                rounded.append((center[0]+radius*math.cos(angle_at),
                                center[1]+radius*math.sin(angle_at)))
    return rounded, tangent_distances

def table_height(base=15.0, radius=0.0):
    """Exact tabletop support height of the rounded lower edge at 15 degrees."""
    angle=math.radians(ANGLE_DEG)
    return radius*(math.cos(angle)+math.sin(angle)-1)

def joint_outline(center, clearance=0.0):
    """ShowerCaddy's open T section, sized for this plaque (mm in X/Z).

    Continuous longitudinal ridges are captured behind the rear lips.
    The neck stays open to the back; there are no teeth or loading bays.
    """
    n=TONGUE_NECK_MM/2+clearance
    h=TONGUE_HEAD_MM/2+clearance
    step=TONGUE_STEP_MM-clearance
    depth=TONGUE_DEPTH_MM+clearance
    return [(center-n,-1),(center+n,-1),(center+n,step),
            (center+h,step),(center+h,depth),(center-h,depth),
            (center-h,step),(center-n,step)]

def joint_prism(component, name, center, y0, y1, clearance, operation):
    """Extrude the same rounded T profile along the entire sliding direction."""
    import adsk.core, adsk.fusion
    point=adsk.core.Point3D.create
    value=adsk.core.ValueInput.createByReal
    pi=component.constructionPlanes.createInput()
    normal_y=component.xZConstructionPlane.geometry.normal.y
    pi.setByOffset(component.xZConstructionPlane,value(y0/(10*normal_y)))
    plane=component.constructionPlanes.add(pi)
    sketch=component.sketches.add(plane);sketch.name=name
    def p(x,z):return sketch.modelToSketchSpace(point(x/10,y0/10,z/10))
    vertices=joint_outline(center,clearance);corners=[]
    # Same tangent arc construction and 0.4 mm corner radius as ShowerCaddy.
    radius=JOINT_RADIUS_MM
    for i,v in enumerate(vertices):
        prev,nxt=vertices[i-1],vertices[(i+1)%len(vertices)]
        u=(prev[0]-v[0],prev[1]-v[1]);w=(nxt[0]-v[0],nxt[1]-v[1])
        lu,lw=math.hypot(*u),math.hypot(*w)
        assert min(lu,lw)>2*radius
        u=tuple(a/lu for a in u);w=tuple(a/lw for a in w)
        a=(v[0]+u[0]*radius,v[1]+u[1]*radius)
        b=(v[0]+w[0]*radius,v[1]+w[1]*radius)
        q=radius*(1-1/math.sqrt(2))
        mid=(v[0]+(u[0]+w[0])*q,v[1]+(u[1]+w[1])*q)
        corners.append((a,mid,b))
    for i,(a,mid,b) in enumerate(corners):
        sketch.sketchCurves.sketchArcs.addByThreePoints(p(*a),p(*mid),p(*b))
        sketch.sketchCurves.sketchLines.addByTwoPoints(p(*b),p(*corners[(i+1)%len(corners)][0]))
    assert sketch.profiles.count==1,name
    feature=component.features.extrudeFeatures.addSimple(sketch.profiles.item(0),value((y1-y0)/(10*normal_y)),operation)
    feature.name=name
    if feature.errorOrWarningMessage:
        raise RuntimeError(name+": "+feature.errorOrWarningMessage)
    sketch.isVisible=False;plane.isLightBulbOn=False
    return feature

def build_foot(component,center,finish,logger):
    """One native black solid: 15 mm web, rear-only sole, and ridged T tongue."""
    import adsk.core, adsk.fusion
    angle=math.radians(ANGLE_DEG);co,si=math.cos(angle),math.sin(angle)
    def yz(height,rear):return (height*co+rear*si,height*si-rear*co)
    ground=table_height(TOTAL_THICKNESS_MM,BASE_EDGE_RADIUS_MM)
    profile=[(RAIL_END_MM,-WEB_BACK_CLEARANCE_MM),(RAIL_START_MM,-WEB_BACK_CLEARANCE_MM),
             yz(ground+4,8),yz(ground,8),yz(ground,65),yz(ground+4,65),(RAIL_END_MM,-4)]
    profile,_=round_profile_corners(profile,(0,1),FOOT_TOP_EDGE_RADIUS_MM)
    point=adsk.core.Point3D.create;value=adsk.core.ValueInput.createByReal
    pi=component.constructionPlanes.createInput()
    normal_x=component.yZConstructionPlane.geometry.normal.x
    pi.setByOffset(component.yZConstructionPlane,value((center-FOOT_WIDTH_MM/2)/(10*normal_x)))
    plane=component.constructionPlanes.add(pi);sketch=component.sketches.add(plane)
    sketch.name='15 mm rear support web and tabletop sole'
    pts=[sketch.modelToSketchSpace(point((center-FOOT_WIDTH_MM/2)/10,y/10,z/10)) for y,z in profile]
    for a,b in zip(pts,pts[1:]+pts[:1]):sketch.sketchCurves.sketchLines.addByTwoPoints(a,b)
    ex=component.features.extrudeFeatures
    web=ex.addSimple(sketch.profiles.item(0),value(FOOT_WIDTH_MM/(10*normal_x)),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    sketch.isVisible=False;plane.isLightBulbOn=False
    joint_prism(component,'Continuous ridged sliding tongue',center,RAIL_START_MM,RAIL_END_MM,0,
                adsk.fusion.FeatureOperations.JoinFeatureOperation)
    assert component.bRepBodies.count==1
    body=component.bRepBodies.item(0);body.name='Black PLA 15 mm rear foot with ridged tongue';body.appearance=finish
    assert body.isSolid
    bb=body.preciseBoundingBox
    assert abs((bb.maxPoint.x-bb.minPoint.x)*10-FOOT_WIDTH_MM)<1e-5
    assert abs(bb.maxPoint.z*10-TONGUE_DEPTH_MM)<1e-5
    assert abs(bb.maxPoint.y*10-CHANNEL_END)<1e-5
    # The sole is behind the plaque and on the exact same support plane.
    for rear in (8,65):
        y,z=yz(ground,rear)
        assert z<0 and abs(y*co+z*si-ground)<1e-9
    logger.info('VERIFIED foot: width=%.2f mm, single black native solid, tongue %.2f/%.2f x %.2f mm; clearance %.2f mm per side; rear-only sole at %.6f mm support height',
                FOOT_WIDTH_MM,TONGUE_NECK_MM,TONGUE_HEAD_MM,TONGUE_DEPTH_MM,JOINT_CLEARANCE_MM,ground)
    return body

def draw_ring(sketch, ring):
    import adsk.core
    points = [adsk.core.Point3D.create(x/10,y/10,0) for x,y in ring]
    lines = sketch.sketchCurves.sketchLines
    first = lines.addByTwoPoints(points[0],points[1])
    end = first.endSketchPoint
    for point in points[2:]:
        end = lines.addByTwoPoints(end,point).endSketchPoint
    lines.addByTwoPoints(end,first.startSketchPoint)

def select_profiles(sketch, regions, logger):
    """Match profile area AND centroid moments, including concave/holey regions.

    Centroids need not lie inside a region, so point sampling is not used.
    This excludes profiles corresponding to holes and unrelated nested loops.
    """
    import adsk.core
    import adsk.fusion
    candidates = []
    for profile in sketch.profiles:
        props = profile.areaProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy)
        candidates.append((profile,props.area*100,props.centroid.x*10,props.centroid.y*10))
    selected = adsk.core.ObjectCollection.create()
    for region in regions:
        area = region['area']
        x,y = region['centroid']
        def score(item):
            return abs(item[1]-area)/max(area,.01)+math.hypot(item[2]-x,item[3]-y)
        if not candidates:
            raise RuntimeError('Missing closed profile: '+str(region['centroid']))
        best = min(candidates,key=score)
        # Exact circle replaces its vector approximation: <=0.013 mm² delta.
        if abs(best[1]-area)>max(.02,area*1e-5) or math.hypot(best[2]-x,best[3]-y)>.02:
            raise RuntimeError('Profile mismatch: expected area/centroid %s/%s; got %s'%
                               (area,region['centroid'],best[1:]))
        selected.add(best[0])
        candidates.remove(best)
    logger.info('%s: matched %d vector regions; %d unselected hole profiles',
                sketch.name,selected.count,len(candidates))
    return selected


def rope_frame():
    """MyriSaying's fused two-strand envelope, seated inside the 15 mm depth.

    The strand centers orbit one another continuously around the perimeter.
    A closed relief solid meets the native wood backing at Z=9 mm. Its upper
    envelope ranges from 10 to 15 mm; the black face and bronze remain Z=15.
    """
    f=FRAME_MM
    outside=[(0,0),(WIDTH_MM,0),(WIDTH_MM,HEIGHT_MM),(0,HEIGHT_MM)]
    inside=[(f,f),(WIDTH_MM-f,f),(WIDTH_MM-f,HEIGHT_MM-f),(f,HEIGHT_MM-f)]
    lengths=[WIDTH_MM-f,HEIGHT_MM-f]*2
    perimeter=sum(lengths)
    turns=max(1,round(perimeter/ROPE_PITCH_MM))
    points=[];heights=[];top=[];traveled=0.0
    cross_steps=24
    for edge,length in enumerate(lengths):
        nxt=(edge+1)%4
        steps=math.ceil(length/.65)
        for step in range(steps):
            t=step/steps
            outer=[outside[edge][k]*(1-t)+outside[nxt][k]*t for k in (0,1)]
            inner=[inside[edge][k]*(1-t)+inside[nxt][k]*t for k in (0,1)]
            phase=2*math.pi*turns*(traveled+length*t)/perimeter
            for j in range(cross_steps+1):
                u=j/cross_steps;across=(u-.5)*f
                points.append(tuple(outer[k]*(1-u)+inner[k]*u for k in (0,1)))
                relief=0.0
                for sign in (-1,1):
                    center_u=sign*ROPE_TWIST_RADIUS_MM*math.cos(phase)
                    center_h=sign*ROPE_TWIST_RADIUS_MM*math.sin(phase)
                    radicand=ROPE_STRAND_RADIUS_MM**2-(across-center_u)**2
                    if radicand>0:relief=max(relief,center_h+math.sqrt(radicand))
                heights.append(ROPE_SURFACE_BASE_MM+relief)
        traveled+=length
    stride=cross_steps+1;stations=len(points)//stride
    for i in range(stations):
        nxt=(i+1)%stations
        for j in range(cross_steps):
            a,b,c,d=i*stride+j,nxt*stride+j,nxt*stride+j+1,i*stride+j+1
            top.extend(((a,b,c),(a,c,d)))
    # Extrude the annular triangulation, closing both perimeter walls and all
    # corners. Shared edges cancel, so there are no overlapping strand shells.
    edges={}
    for a,b,c in top:
        for u,v in ((a,b),(b,c),(c,a)):
            key=tuple(sorted((u,v)))
            if key in edges:edges[key]=None
            else:edges[key]=(u,v)
    n=len(points)
    vertices=[(x,y,ROPE_BACKING_MM) for x,y in points]
    vertices.extend((x,y,z) for (x,y),z in zip(points,heights))
    triangles=[(c,b,a) for a,b,c in top]
    triangles.extend((a+n,b+n,c+n) for a,b,c in top)
    for edge in edges.values():
        if edge:
            a,b=edge;triangles.extend(((a,b,b+n),(a,b+n,a+n)))
    assert max(heights)<=TOTAL_THICKNESS_MM+1e-9
    assert min(heights)>ROPE_BACKING_MM
    return vertices,triangles


def group_3mf_object(path, name='Lily plaque'):
    """Wrap Fusion's flat build list in one 3MF assembly; retain color meshes.

    Fusion's One File option still exports an independent build item per body.
    A single assembly build item prevents a slicer from dropping each inlay to
    the bed. Only the object hierarchy changes; vertices, materials, and part
    placement are preserved exactly.
    """
    import io,uuid,zipfile,xml.etree.ElementTree as ET
    path=Path(path)
    with zipfile.ZipFile(path,'r') as archive:
        entries=[(info,archive.read(info.filename)) for info in archive.infolist()]
    target='3D/3dmodel.model'
    data=next(data for info,data in entries if info.filename==target)
    for _,(prefix,uri) in ET.iterparse(io.BytesIO(data),events=('start-ns',)):
        ET.register_namespace(prefix,uri)
    model=ET.fromstring(data)
    namespace=model.tag.split('}')[0][1:]
    tag=lambda name:'{'+namespace+'}'+name
    resources=model.find(tag('resources'));build=model.find(tag('build'))
    items=list(build)
    if len(items)==1:return
    assert items and all(item.tag==tag('item') for item in items)
    assembly_id=str(max(int(child.get('id','0')) for child in resources)+1)
    production='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}UUID'
    assembly=ET.SubElement(resources,tag('object'),
                           {'id':assembly_id,'name':name,'type':'model',production:str(uuid.uuid4())})
    components=ET.SubElement(assembly,tag('components'))
    for item in items:
        # Component transforms use exactly the same coordinate convention as
        # build item transforms. Copy them, including any production path.
        attributes={key:value for key,value in item.attrib.items()
                    if key not in ('printable',production)}
        ET.SubElement(components,tag('component'),attributes)
        build.remove(item)
    ET.SubElement(build,tag('item'),{'objectid':assembly_id,production:str(uuid.uuid4())})
    replacement=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    temporary=path.with_name(path.stem+'.writing.3mf')
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for info,content in entries:
                archive.writestr(info,replacement if info.filename==target else content)
        with zipfile.ZipFile(temporary) as archive:
            checked=ET.fromstring(archive.read(target))
            assert len(checked.find(tag('build')))==1
            objects={o.get('id'):o for o in checked.find(tag('resources')) if o.tag==tag('object')}
            assert len(objects[assembly_id].find(tag('components')))==len(items)
            assert all(child.get('objectid') in objects for child in objects[assembly_id].find(tag('components')))
        temporary.replace(path)
    finally:
        if temporary.exists():temporary.unlink()


def export_printables(design,logger):
    """Three independent print objects, with all plaque colors kept together."""
    import adsk.fusion
    parts=[('01 Lily plaque','plaque.3mf'),('02 Black PLA foot','left_foot.3mf'),
           ('03 Black PLA foot','right foot.3mf')]
    for prefix,filename in parts:
        matches=[o for o in design.rootComponent.occurrences if o.component.name.startswith(prefix)]
        assert len(matches)==1,(prefix,len(matches))
        path=ROOT/filename
        options=design.exportManager.createC3MFExportOptions(matches[0],str(path))
        options.isOneFilePerBody=False
        options.sendToPrintUtility=False
        options.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        assert design.exportManager.execute(options),'Could not export '+filename
        group_3mf_object(path,'Lily plaque' if filename=='plaque.3mf' else prefix)
        logger.info('EXPORTED one printable object: %s',path)


def build_design(app,logger):
    import adsk.core,adsk.fusion
    p=lambda x,y,z=0:adsk.core.Point3D.create(x/10,y/10,z/10)
    v=adsk.core.ValueInput.createByReal
    new=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    cut=adsk.fusion.FeatureOperations.CutFeatureOperation
    doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name='Lily - Flush Bronze Rope Plaque'
    design=adsk.fusion.Design.cast(app.activeProduct)
    design.designType=adsk.fusion.DesignTypes.DirectDesignType
    design.fusionUnitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
    root=design.rootComponent
    def component(name):
        occurrence=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        occurrence.component.name=name
        return occurrence.component
    finishes=[make_appearance(app,design,n,rgb) for n,rgb in PALETTE]
    plaque=component('01 Lily plaque - all three colors - Save as Mesh')
    ex=plaque.features.extrudeFeatures
    def rect_body(name,x0,y0,x1,y1,inner=False,depth=TOTAL_THICKNESS_MM):
        sk=plaque.sketches.add(plaque.xYConstructionPlane);sk.name=name
        sk.sketchCurves.sketchLines.addTwoPointRectangle(p(x0,y0),p(x1,y1))
        if inner:sk.sketchCurves.sketchLines.addTwoPointRectangle(p(FRAME_MM,FRAME_MM),p(WIDTH_MM-FRAME_MM,HEIGHT_MM-FRAME_MM))
        profile=(min if inner else max)(sk.profiles,key=lambda a:a.areaProperties().area)
        body=ex.addSimple(profile,v(depth/10),new).bodies.item(0)
        sk.isVisible=False;body.name=name
        return body
    frame=rect_body('Wood PLA - rope backing with sliding grooves',0,0,WIDTH_MM,HEIGHT_MM,True,ROPE_BACKING_MM)
    frame.appearance=finishes[1]
    base=rect_body('Black PLA with flush bronze pockets',FRAME_MM,FRAME_MM,WIDTH_MM-FRAME_MM,HEIGHT_MM-FRAME_MM)
    base.appearance=finishes[0]
    # Use the same closed two-strand relief geometry as MyriSaying.py.
    vertices,triangles=rope_frame()
    rope=plaque.meshBodies.addByTriangleMeshData(
        [coordinate/10 for vertex in vertices for coordinate in vertex],
        [index for triangle in triangles for index in triangle],[],[])
    if rope is None:raise RuntimeError('Could not create twisted rope relief.')
    rope.name='Wood PLA - continuous two-strand twisted rope'
    rope.appearance=finishes[1]
    rope.displayOverrides.isSuppressFaceGroupColors=True
    rope.displayOverrides.isSuppressTriangleEdges=True
    logger.info('Rope relief: strand radius %.2f, orbit %.2f, pitch %.2f mm; %d triangles; Z=9..15 mm',
                ROPE_STRAND_RADIUS_MM,ROPE_TWIST_RADIUS_MM,ROPE_PITCH_MM,len(triangles))
    tm=adsk.fusion.TemporaryBRepManager.get()
    for center in CHANNEL_CENTERS:
        joint_prism(plaque,'Open-back bottom-loading T groove',center,CHANNEL_START,CHANNEL_END,JOINT_CLEARANCE_MM,cut)
    expected=sum(b.volume for b in plaque.bRepBodies)
    pi=plaque.constructionPlanes.createInput()
    pi.setByOffset(plaque.xYConstructionPlane,v((TOTAL_THICKNESS_MM-INLAY_THICKNESS_MM)/10))
    plane=plaque.constructionPlanes.add(pi);plane.isLightBulbOn=False
    regions=json.loads(zlib.decompress(base64.b85decode(LETTERING_B85)))
    black=tm.copy(base)
    for number,region in enumerate(regions,1):
        sk=plaque.sketches.add(plane);sk.name='Bronze inlay %03d'%number
        sk.isComputeDeferred=True
        for ring in region['rings']:draw_ring(sk,ring)
        sk.isComputeDeferred=False
        profiles=select_profiles(sk,[region],logger)
        feature=ex.addSimple(profiles,v(INLAY_THICKNESS_MM/10),new)
        sk.isVisible=False
        for body in feature.bodies:
            body.name='Metallic bronze flush lettering %03d'%number;body.appearance=finishes[2]
            assert body.isSolid
            assert abs(body.preciseBoundingBox.maxPoint.z*10-15)<1e-5
            assert abs(body.preciseBoundingBox.minPoint.z*10-14.4)<1e-5
            assert tm.booleanOperation(black,tm.copy(body),adsk.fusion.BooleanTypes.DifferenceBooleanType)
        if number%8==0:adsk.doEvents()
    base.deleteMe();base=plaque.bRepBodies.add(black)
    base.name='Black PLA - matching flush inlay pockets';base.appearance=finishes[0]
    size=[(getattr(plaque.preciseBoundingBox.maxPoint,a)-getattr(plaque.preciseBoundingBox.minPoint,a))*10 for a in ('x','y','z')]
    assert all(abs(a-b)<1e-4 for a,b in zip(size,(300,150,15))),size
    assert abs(sum(b.volume for b in plaque.bRepBodies)-expected)<expected*.0003
    for body in plaque.bRepBodies:assert body.isSolid and body.lumps.count==1,body.name
    logger.info('VERIFIED plaque %s mm; all lettering flush at Z=15; %d color solids',size,plaque.bRepBodies.count)
    for number,center in enumerate(CHANNEL_CENTERS,1):
        foot=component('0%d Black PLA foot - %s - Save as Mesh'%(number+1,'Left' if number==1 else 'Right'))
        body=build_foot(foot,center,finishes[0],logger)
        for offset in (0,-10,-35,-70,-80):
            for target in (base,frame):
                sample=tm.copy(body);shift=adsk.core.Matrix3D.create()
                shift.translation=adsk.core.Vector3D.create(0,offset/10,0)
                assert tm.transform(sample,shift)
                assert tm.booleanOperation(sample,tm.copy(target),adsk.fusion.BooleanTypes.IntersectionBooleanType)
                assert sample.faces.count==0,('Foot collision',number,offset,target.name)
        logger.info('VERIFIED foot %d: 15 mm thickness, 15-degree tilt, collision-free insertion',number)
    cam=app.activeViewport.camera
    cam.eye=p(150,75,700);cam.target=p(150,75,0)
    cam.upVector=adsk.core.Vector3D.create(0,1,0)
    cam.isPerspective=False;cam.isFitView=True
    app.activeViewport.camera=cam
    app.activeViewport.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
    app.activeViewport.fit();app.activeViewport.refresh()
    app.activeViewport.saveAsImageFile(str(ROOT/'mockup.png'),1500,850)
    return design

def run(context):
    logger=logging.getLogger('LilyPlaque');logger.setLevel(logging.INFO);logger.propagate=False
    for h in list(logger.handlers):logger.removeHandler(h);h.close()
    handler=logging.FileHandler(LOG_PATH,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler);started=time.monotonic()
    try:
        import adsk.core
        logger.info('RUN START: Lily plaque, 300 x 150 x 15 mm; MyriSaying two-strand rope; bronze inlays; black feet')
        design=build_design(adsk.core.Application.get(),logger)
        export_printables(design,logger)
        logger.info('RUN SUCCESS')
    except Exception:
        logger.exception('RUN FAILED');raise
    finally:
        logger.info('RUN END %.2fs',time.monotonic()-started)
        handler.flush();logger.removeHandler(handler);handler.close()

# Embedded Snell Roundhand Bold (lines 1/2) and Arial (line 3) outlines.
LETTERING_B85 = (
    'c-ox3%MNBqZlw7tLal{>-!IzDa|l`p-NHaXj|4~q^rA8EKK7ZDCo&Zo8$qQ)WhCSL=i*K$jYi`?{-3}7uYdiwfBD-#{O$kxyZ`;K'
    '|M@R}_rL%B|M};C`@4VtxBu}kfA^pN{ICD>AO80DfBPT*{=feHKmPU)?eG8g&;Ri+|NOUq=s!wXXN*1XDrK&_Wb-fo_W%CJzyIt1'
    '{M$eLV{7xrZ2PXZ>+1W|{r9!jA7$NJ*1qMA+0Q@y{onrMU;pj@{!iKeqyEPDahk3;N}Z>i;lHqFZ>68psxI?Se{ZWh$3CU*(#qb)'
    'W@n8$^mA>`-Hz?%k8)Qp<6QmvJ>7P9>aX0<N8M+Ru+ufW{#Ki7tjqP9o~^HQ^wULub%kADrC*+A-8S2^>#Oy0=jmmAzx&H`%WjrB'
    '*4VZ0I>T(8UeCPeOg+hn%bnF0R;`Tu*)#err_QRE9glnOt##<m_MRnw_VV_0&0X&^>SwRg+G=x;YNPd|7X8J^pN%uu@7~?|q4(W%'
    'Z)MM+5B5IAx<h~M>P}`&yWX1K(5`yLrMz#vMla`fJ!zeLhutW8owIAP=)&)MdL_JZy}hDWns%%1G1{2i<g{JiecZK9U3<;^-JyFq'
    'e4?$F(`?uJ<^^dbc0Fa->GibI`dz2!=6_j(-+S>dw59K>1;_QukE<`Hd#*=ou+OxcTMO^jrnToaRal~Wsy?R-chC27xnaGibxU2g'
    '(?1oxR{eADYyR&26>eoWy@J8V9r-=l9;XgnZtQC_Efu{xJ<Hx>{`T{hANs6o>t?Th_FM8-AEK417u)@o%a3|)(YDZ!>e+HhX*Eq<'
    't?XL#L7!b;S{ZHWwde)rQod8~XzNR^ex6zBQ}46szsL8hzif>1Ln~!z!PheD?KL;rZu+e91of<VDLk0Iw_fVjp399}o7_M<RSPbj'
    'V(9B?Q%%-h{%qM@yIy}X*Xqwsf3NUW=jwg@&aM3AyOWa|W38!IEW7sX`o>2Uy+QqjwA*?kZ04b#ZGZ7;TiD4h6h3~JWqC_aZ?WOH'
    'nznG+VK=Ydhu(soMi+idPY=Wj)4I}C({AYnANFnC@0)3d=>GYz^X~6*x(WF%ZAm@I`rXcu-MkI=fcL9!qqV6wu1_sLHO_Z;TK-yk'
    'MJsPSFQuC}vuRmsqnDLWJFga#zFAq?5YG`bt!eGis{K>%@7~@oj^&^J>Hqut|Hi>}^rb7GPu{mSy^lYiTl$@<jir^ZUtdFaSndyP'
    'F+Ho^i_VU<{&Z~ByMLU``d@ndGxf&H`JvUSWqSQ`?eJ|@wVsCF+8C4T>QA&!>(%igceYQM;lg%dE3%4hr!7*}7)MXvyw`0fuQRm}'
    'xv|x3Cl{eT*7n(Y>mz?w4<g^K?{aicw$rJlQ$-)PbL^#^)<f-_A+mkf!`=7JA*%aaVRwgau<K*!+~4nd+FIJaP0mRx<JsvQ=v3X>'
    'vRBVG-}Q>zM!QFUpfhcTo&K_3i2hke#N~OHj<PcKpd07C(@q|+>Cg8$ZyRH$!(z(=ve0VUjiO&}`gU3@cp2I0edzeqBR4sv7Ir#~'
    '<i^@v`gUQa^?S8V3TMp;GkyEZu{yOn!%Rnx*3Qzlxc!-3J(^yp+{e&QwXoB(Yu#$WDwvpIhd0&zY7^`B-b2hXuRN44s*fIKqjOvq'
    '9l$;=d3Sy3I{H6(?YY8?b#ZmTEjhEh-#07Tlv5`ME_jFC);rQMfg2np*1#CNxsHSDVa9W5(XFM0)NM5t3F+qaRdvIk+2$|HndlXk'
    '9V>LUqw_<{@hrQJBIho@wse5%qw7<?6)zJ-Sq^6W?w+0eCr>Mv=TC8PMe;GaSKm$kE~kwCbn~H_?RveFWhejCem+Lk8{s|Z&DUc)'
    'B0M=ty?8xzz7%a+g<}de<prkA<eul%k|%ch9+%V99$VhCK0AF^c{+Joeev(h7TsJYbk)B(_8a;u+H^XlwHr_F3zn-qv)<`kXWLF&'
    'k5{Q3I!Z22g&*3D`bKg_;~nK3&<eV>i1j!%>~tO|${_SO`giXX+!rUqnw8^DyU}!<=q2;7o}Gd(0<ud`yY^>?my@5<i=S~CX}{}U'
    'h!wu4&~lR7)+0B4wRakw@;ubtY{&00=HU@^Nqx9?9O1N<{=Opa_-3-xt;ul>MGURK<47+^Z%-$`qLq;=Uh7x;uW<y<IA$DEDuh<V'
    'u+yx|=g6e{(0``~n_o*s-$yY`ZZk#51bv+RFGJX4H7zN9IQ@8DP0@&AG#yd8$@?zH5vCZW<EXvOypZ*dh?TTZ*NKo`p}bb87J&Rf'
    '+UYwsEk&<S$5l<=ObbjWCWp)zVaG<43)J^-B{Gwy|E)Vwn5?MbhMgjR?J8o`6;?XCiXE~X`1@78&#9Z&Z77+V`{ggrx3qQ3z{Q1~'
    '(xc9itiwey&9l?1)Uv7a+;xQ6_BYTCceegB>w{QUakTbjUQW-W<46u3=lz~l3t)2lMQ-n1PJgJ=NRgIy$8x}|SEtkLa8Ap2z4$?9'
    '+5x)bu6L?f;pK>WD0aMd(2N*Tc8h3=14Q2Dr8!!9`X^jUA1$mn7nS8zj;-5bo#-gn0jxc*zY=!ZWHQtOR;blq)WVz9#T4Q6o;Sxq'
    'p_e?gD0F1MU`ZcN*U`Dp!c98`sfTDm8~<%>Ubdb<$<U674>O%P%B|%W-=iwvJ9epB0rlrAx%%wNph%JGj4i9bwegm^qgW++2)#D~'
    'Q1)MXfTpxh-&%)94R_2-DL6#^ch3N~;f=LFm73{2<tx^sAHNwL8_xykv30(4LbvZ{2itc{-i^LlI5I70&SFlu{8@dz!H!j6?#)wh'
    '_}X21>$(^D<*?KLYwPKiC`e-6;Xk!5Im@-tO0FjzS6UWI5437qxLIuw9nKR!uyc88Uuy>x1p+Sv!;amcOhezOtrd1U7u(@nU^lLC'
    '+k7*{ND3id&Llf+fguO1FskX+-(wKmYSAhAYv1<Ko|z8IbyxAb${F?UH#_Q%ydFDItM=kEdL&K25c+5=nBLNk*GKj{v>jIDYMoS7'
    'k5N}XZYQ+VmMl$f?k$$iCLk8n4o_d9|D~(pDwLtVEMgwHc0HN$BdwXVle3rOUO*~w3=j<KMAq6MYs|N&v~PnS$OqiOg0%PL?K)>h'
    '&!=VYDMQff+v~aaMry4vRWGK!?7$y`XO-7e#ISc913DFSC-U5P=1Z14(nH+iefqqGc6B3|*8*za?df%pz3V{Nv%P~rD_F}@Z)*~-'
    'e;-X>Rg0ytVgjKe2=pmM7@DrOZQkF||32^bHmRGQqRyL3S$<nb=OoVUj*l=?RPVEgrQE}8>r*S#)?d{!zk!Pp%*tOX?2IL#U9ZoI'
    'dsoabU#g~Ejmy_R%8Q1T-j9;Es&%gjF)}Nib+gMOact$`qjya9J|bz>OFv|<`eb?q-y`U4XeHukwb|YazIXs1m@A)P0Ho>8^v#}&'
    ';+3<Pw9*M(RvwHCIOpIBS}YU!lf}Zk`i0ql9-s@DLqYV|&u??=9DF;0L`Ieh$S%LBV`V+Ff=l65Dk<vU<yLY2sW;F|cv{7{i||oC'
    'ujH#6V1HUXdYTrlOv_3ukJmd-&Bs{7&o#Y?!ZGSLE<f<|09E9nO+%=zgtNVXadZ4D?HnX5xn;pu^>8{X6kOX*w}mIyTV`W@Tf53P'
    '=~ila;k&XD;8eXSK+5qg_Rb-uQ$xS8hT~be2&LmhAo57x-sbN0HY@4h3y<&n7?X5&eJ()TO9yWOD6yIL{vhPjj{WH=CMT*csU7NY'
    'f#7|RT^z%h-`3WFHHek;IvWs{?DYSn5!yFO>T)Xr!T`54g-AXwHjy>2O-oNP_x`!HwNK;{wNmCwLfAY9SWl_R{@$|E_iapDzx=MJ'
    'kWn8)-m`t%0zWGcv4{l$_g>nqFjHPe>xDQeU4V9-UT1Oi(j%SLa}4&Zw!+VIMXr6YDCOkd{b>QLLyRC-UDFQCxjI7VMihCDPJpDK'
    'Q%B#*Q@Ja((!SM~(i?xdl#*e&BV~<ux0%6!7q^1YN+c1VjgS<mM?uT`*{+~bp`=b#-MAdVTP#h-i9%37rdU*6#}xaok+a<$i&P;P'
    '?p>jE0J5^v@~UznljU&UqVI}E<O3>&gww)K377Vr7M#{wdy9Dy^-MxxeZTx&y>R_i-P-9+;y50)+4SnQLG;J@90xEKOy&Suy`V<U'
    '0>GG)Jr2I1jk*C;aE&v7Te)2wa0+O3#qi04RZmoY<gHr(!FQ1D>rvzi<Gda6$@2X2X9WZ&JXKL}NLfO+xZbj#_$8fiKmc0z&q2zr'
    'dgF%Mn{u|3piHNl4$<dEb$!4yeKo?)u#<NvWYh|g%Z$p0;tG&Ay}1_Q@6sBj)S!<8cKc#(y%Zu=dEpxY=K7)4s+1ORNx|NW;I+$E'
    'V|Nq0gqhxv<M$035m}AG4?HG&F9JQ#n8}%>_orWtJcL(Q2v+#(w%huV^8#+Y#}Ww!%S73&KE+u(>^P;grF98Fp3G~y_Ax-awtm=='
    'mFlQ&c=nT*<FF!HFZruD*^W2U)*3tRPJh_Ju}<KpI2%2Jz8_n_kcyvHOW!}bM*OOrmtyzk0~f&j*~zgL5DuW+8g>mdLE-&SbQ}54'
    'U~9`zsr{=4;WM?LHgE*)WkxDWNeghC!b#Zab%WU{u-AbTkqUvC+&t&{&g;o%>D~%>+?;RWX(i&NHzC18v)S}y|JryHT>t&<0h^Gs'
    '7~FI|hB941MJ?Q#b~+pM;(<rx!+P3jnJXdGGxrFjl<jCg5;`k@wHbS_1E|Sk5-G$I)z(wipv~8xmm=RGEg`&KfPb-)mHo<%PEy5@'
    'cAS{<t032rpy|0c$c3V&^J;UP{-86uo*d#{Ste7=se6_48|%Bh3BFN*En2)hJ&#gvg^k)F`LoRlUm<w>zzt3>ZO)CKc`w<=wany%'
    '*ETq=KWexct;eG+Q1at)RO{SlkC%sUk*QPX0JXj+*NW3;xd1Kc`tUOH2>oU!$6sluSWpg$OO6L%>*xa+qi#BJu4$(zN1pKl*pGKq'
    '=`hlx5!UweE&1Xdt`tje`T@V%Pvi*zUbpAv3JXIAx`I@tt`A7oQ|YZ!4a<mt9W=drmb04&hU&W%2VOTbFWD*S(221C0|J&Tgr`pK'
    'b-I3!ajD=^#Kez0yVf}M4;7J;OP<6@dq^RWR?9QfLE*yQWD$m$j;ZbJQ;}d|was7uTtMfRJ92_9vj^hd7Es{@5-%n1jqF^Xo1>}i'
    '7hPz(^0{RzCpEuqb_ly~CuvErzJgPcrp|~ibhcJD4(s@=cW<Nuj^7G-YnbVv)Hc><y98e^xS;N=ODb^wx!wzBw+=22k&G_%5hlki'
    'we1^r`uN&^BvU#^V})*x6nUB|<J@O#{-!Up6?>f*g#eZ5o9PIuQSNnRN`a8xrw(hEqa6YRENJiOW5@M$8p{3ZLO?L*MqLxca02^9'
    '6<5ANr>A0Ic7V2EI;l;d2H-wktS37X5q%LL(>4-p(pd$(ENA~tKJ2dXWn~Atqre9hb5U<Q1P$+cgPcdNWb2@$nvmX1>z%JzUopXU'
    '@=*FL4cDKH1h%YFQj){BA!Wyw((lWsYqf<tqr&QP%+cCQy9EtE??qcbP}9qyr+82vsXV9-JAJOJU8(3H(=<YfK0wY-q-od@{%fla'
    'b0z{_(_7Lv(tp}ZNO{lOsIzwYz4s*~6j%lq)cdJn*2&tJ!nW?SfUO6R=3GeUT@N$rIa=HEeUG<DNwOMQvGSf4i$ES=^YCPNCn9Q!'
    'Ct7G!OJ3;cS8&1QHdl>BFAwNCv)*g$Nnekn7O2uro-L^(UytEru;dzLA1L63!4X@{l^BK2m8!?hr|3EY6bo`gad*_K*cAu&8)g*<'
    'et?~K11p%x3CK|o5bCfZfH7@_3feQ$={eZlWDxm+xhuSuqMvkSx(PXLuuHk2yd0>1T?B+wCEuIVGdVNVr;ab7U|(xcu2!!1mUlU&'
    'o`nEe4&(t1l@Oj9F7ABSEO=^R>w^v|S+Bw@JN<#S-39wnH1WPa&&0=BCqkb}p<JGO12C?ad0k$K{Hg0p<7Hm5(~S{{0<Dkr5V(#P'
    '&>GYoy=s@<Hwd9Jg`y`JH;_6I8$MPej2~gwlp#<}*kHLY)Q2&ov&yJryuGPiHq5?gJaG@s$89X)L3Z52js$nG40M#V5hW3MY070p'
    'BJcez(#1`@rcI&z`hg)p;=rvp-X2jm-$(yB+G!DkfQ;$-6i{D+QCU6OQ~m1vSu?<<1A$?H0}-Euo!%%17kq|u!$)b66O!NsZ(fg6'
    'faF*!Xw-~r<xX%@i#nL?bUx@!kuZ~7kIV|>%qY6(q#kLf!{HDoQRj{TxB)kBXd3d8JM0Mbn>-^KKt}O{Vh2@*NJeC)+tWIjoSLr3'
    'MpB^ft*zVw?5<it;I|+qilVc2atZ1uk5OBgac6uYt={^=P<=@m>Qvq2L1E@-V;S16VaKspaJ8HfVJ0{0+)0N{FPV51a$=}tb)=nh'
    'X9`rKCxcE-9CQtQ=?2>fKv<5UkOB56V=Xc<f@1BD7FM`9c_X5UI4p?xSjv~s<q<x#ZF{3ctJq#&iC40yYaHM*EwB{?64`0NX;CSb'
    '&@1TAj?$X0NF)_Jn63{-{-zg$JCm7~qI|19Xk#(9Wa$`=(i7<4gcX=%o8C|5<LV9P0~7MwcxF^9^>vhmuXhAsrhlvV&RK21l;yt_'
    'vQX<JVo##cz-4u!zXvz-2#Q)cJO{Pgw1Y-A$sBdzc+?7TscksmrKOz=4N8;u+RXp3I2&ga*kBrY|5Ib%53_*Zr4USk9$xDtGpLa|'
    'nuntQ=4s(Ha^k?sP%`npL^W^&cTH>fr5Dtb^ki@elY$4>3{n8qK)WOg4wN7I^4Fd->;~|m-j%Yk7RU?U;7}gWd!H*7CsY`%5uMxG'
    'JTJy0o#g<eveR;hkqtL6NUgX8uBwaWN=?@d_X+knU9SV{4!~@JAQ3l$J>^z3`k@~n&ko81kZgxZ_}DSF+LsugYW`Yr%u@Z;<;n+|'
    '@~f4i3%>5Uj%`B5A*j$>mamv;ci?wyZlxNQT#i)rHT3J+Jb8DU{VFFz8SgwZ!0Hwp(R_Jq<BLbVukeW7GM{JaF#`H$XIH*8Bofyz'
    'UaG>PRwO)=^QEl~q;}b5U==S$(HohQ@1{4g!j3}PhJvJ=D>JhV3yvT>FjJXbvN|OoyE&ZYOYq(%fGwd!tUH~66iVd)^(kMnLP#WE'
    'G^p^`T%Q|0C&;m~x>zXs-&Dzo7@sR{ly=QjwS!xaKmjnP2QJi3W7qZ{9Dh2x^fC61WPokvBS8+XrGwI~05B76%wR^qJ(M%)Fb3Xv'
    'EIYX>J$@yuyfx5&m~3V|aEykX(p;@OPz$zm*b%beq5z0u+iJbSro_4Si~~Bc2aJmOS@}p<1j4ho02%>xE_9yzv7MEbX@`LftOPi<'
    'MmTe|O!R#Fv%7!*CZ4??)nbQSJ0RvgTnIBoS+%i3_3@$zJWQg(H6&?LUVCdfYDWN}^ye+)DhM$a+~hOkqfxHXchi>AQ8*&Tm*>z+'
    'QgE@umnp`-11JvK!z*^M2$c0)GS52W<yC65iokUl1r3piYBj=cPz+FJngR55J}cicynxQ}#$h}7yXo{m(Fy*jq{lvUdfCYB$9Fc$'
    'QG$Bnd|Q3wvIBY#UQcTJIY*s$ggw;v`mh~^6GFtPg+Fpb>O}#bk$bnGgH5Q!Y+TZnkxtZQ=1Xv0&+``pkE;Et7d7|iR_b<%UXj#e'
    'jcG3tMO35Oc{M2JoYjw|{_H0B9MB@1`iy3v#w%DVJ|~|YTbuliAbUj+1=)B(Ins}}5!chHEO%Dm1I(}k*MfJr0ixgAqryS_PW&Iv'
    '_WW1?Z;cu^b-Q?4y(oQHVz_<7j&-sq9%#Sq_q(`u@>iXZJDx);2xh#ZFqV0JAA@*wLci3ZpFdk+{PWDvZbp1u$cEY&`upL#sWUYQ'
    '!5m<%-E_*@xDfvp$mip-DtM>V0OCX|z#Aq*jaUQ@eIIij5=S`YWqxL(=+Ztj`!f9i2yu|}w8kid@60YX?E+e_a3%EuYaD2+xTioa'
    'BSKJ$M{?<Seu^jW+g@(A5gqCSWSmbZ4{Mkng!<OXCSN5E){8lR$Q$I%Ns^UYy>CVt1pYX%XQm<Y4aAW5k*?k+)9!aMs%G}PAi?YQ'
    '8=S}!<V^i*SYtrxtz_;)eq?xA8DFftL1P3(L8#Fu?0~XxUz7vh_6C-hgDha0HB&vsS=tZ~#Y^vD=44~NP$$d?bG5&(+0L;(50!o5'
    '^4ZqUjIb&nnxO0E-0>8P@)SoiiFRg~)7T?$&xw7(YNfb9HZ&8TVQ+H6UK5Aj0#zuW=tygRMH!vURtpT^;c$@T!lR*p`X7~+%#^hY'
    '`BS~=(<9&CEEO0`HG>s!934QcV*sD$MLDOJ3reScxDdQ`AZg|MBWkSxR_uBmOzo}@w>k>(aMtw%JV@bNt4vY7&YQfR`4a@4VADIi'
    'yk3YbImK4u44`ww0}8(bwg5k$a(J6CY=)UB;S_iF4%C8!U>f_rQIQ4RxD+Yjik+1{p6C~BhiX)!ejM*w#55P&8!leQCS-I{q6Gc)'
    's{oCl5+$7NbVo*~VI(lR20qGGqkMW=t|?F~>i5)|0zNuK;ZQT6o<FnU?hzOqE4H^1I~p%wg0MBhPD_p=l-%XG30e)95O=${e!lBL'
    'xxAnPC+(U&%_EM--DwMK&};pCcv=8h7kLzj$~C{sQNK_$gs(0iK&%BzM+cDE3kTTpn~LlqMSn@AI~Sm(!-zOLcE+YF1dx_LI$5yM'
    '{?_FO^quhB+H$b2;JF0Uq=*Qhu#nn7SbiI$ux44;T5*X>lfw}XUpS+0rSO-uc;I%<d<q@##S!bQy9Q&PO4X#9A%P~iFAi}iBail$'
    'F+BisAN;+&&UZOe`_`iizWU0>N9pvpd-+gv`F#SUmJ9^SSFn=@-!`l&@v8Q=JXo4dideuHEbxHzHvt@V50dKSA9OM{GO8A=P|~i3'
    'E24d2#N{AmQLUqu<7SDVMzhHwYkMo;z_BE}lrMd#75M!C1%ib#%g*xxQbGfIx<4x&4(cH>(UcMq67(?nC^>_Zg+j;>mkbm5YQ{+b'
    'aZVQl_Q~=}a}8N<UOyYV8_p(a(ps^9DBF_nyTsjU&j<-FkzP}>nl^F0;wp+k*&Cq!#R1nZ?4OerWw=55s*vj=y3~oUR8s4o1(XHq'
    'QQY&=q0z_X4nY;ASOse{3*Ltgf=wIDI(badAP5UU&(On8OHfYCeCZkCAO+S2|GLX#W_e#RpB5R-Ra)P%8EMnf3xV?4vLL^?6{35v'
    '#&?`iVr~@Xbj_M(CRWgqLD&?VQ8x;jMvXgvRw>qjcv(n}BlYgxU>RLV^WzIB+@e;6KaS+K5*CozT=-34HzDfDi)sh19kITCk9I$>'
    '`h1E`Ond3-I#CgWKybk0D>+Y?5%cOTDTIZ5`89OtuQp=Gnj8up?gS-+iq4I7Tp%Wq72G7WOuR2aDO+ZS<DNv;Y~s_RBT#n6t`$u*'
    '%tpo_ykS~sZ<Gngj|(~nS8mc!6pN*BUdXAm=*=sj+-^LDV3TV~7pAH#XH=uesw2Ld9|D7CtX!ht`wdSR3x2SBAiGjd9FaKC1kzws'
    'o$#}z>*jXxDy4+=J%moc!>264X6dl#@le13W#r}tDbSjLm!0e#;KHpfixY^C0jrm#%o%s`cc1IvQ}Vd)qk+WeW{jFAYsfqu$WA3n'
    'E0vQ6QZ?c9NGk=h@F^8l+-C;HNFi3AaRf!G|Ik?nE<fRI&Imu|F~MWeu@z=qg_kgiF(a6PDKi^o*PE{d1_;!&%IA2MQ?eQ2(y@~|'
    'sNjS8z21->HHuASOETJq<&zptTwOWZDYHg|cPZcXV^YRX)|jcehAbk4q9p?Q+C3jBSj&<=2C(dRbL0$)yMXreu~t$-A<Mu>0Tu}#'
    'O9>UO{e-}lMATPau4dKth>tsUcryUzPu^uUNY~v86U%8kg{4*Hk-X@?aDhmRNBiRDmVioKwhyXo=phW|^>JjzA|Cz<0M+%o8lAv8'
    'Ovu9LU0?P~KO8{F%GMPsh7%4RuzzO1os<S-XMBxh`U23Rbqwg#54TMxL;<^h8`gbuRAC2@v@zu3=43fg*w+w+!%Ti2r>zreuFSV+'
    'F4i03>|WW1N2bB)zTvIBouh@WI|f+XHM{@xW0NM~=4Q(GX)oncnoWr;!>+(o1}mLJ15qNRVX)9fbfa4j-1`uX9B6)Tu@g_gEaMZ_'
    '9%hHOqCGH9pRFZAw~<myDA{R8|1+GA{#8vk5x-&)h)FlEx1ouWbB<Di#d+wghW{BX#AgP%7dG3hvB~sNs0Px+6#YDgb|&Yi!i8QR'
    '?SSOF&;?}TO4>nO<3ys5xxPlSLyI46xOYTj8oo%60H+U5#=G8v(#VQ{_?FkZ{DVpA)#Q74RSSsrLW*3`mIUPk&Xe}C)@Ydl!Gmi-'
    'y}sFqhubRbJ8d#WTMsd9wA(3E1-j|Erf9^Z-xof6d)LFSxpHVWPuMAB84wcm8t+5?L1nbu>5{8oBP)eupbaXCaXG5jCQP4K(Rq!m'
    ')oVjX{A<LNnXKSs>0Eu}4sQ%j4{qdg20uH9C=l?*x!*pk)MPqw{<+DQhT81hROj-yAMq0KTEm522+4A&G)7Y>$v)A>$qlBo??aJ?'
    'kzfk$BOA`3?GTU*faTyYK#|xuWg0QlS&*XWW9U>F??ZG8C=k(uET&6oWGP&Lh$%i8%?y)nj`KDDDX^Q|GT>|2K?pHbfu4`N-r-(N'
    'C7U}b-!O!ArTaQ?Y_+Ocy}0eS=;(ZOJMDeoLRhh4<#lVeIRaqPG^AC~%KUzFAfC~Q{DSXYEWJR#)=#rd3jjccLWmN4Zzx4(Z0Swq'
    '``xfZC<7>%Ia&OtK}WARdlDgr;9DoiRB*zzqKUC7gnhk>(D#W_N&Fv?1oVpPDTmhANsMoHgi6bO@ZuCd(^5ts-5$A+T*sxovIdV$'
    'kM#6N2n_enMrUB9M%&y>JKA(#+^KCN!&ft>=t*z$=&xKt!*B-)ThRVL7?M+qmaK7JH*AHq!22N5PBW<P3bE*nNhbzqL7UFtDC-H5'
    'vK^?5>#!KX^e$lTW<Aa{gF?+x8t`yVbh*OwG8_;AiVN$zo8t{xC#y6Qz9-0g|H^s5$<*ZJ5^ijMy<kZ5dfcx}S2>xW?V9QHijq(z'
    '7qE5`wqQZJiJY^1wUBV2{L$PwU$fLm>9X*c{%o&8!-k<DfDXByc7tMjn<jBY!Bp>;cnYDF^_3cZMrwUVPmp$Bqj1|kmZdM&2r}f^'
    '&We5-Xm9#{kWG^`BfAC<{`!3HJ$jZD5G_0~K~UH|?FOBw<pjakP7r=tgNv4ComZ!{t(2M#I>e@j&hqva`+IddzrjW1!A6h+I<X^_'
    'vQoaEWrfh`u9J6$FawoQIvQw(yLmmLCqwKk<Qd8^v~C`BP0mcvU5*|WG;E6%%}74z3U$=zSz_63xOy7`kkuC41LXxvTViWzN9!Ia'
    'Tn7vcJ~O4(4LJr9X|8t4dk|nCHDq@abyl}M&YQ~}N)t>IdfEC2-ZL5m#2re)XTab0l42+>fW{S#OE5+0r7a<AVRW8mBsw#1sAK@M'
    'c2n_YvQ4%T2~NNT8n~ieu34I+QN3&l&g0u4>_<->@V&k(44K^%Bd2ehlNFj(bTm*$I#h{p0*TDiTt6L-MkgQbKL*w&h*To;q+xUc'
    '$!WbaeVJ)(_EXYtNaLtE;w$Iq!L3r34M7tmFn^TRV7J7PYCI=~N`+D>f`_aIxVH#CseUM!e+%va0W5u_^<zSrl}GPX3#tJTHl+%e'
    'tUksR-3tWgV4v?SQIMzQMsMG(`KS%T^8jC`!|^%d?S{DXx~I~vy9J+m@dzByt*8|9!Ql7L$3U-Q@vFhrbN^a#CUe3Q8ykYJ*<Csd'
    'xZP<t8K#`*_*wkeG}}=E=r0!U1hJ&V5WUijbnO7s^{;M3%nUbANpL{C>xYkUfEwVP;0iyKg{2aN9y7@lFX>`5&L<yoI!t{0wY<G;'
    'R_X>Yinj;8PXtJrJ9akoh~rSI0V2HH1Btmr&Y;aB3rs|Mg|cgznNrw|LrOzRAoqk04jRbl=#Q5|_C)U(M7f&vFO(@>NvKDyVuE)n'
    'w1ew%za6VRa>+jx8r0yt6TOl-Xxp}TXamT&X+ryd-NajQv4pT_ek5Lm2G1~p@bnt|S^#k<@z#VEC#U;z1){a6Ra`d=H+*t}MS6eG'
    'VAu!A0tY&!MnLM7W^~5tI*WMZq!bHFnE-1BO;mQEN0q|$d3>|?tDPDVq|=p<*G8=5LQA|Yi|T-kv|5aWmM8ieazmWIT3NC1aESVU'
    ';)hp`roCuUSb<P_A_asKP{@DJtqCgvp`#y17i~Zkuz8T^;fVR{rb)LPDEHL@0CQ>A>zp%D(J(MXLpSw`o+=@OMs-+p@FZKJt#oe@'
    'IvcF9-G)W1Q?Eg|`Ow=Afd??IyIskhZ5(07Aa^tng3}!OgWUEUed&-}$blzyv%KDcI4!r0cbJcE!bcl4R@bveHX>OsK}&o%V|>Rz'
    'qmDHEc@u9hFpM2<&S(jvdClr6ZdgjQVFnVc!#Iwgzz#hQ31+%t&4EYDZ%y$vK$>n4G#ev;+{#ldSV1|}FDdE-^nuHtPe5I+n5q+9'
    '(2K_Z4(|ydFJB0(G_7iU?@IdOg7wnf4p-9-RiEv?rjhN^pc+0a$M>sxVQxkssfeZ=oc|(H0^-k~U1%6_v~w<IlXh{Tdn28Z-+}rI'
    '5@iGtLBrkdmu;x<?GNP#d!*D<kq3;p2=LuW>za8v6!}PY0X@GSzJ{EL+ikxtIq(RpN|o<1;8s%2X(U@Ww*?prazgio_k6TQODXXz'
    'MCK13pXl#haKj)IE3eUF2SnW?!FD`zg`XgYlzJ_s6cG9Ey(4`EnG4cR@}Dc@1}J)&_h#jZbUg^~RWn6*$k;&tEkkDv6oqu3j$7#m'
    'C!BwrE}SmwADC*V_cW1%Qv56R0%Xv-vwiR<gpR79j6ec=4VZ;)DGsQWuNb*WfMG564kPY)3ib_ug0IgWPSRLvAC&bXt85lQ=#+H7'
    's}=gMX(VfLK5e&26e7|4(+p`A2*EdsGOVx;FJ#cznt;4A09ZSq{3Du~Kv*g$Dy_%=ZT+)uxh2X>i)0GL%RdWu_8;^-kuDbG4zeX#'
    'C+#|h42e_zB;48DkcP{lG#`pfn9{QhE9-&avfF%LxDce7k=yDOAsGbf`I1rD9db^{k-L4MfZ;XQOIC8v_G7-91`{3S4YzkH9VN*F'
    'RE%%!fcl8)m|0_jZA3{Y%$l)&YnUaU75Jmmg|Y$AKYldLu=h{{3Or>vm>i~ue|FQ&r44pd4>0mCuLtRe%!@vz=&&BeLJsC!=TjVB'
    'Q?ts;9>0HBx5OzV(tC5?r(d1ULiZYu_R$I}N^Bj(|3nKRrE^jnnzh&ZD98l2m%3lO(eOp>pcB?0Hko#$il|pnG=0kzWFH;?9P^p<'
    'Lv|~@fykajO+_99?={@Ul+<VTy_sx^P9i#MZX1AM(>{hYTj7w|()E}9DrgaKP?m9jdo>+3@QC5iC!dv@1Fz5`pEb*oR5A;#aHr*)'
    'YxH@`K`aW`(aP6gZlk}{eljh8d3A&)XeANnu99!g&5F&sc2@Z*4zN)}n#ND=?>;Pbb<i2KWwq|o4vHY{RKO*{D4a->Yy`cCMRM6W'
    'CZ^3ro;^5r6hWyWC?4y-Tg7Oll9_5(bA%;{7U4}`Q`5Is&|J*#fhzTJa(~%mzqy<n!8vbRwVb3GfY(C6fSITN#s%=Oa13d9D=AQl'
    '^wE>CEM&a<cP~%=sY1nMC60Jll2a%+RB2y15_i{-FLsA#a_4^iv<*NZ%3C-4r1&+ZCnmYxkNA9eQleA()g#>RoWhGntXHPP4i^c&'
    'aWm@v<0{UZ(^^H^5P6)DO<X@UR)2cWF_E&-yYDm5O&WYa&I$^mpPAu$(B1P6Nr3%k2`L>TWz_FsX(^s2_C+<HMqG4t2>BGR{5KD*'
    'X7mFk9%xWq(dmCt?4)-DLN9!k$FXv&B{IMqHp8&`9}g^guoOfRtlVQL)?B@7b%gB#auE1vD<s(g&2X@$gBd0><PK2f1TspqdeDH5'
    'c-{>htD{Y)wmnmE<gOY8dpPViQ}}8rqC=Z;k{acNFZ-1;<NMVKTF-VhSvKt;8B;>0Wo^C3o@kLYr0~l4c|8#CMjO&=Uy-Y$Ue7V8'
    'oBJMOQz%s~X_sfS>aJ~*<3G@*&<#R930wNzU7<6Krc-LWC*K|G>bi-l7(eX*%J8YnV&SA6|4jUVFlu>r0Bp*`XlhzLNtYHkBAl|i'
    'mhE<R2OnLC`y*#AgfBrnrupsNyA>iK4N@(C6_|g*R5!+8JJg>*WNGYL*{lZ*6+wbVacez0_W>z#+H~!O9k|~>r-~M^u&c78hXQ1^'
    'CM9$^@H!~cq+LU!hvWfpI4F`AA|*VAVG<%{v<9Fd;S)cZo*NhfNC}+wJ+87Jpgg4jYbPU=estI3*rGjN9+HOi7*keF1}Ej8Yk#-m'
    'Q#f$$rv4;<leQsfEH0TmyX*FIq=m@$!j7~C0;XkV-@>Cl!=Z}yWGv+I!>V16RBV|h4o@1skx7MfmuA|8;H;Hyknz^>M8lV0i8hMw'
    'ayZ@QqI|4SLP^-9P$*XZth2w1&_#7OJMVL%LIDL)(alafN+a|mml<Z;8bx&7$}~S2UcJG~gW>&rMI-&A5YqQ&W;IAF$rW!#tqIhH'
    'p#p;3?(fSY7jDa^gg)8t@W>!htebW~uc$;L?$Msv#hsAq+@CGrmk_nNdhYyxTHLp~nWJTOhyJo*%t1Hw^fu_FyR<9A*NhG!{t!U@'
    'l2MKEI@7>%727s^=u84MClz-GT4E*diIkwf7k$7hcZCr~;!jG8CvI=SUPg|m=4OOi3}xaNu)&DrNO8iVjWd6A6Liwh1tH<x9O|WV'
    'ScT81tNk}mqP<vJ5J25`tW)lf2a&!X*u#0UKJ`)GsMAb;8v6IopARCf6}@oEy2qg7e&`bZ!7U63y}Hu7yIZp4HRz?AfxCNp0M*{d'
    'bI0nKX$?D}MMrZ1(p+XllvgL+4(i;6QlVr8Uje<ofx-m62VvKo%F|t~CHj&CTB0~N`V%m(o33#kCUOptQ6kJa1;ID=(0y!f?4TXV'
    'chPq6(YYzULnk3qoMBfdm^ls2rG9j7O0mjVo;rs-7rwtxtDtb0Y;Ket2YmLRQtWCBR?Y`x@+X;w=!lNrM=#kBn<(H+D+UEO2SA%f'
    ')e{oznC)R{TY5EX5;WNq5CUL0->@Uu*z|w`&j+g-*<G}|AhOi31D1q-K_6idG{N4NNi4(?*ewK?IV_+h=({F~4~+<Pf6D6v#t!WY'
    '2yv(hCsB%~S18`#AtUSvHEFh;kEIW<X*|a7y-#HZD{HRssVGREVAMhk1w^}V2851<A4sUuas;hsCPSBxxJ?cpX}6I-Cr4`0A2O}7'
    'xh#&f!e~-gybq{5D=21Q%8=%XJHrmh#<VLsX@ZW7PL+;P<j>xYSY)-dqAHYv+?qn##u_11-uzjps1_70uOj?7fdG)jWs_$|NV{2u'
    'bcjUf4@DCO8h|jr1+eIjm?TX&)09&w29}tY(&Hi6Ca&r?*itJHZ4gtiwh-jSjQ$?vBNsJ-fJ0jGBokt%dp<h=Nos%h3E;q<hR?(l'
    'gY~3L{j&{`TDKgZdPCW7A+onocA0s-Lu~bg&sWs&DCSJdmG|$JSoWOcpP=~R;{)~eb1XuhZ}^o*5lt8?kh|sNmw63uTVr-#fZX6P'
    'Jx9kfL3anCw_Ef3H;dR<)H>)p2&ojefg`dRc4X-!oc*WnTW5xVrJ(VFxrnR#FkwW58O>qzF6<d|N7xh1m@z)~q?{W#ezV#UdP`wP'
    'EzLQC_C*Ltx%j{fcF$;d01z{1%ABS#HUauH(sjuFJjx0l1sz7b+vri8M+BqLd~Y6C`Y}&jSkU<H%F#2tCikb#M>51K)=NHs66!6V'
    'P60RtSwTtXIm|->U|F9Q8jW?XkJL9K!oHY70~rP=U}~lvYl&##ttXPd(d4Di5lNkrW-fA?xB1hI{WQR{TiYr8hIl^_6OupQfkMcH'
    'x8D)_Sg3khLg_@aD0Y?+9G1IWDOAlFP%S3k@`!bKr)A2_ihL<(C?M2Fr$^eM_b?xLctdOKSZ5S2=Y39AW(d*|bj=&_AX;OCgOPmf'
    'LE6|^T?P6)e8kY@xQK#LUklG8vrV4Fs22qBa-}r4w(_}Wh5%HWp!@Kw$sZ~1XhIyUjQ4Hbf7}qOK4XMrQT50HBwt%es|r`Cuy<A#'
    'p-||M`_RQkaPwqmU0Cj|gd$L3zzA%77dy^pcP;6+z%ipI+k*-SJXnDz?7BY!C@YNgM{Yn<LSJ^dMjdv8$tSoUJY19)HqquWU*MgL'
    'vO_baTF8<hJ4VmopHZ#BL8cu&84QP_Z!g#qjAww%7A>2Y5fwmYAIRQ>_n{VgoY>w77|0VgVqyH%x<YdS0+F`bF~2YDE>eeD_EbQ='
    'kpPY}Q2%*Mvu%;cVHy|5Vc2=H5sSTyh_uK6DxEQOp0?<u2cPBh7qsI~*um~HmxZ+vcLy`h5-zcQ=!ztp?(n68i%7dsMQ)CPKkr8k'
    's8J1N=*6j_l||byDFtFoVP?J`y;~><g|<~a=G|D`DlfMQ_}o|omm##WETiL=&)8;%cC~F8e`1{H1Sqe&VM{)#tgu6KQVARJ;cY1}'
    'KZ&zx?tGnY*exP75<;36@^@jfyO_D+9m7dPN`SUOyzqNoW%acBE!4H!XLsoi8V&%%4ali*YU1+ucfE$_AgC=OEzb{F5(Qv5$D7E`'
    '7&C>Sg%)E}a*d(VSNuBXe7$3T&dTbs!L5rV-*6}ey!XQ367+}wbvPDNE7Y{*VP%i7gZJ3plJEKcc$+XhAz|#WW6q5H(6qEo=wc4f'
    'l!4^^AT#XHuA30Q&TA3DE5oZM>c&yq?r=i#sv7Z@1!L{xc~j^+l_v>~T>}WE9_;}xd1zGA=<kZ}c8JYsy8{p1PqWb~THPF`n3h2z'
    '2c(Zi77=Wo8K{;(1RD_|9rOjP2YKlE%p(Jk%U#LmjT$+W<Z+8U)yuwFdn{$L)czV-G2^4c)u$D5rrw-K&oGtgiE(15Gp@7CI1?gj'
    'IFu#O79K5_(6Y16BhCw;EGqCQ+kk$e6L->%^0PjXL+_Z*)=)~KE4{y7aO{Rf9!QHE{Swr0C;^!hwbnEP79j3MMJzOLUFAX8{6<{s'
    '%ej%nBPnK-nmNiVU}w!AB`+nayKr+}WCq*N{ir+N2(2GviQpq^L^+z1?84{kBR_-%s+K*-3N5dW;%zA=K0U9Z@5-bXM`}3G&x0c6'
    'wP@oEE3<LPh}H~69qIxHssD@SU@UdAO6GW=IvIl7X5gVF0?9q?fJHr4jO_P8?UYcc3M`mzEw@;uPaWdy&X&#XiBsqxAodt`j0#yG'
    'X<M0RP@#rrU36v~jogZ(y#Wfuu|0Y^kP765ljx=y8WgUB*AbFB4b1DH;?-lojW4&~jIz~tOI8x}gL0_bx9{#QACOmEQ=mt_lu`+x'
    '&&-E~2-!&Ach=RJIKrq8G=+Y?6x{}Ti7iF?;Jms{J7cU8Z<y*9ISkNWl<w#<Y0%;7%ojo>z`CC#jZu&(`>7z99QFAo^k9(pp;at+'
    'Rb*rcng*c{J1v^U#6l3nq>yn;Ttcn+^dZBWa1heQIzwPp|9FwoMX_b(YNucXyvw|_s8kQ6lN2%0DV6TzqHM=Gdjeh{fg8<m0OgO|'
    'VKf+<s7L897~N<x!j-5aoEVt|v`GhWPfU~)4q5C%J9caern?N-Erg~u+cd6)O6U-3Coe}rLuaFQ=Nuuwha)H+3=uoK!CixqjU-c!'
    '#{=1g+{2WCb;1tP5=}hlV};$cn9M{0>6Ku#mVY2oHGnkecMg9tX(UFT9@WmUlMlmPb#sJbKHjE@xzpSB_Rb+J$8kcZCR&L^?_rr#'
    '`rq9tj)quH0Sgo+=1aWJYwE`F?x<P;v(j8ewJ`<~k*rgvEzxpthSe8}$r$4X8=6?cdX8f~I9JE~56X<oty%QDexpc{eA1qZMDH+h'
    'QJ<&~sppvpGmzSFq1%3h8FL9Ir78q|PikJ%i3|1<ejR~BKP{)*oS6<T4{RB6)<F&=;IM>kUn`SA>c`yNn_7e2fcGiCF)U&7Q^*ev'
    '4e~N4?963Hv<wlfyk4uuQWXQdUXp_x7odR&yiY@&ll_el;_+hLQGsQI2QU7H93euz$kJQVXNDOwi@Mv(`WIGSMCK1oHqojjJ6?Dr'
    '|D8QXcu*T&%)<aH3#)BeCo)*F?02x6wQi@dX8tMy7R4Nl*Y{&89MGY=SR)8L+mqTz1J>SgU{jz&8wP^J`&ENq*7{xc0LlA179jC<'
    'Nju7to_F<;;nChjJ$-t3SK1MrIAvTZTv_}Yai=|lEFd8tPY8dy!P0`j)>?6er{<@)^f`c7gBP9@)-3C})7ihbf{uZQmzA<JxkN7$'
    'v9uc4;qf>{Rt}(D@ar2c3!VxBYWebz%AZDUOAHp6U{ceqbFGGz!*%>1m7qxR48M|UkvZqO^W;Ky4}6cv-H^mYGH>L^p!1$cfvDpx'
    'JnZ1}0V%R&zkLCiTo`0?OH4r`lCk^_qe8-rMn_K+f`l4BJK!UG5bu*I!46?XG<0YI?=u1(BktFHgPPkGFqo;kHxkPW(VzK#RNKDI'
    '4Q9tUBZfUDI(Hvu4jJhCIe~#vm3wYV47pnrC97w{_47FaPtyV0=%HGMh6<Aekxnk39ho+OA_TIxLKUmf*||L=?|XO1|6K07CxI25'
    'jCwly6YIMixS^MB#^cBX5qj%ntS!IoU<Mt!0&uRMcV8f<j30Ul9$(@ha9rGX9J7tAZOW8UM)BkuChzc4JUJ4myPt_XdgaCBHX4oi'
    '%c7KDdkxj*mL-=1-+)kp!j4X^@Dr%rPed;XeZpfiRDz-o9Ma^>T8#%D?hbrWb{lSo=lP+b|DN;$BBHR-19j)1@R(rp2xgvlMDdn7'
    '8)xVBplBnI)tEN-9+xU5p9-I_!>m2M=>}6ijypR1AnqWO9u5W4r005DxH5j0Gx(wbaPN1@GB*WLBDf?W_;(SWS1i^%PbN=e5?*T1'
    '(7)cQ^Na!rB4}FH?{HsG(wj4Z3{imO+))-y%!k_d0IG!T+~RkcYsTCnV4jC<A1GW9Kwwwn<R6n9_6D?BhGCp9_LydV<F><YINo_m'
    'uP<=N4h(Wpj#8lenobFoIm^b%Fc6+ZhyBMp?ono-<FH51@)sFF8Zi}RwJ>8UC#syTe5cv6%$_sh5>YCmcC=j}-~R<<%TqoXxq<TT'
    'tAaov#_5$WMu8{Ec|qS1rIjEeF@A2ris|L&TVb-9q7Utjn!F}DL#taB@@c&kEeSox$HV0Sr8)dONeO>6#$^;{4)@@~Qk+203u5mp'
    'TCxUcOVM+nD_KKv3oqod&z-sSI_tvfSF5g1y_7l68!%*kOAr5g+>miUZ4~z-xpj5slA`GrRd5FMd<`I!caTb1EmtT78~4gMod|{*'
    'iaOgo(2N!tQ^T&RxAbfiflN)fac}*CMc3Qi+_1md18@_V9Xh^X5oSR#n_$GFqMu``A9RQ>TI?2h-AERvTsxU2dJG6Zrf)9@L1{sP'
    'GKW~1X#>YGz<${5S?0em;DJq<-CftE0@!XDk1=h?a@c&J8{M-|S_dabk9V>yWdU+SHTx}Mry1QHnl}RNjcg_89~{l#7{fQHRuK&u'
    'Ek`m|1B4e!=gHfO+d+^~u2?3h7En0e)^Lw0NfUK>AQZCxjG!L+jYvW8AMX!TbT4AsOmpaAhYm&=PZm966b=e&a`#wuJQ|>OB|=V='
    '9C@$-dx6HN{8@TGkkgx#{h~GH5*R=BPkTR$Xn~JiODYFCf7nUn?$k_H*wN>C2609kF<+I2YTP6olbUwWrdd-5#}H%xP;Z75hL?Y>'
    '>?mEEV8rMY{n$Hxcv9LO>!%d(#>0Vu>z?uuB{*}fJnKvsv9b&A(t^4<HKqdyBi2k8wC%WO_>LT{(cz19`teLQQ`c|US;4-dKCsOo'
    'wsbm-3atqfy2EZ#E~n)MG4`-S!XDI=L0v8E7;nhckhr;-Z&6gG<8|Ip$8af7r_^xU^!ZXQhMF)7zJ!hnnK}L*UV1Z&B~q@<yf7Lh'
    '(he96QH5&tmxNLQ-B^36Kft&R=JTQ_vprcn20poB!D#c>m+!^|6QLp5^vt>71_E275D|8W7ZnbSJ4>dk)$nq$ELvU<A~Y@O5Rhlc'
    'tk>bu!yZz&!wv|7Vja4xF}<TOVxFGxF~7?#i*fVzY82|U01U!GaO)$?;1JWS>`~pJv+gEs%5>q9F+-lyav41)&$8q3Zw<=aNwZ_*'
    '2r=|*+cDB`-uS7{%+uVUlZ^OHDDdbHKysL$S+~SRJ624O4T+-JfTZ?#^?uZiJoB3_QKB3Ua!Q7v(Ej@pG&nJf3B|71;E*&N{kb_k'
    '>}U*N_Th!V`}_*ZG6jlXu(>g75VtRbmuf0DQ^`DT-LCapCUA3*lRTlw!Q3r|j7_9Ua&^KXf}h9t54h@}Uc*$7N*hJ4Vk%Gg%+P{?'
    'M#C>WF`aM%2I6&o(7{SQGxS0@E-5Q<3WuEoZrs>rLx;o%?E_HI?h}W_sjzcU?Q`F2aJ8x>7bnq0O&<z+iQE}j`3lV##Ae8(_`Wsl'
    'z^)(?w$SW8p15ejz^Wmo#O0tMyM)nVFpsBPEymK63_<x-zyOAR=|9oWaSaJgXTdY<XnGuo7`%02z!IXlLVY^E(u(dIo!hV#g5XX^'
    'H6&6>(1EAw`%obu8$NF`#v4HIVP71s0Yso%@3e%G_AAHP;}fkhI9pBs4)6nasE*fx=+0+%c)DRWKLv;rGu2V@9~qP}QqCjG`uRTD'
    'Ab=)JT@hHAAAoQQMY<Yhu>YFxudVinpzQb#Q~3n6*W*IaZ(0$7at9vdYq^d*R$#@VxB-1Jg0~ArAI-j!?i1As!dLdt%7CkZaZ(03'
    'G3*JuaZT$&Gq?r1-4TRySK7=KT1^m!fsICLhQ9cX;~ZnOJoYZCFQ9B^to&%(d=-0-?@$4$U{Yld@srIu0Xjk6Fn6s#EJT2@X7tEI'
    'v*rA7&ro`lLN_oP>m?LisBUlInixan1K=XKMu#+_uWwV#H_w#xZ0^r{;uoOce0)eayF?54*cS}m@uR*De?D!DY-U{orFrh*2r~dX'
    'MODK@uE1s%4QE6Z`=O~9<v{vOct^VDK%y0uBL1`;4~O0KY-%W$Z3RejEGwk<hRpU&J9hA5Zfe^xSLQr1=j&2j3%iATg&{#I8P`Kw'
    '240HAd&3TD4nN}or7y@s;SOC?lH{Fc`YQbNV&+N6-Gg8OcEeiB+oO)bSWUeC2qAk*UE*eY%IR=DGqtOyb;RgtVsxZ%V>+A7778Jx'
    'mhC~M1^p&QQKLt9Mm`1oQqUXV_9g751&r&U6LH5kqxF}NYL#1}%bOR@z)^6f{Imd{yi8_DhDef`Pv}5XXqdTDfEyXu#MIw#$8?LL'
    'SVHiT2Q5!FUCt~~db_5RF$!d*{8^_pgRxqO#f*^?8Bhf8Zn>K0JM-K)jRxw79wE4d9>hlTK%RL@n<|A{R26?t-ed5Fwc%Enfdy=^'
    'ci_<&dO@X-4rw}qGN45w2q8dI0JCq3DKgX~Zd3-Z!DmlQC5#TyN<AaReVWWqPY+d$AUiV|q4`SPP9ZWVWv}Uwq3Y8h<!RZ`bmrDl'
    '-m|>TNe9nXzNo?S*dcETJ$b@JyCYA%OGFMw9tKP>UZDt0yO69QTzco2Ug=C`e>_{D?1ReI$b1EC8U_#`VoRc})twle)ABfjA~+!%'
    'z|DD2ftmz*S8!)`W?e+!BqBP#qIC`uv=u;Z4R8}--DTm*r*9QX?3ApgRU})Y{#30oJ0Wts=%)8zCR7Y&&D7BY8lSY;N(p8PYflEP'
    'q#auF#peyebvfbCt)3|E-mfG9cXlJk2v0qfD;cvv5pK^9eW#{ke@r(=44Xt`s+yzQdnWSkx2DR)whRS9RO=9DLm@URE9N~MDAYZq'
    '_n>Mq-?@bFhRx`aWs)d;N)aF78mwY+>&ko|!Wj)340ky(+YBDWbxr<$KPwCHiTXB3=pYUx`kd?a1ZpYBqH@fn;ZR?sq{7@iYT*e;'
    '*O$s{q)UTEePNG7dUzwHjl3YTKx{#qMQCeNpyVEYR_P!PUX$5p2#GIRJ&s#0@BARuJ0AD;j^Ja{TE<v$noLhtBu#U&w$186QCCU@'
    'K*wzLH=f!6*fzV}15-*;-XSeB{Flrj@w6w-!E#Iq(e4@m<GK6#P)5|~U{6wZA3ybN-97gQv~PM!*>Q>U(|u+r^F~vlwzTtfMn>1y'
    'pMy3yWl$ZtJt0OyC-h(#0M~Pl#qjVdL^W2HxRLA{E^o~iOnbyQJ&m&6{1i$-yq3^HMl>k=B2x~~i5y>v8^8gsC~)yf0cQAtki}6}'
    '4Lhq<QV!Me7N-RVEGk1rZf{oV4S17uv*{!5rCAu^0)+Up@ZaEb*au{ThZTH411w;gJOWlZyoNqgQiqv03=^hrCs|3Ba3K)3q-)Sz'
    'hCynQ+*ksPo*dvA=-sana$#O9M=+8KEolyHMMj^3)TazP#C>aA%^pA_6(i<Efhx@}E+>~O<a>baVK<#1FB+QP-nPIe!}6F9bWbwL'
    'I%Jv&Air~KFf-Z3Q2KepjB?Ip;jY)U#>Zt^#03?(L6A4;gmV#ecRYu;Jhv0<jUcmp9F|3|B&7jJ{W(woC3-x1B&_gj3LU^Cp?Ami'
    'h9^R!%cKJ`uLpQMX?SK->-i=Mz=wh+{ZOlY-k52N-7{4xuIF=mo9n*AjsY*klVn+;>3h0$>R{}w<V9M1?^>7G@_KFvfky-e0wXi*'
    'n4dvLO%HDL<^VokQYUl|l0Qj0jM$pv{rDL8Qvj<QK{xctiUWDaMI7CPRNX4SJLm+P8g_Z3Jp0I@zO;`b-9+of`&FVfDwo;_d*0Nz'
    'YK(xe5?K)BQNlqx!+`U?+4|H#c$pPB%6GYjOeq1!iOW%|2VEQB^z*x%C-O`)C8FVqLaWD~j)#Ew<_=@FQ3-cnWqFS^o}ktJz8E+h'
    'a?cFIIl)h(;^uKHI>Yl*5RxAT_S}{mlJVFCubvzGeKNWLDQVs4x^jC3xYNsFlgfG+TG$bFI@#(msG{KBlI*~OCx6lF<Ac9IUtS2^'
    'E*yN{$#y%#Djx^Zd7!yCE?$%q=l$(7@DyO~p6mpgh>@v4_vZUqI^B-PrBAyRpf{MZo7#36E%(p$U>Z8EA5+wPd$uEK$eQcB93*fe'
    ';1YNr2?<KT%M&uvjG`&C*tL_h<lMVw(s*Ea(%tZi>~Lg4qfktwuxX+`*<4^m1=$|@*mlSq5(5Ky7lMf-;}$pUbxZw5xfY5Ya*O+Z'
    'uXuStl5WPM;Nxn5j+WQG-zzpZ0p<nAW8NGm8b@yH-`#bNJ#@d2iAdh5CyK3C*9$wG{e_ke()vCHAs&f0HNBe)kDW{ud0>{U;6_87'
    'mH#MThoPGtnM9z~JYVy-rOhkNn}A^H0~l6DI~q>&p_VAH5t6arXKrr31f56S6X=4(fT9Cf_$s++T^<{rSX=@<P?Svyieky@N{0B('
    'LFQ->d?dQKiqB*ZHY-W;XDm50<+j<N&sl8LC5l_=gWx@X(9?%54Wm`#)blW~{uHLaRshPV%a!+N_Jh(!T5l2Rv{O1g>Fd+m-!UAA'
    'c$D4|^X1Zvj>7A%fgACb745-mZs>KpQNhe19X%%pZIEDti?|u*W{-?z{^z#XU#2v#zE05~TW%IpHX6K5JWtGQpfQVHK3bNu|COO;'
    '=mb;2iY7zE7I@&=Pqxy467lL_8bo{M_SoaSO)0EDFLzBfM2h$1@HlFs%w8<nM?p&`0=BH&5#m+)C%EzO<=6O{L8e(I#I<3yuV?rn'
    'c2l#p1jwZu8SP<4zeVLdZRLE8FRoiNQsu#J*9{XK9Gu%X&3I{mwshh}g^(NyX+?(kg&d->Tr(Ju%kMv>u8|8vCJZj@hrLp7XW$7n'
    '<oC-R*+bO2MlFe!I^?Zp-;`7dZyxJx?p9t7=})v?sp5vZ9#YKPG=chtJ{mfpu!&~3&)QcVfZWH1Z7XP?fS`;*r=L<sZImRGKQ<)1'
    'YBt0hvY^a+?3GtkE~aJuaZhvS&(dpz1|6yA3=E9kfWw&59k5VC{Q#9Xh7Enp6PIwIGBSfRftP7M1bl@Z#C;~DL!a2tt;6imyNOj_'
    '>m^5-W#9mPdMdHgP-mTK5{Gp|BF-w?`?4q#J(9me{sM9L5V3{OV&Vt_;`tE#6XML!HBzrn@d8ZvxpOyS2TF`G%Bd^7@ur+Z)r)Z8'
    'C(3l(#YZnhP@c5NtbRynpO>qQC4!TW!e`hqyN>z|UDRKph6z%`@KLH0B9U`UzUN%}s;0wSp;Ni;$9V!31;`v}M;c1+wUzN(a-L8Q'
    'xfUKw(2619%d=o=G(F(O5P3r%I~NM0M-h6WEh8F3C$v@65a_1*ATUH{0p#6>5l0ybAha!7qdo|X(lX?_byBXcGLVaVUOUa$6xDrE'
    '+hSA%QLrhA+i1VqSrOOb>F`u_(7*LbE&u~$*u5lBMkNH5#rtS#58?J`x@LSgfwFlW-q9Wy`~*}?I+}h!S@pS<?U7r38Q@3LJZCE2'
    '$<$#Q3g*{>&(uRVhTat-wa8w3mijth>uN!;$$E)sbp(9GfFSCXh}dN(EHfI0tC}fFK*bPgWUBkGhQ0YnK15?iMkv==%e^1VihQlG'
    'gVG3O@&|=7vAo#_GD|am7MJhVIA*lI2)Vz}l}!JgpA^FI6lPPud&oXeNSbD;%xHpZ^srRMcezJAYM3wymQUA*M#+q}ITz<>E{sTp'
    '6L>>iBt*!@T9dX2e)L9Pg#f825BG(io(;HE4UZ+i7$E&tm3#e&EpPBZu;Xw=f`&LO{M4=%mARbN`MAq%^VgCw(F14A*Xh$B=2UQh'
    'bUng}rECz|m`Hh3OQeG_pMxsD5gC)`V(a?NAsV?#-XC!&b*@IVvQpEW%3d=sBJFVJa+&juf_R+Ej_<Jod^S0g(^ktA@8nW$8Wq@T'
    'twp1*DI`YF5HpD#zA5&CGJ@^r%A@_7cy>H$5oUTE2sD@aRO(?+Z)TC4>iCUE9YDLpTeU~?a`j+MB>HFyjCRCfPMzC2q7ElJkUT_n'
    'Y7DydsKD;h3gLCV-#%j_a^%h(tz*TC$Aj5hao)at3k_91_!2j|)&*ISbeS?;m{DKaIKC$ZRou|c3NUST{Op<sF-Hb;z7jii4CJ>g'
    'r5!!^1h1~7LezT|9cs0c)k;@iw(27UF#Rn;Fp*Z~iTDVUs&1IkLCj1e0E=LPne|P#Fpsjsj@cWGYVm}Opq~-8An}Q!bE<1}Gmeo>'
    'o)MN0b78@AN09AoMg;45dO1Y4Q(UIm0|xu|tALcCsCz{rsWL6VgASCA=H<{2FRykSqmKaCDnb=tS$R3KJV?^i+;iMkL9&M}S8x0D'
    'M(9pOD>cJy8hq$%Az{xqhhs(wrh5uYNOe$yqol>cOO=yx$t{pp2qDA+GJ{S9+G?rQQe4kOc&ViB3kvrjbElS13IR})B+|2~1L$EN'
    'xK_#B*8i>wkfI?FEm{rT0A2p9N2hS^L3!YhbfiY7lwKQxZcNC%e^vo%iqdgY3>qf53l1#t8?Cfp#eOIhDuLcX0f?F2X$6si(W!Ku'
    'Kc)hrl2pry9O#G(4M60j?<2y#W&?|gZaQ48@s-Mh9GexP?F6V%fwY1o?knn)M$L{<UF0}#*Z~uFbSrp_$e2)$rszu<X@y-KmU1V~'
    '{3bWQ#Y8FZ35`{B8=Gn0%*M?Dx(N62#BTTLVaL|r*27SmcM=ojVla*8%MK7TB-^5|i2>08PEKaxf{@g3rVTn7tX;O<&+)_La@}e9'
    'cmX)m%C~_pk2cNWt~AMbupxm#*nxp_^cB>#qKZO9%0@mXqLEfzMX=sH6KqaSQSN3&Qd$f%kL`y1L#;0=Jk`@_y)9l+FFR!5Xb467'
    'd&WNYnGN;-MB7m#x9H4ytT>)17dW$MZVZ3FN>40)8C>@XVFz~^E;}&eOtWeyK$F4ADF^iGP&Az<B4I|eyL7-zCi<zPrtLvLe7aZy'
    '@Y5iC57+uvQjAdPK!>IT*T<Ke&KFS$&zU}+CAchLf4;i|r)U;>4{VZL>7cZTX30&v<+<($8qiObU;FU$jo{+dk-{?zVzuWgnWRJC'
    'i>G<Fmq+p`2nj4{{o3|@%rFWYB`W53<qDWjF?K<gi`iPV!)+I(Mt(6Klrkl1{lR{q<pC+d$#%&F4}`m~&!Q2NZjexi1`OT$C0E*z'
    '793{I&%HHN$*)VM)oSBCH#n=`!z$Y2gutluth??>o@r)E4;d!1u&Lc3kJ6v2dw8i0MH1L$5vZqh1Hwf5=^2<)vx)|*;EfjuNd`^{'
    '1`48ilwOY>eg?t;l=K$ej+BqtbT_0Wu-leAu#RJ7bdU%j0n)a;KRf7So?qX5zM1#iO?sxo=;Zw!ztXbZJo6G~%Cq#4!-(GLy*<0)'
    'FimPZ*LazvXDL-P-qS0?<;5|sH}cla>?}}}QckWZd0QBn#O>ovV>B`0)YoGXaJ)5gE1cxLf~??KVwRU<t-WI!A39C`pbswQKOv&n'
    'Jjxk9L6|Whiv|vuaS<;OPBtw?1QdRHS_q?%*??K!e&p2kjFoJ$!j5tcRcYpc23a3KjF~M^NW;wfh|Ei{I%muYgak!-WCk}BI|Qw1'
    'T0JnmqZa6)_RUJ~`Lk>bMhsa-Ag758CSDFR;`4gE^Ff~(TAxwiA=o%X+O)3aTXFrYyQUvr%3V>&m7EqZmW9$8y!PVz=o6t?_=3*v'
    '?6t>^uS);urgt&xPgcph*5c0t5*-7uak{2=j6Aix85#Hbwk>0ricyPX5V8_sOA>$Pu5~7Yu=QzSM!O#U0HnjWee2E*`A{i>(}3@Q'
    'Z$W|(u9liR!yDKvP;=iwupwI4mkj1|XWtydjK|f2#|}k=^$bgdeL)RiBr0li1;v#>{kmgs1}BwZ3Q7kMH*yWnbuUkZbWhZy1bBB-'
    '4VQ1F-zDaHSi92cQIH55^GOy&Fr01f+5y16$TsN04m;G-E(kXhSwrN*n3ellUWS7ilTOegqEZ)T0Hp+mxat*lXqlK14%cF2>o!sr'
    '$ijs0K?kkVq(0rk`>Ef+k0CCMt5HEfLXJ*^M<K+6dKf&Vob<@Z#UXD91H0`IZ=t0_2iLMT&qzD>yaPs^%=(yO#({E-PJGw%)H52a'
    '1G2M>J#!wAK}s`b*%u;PL|&ew1&wA5rIk~j9aGq0W+5*_d+a;)5c4xk2xmRs9ndo~Cc!pmG{(W>rCM-Hkp3F68XBok759lb0~<9c'
    'G<Vl4$glv02Wai%R=5}-(7_qV&4SC<Am_|CWrmP0_zH_2V8&l4m`^)~IRj*ph($4&j!-y+aMU8$pLERbZIRYp0utMv(aZVRqELyQ'
    ')xEjpzJpHzaRAgC&)Cw;Lu4;>gqTu@3#YM9-r|i5vl$rUbl-nYcx@mCgI1S4Bk)1;nnNCPWdCIFY5a$q;UVK`cVBS;P$=^-B1z^d'
    'I^@c?cj$TY^wPEZ&%(R~?!IGc{V)mLy${j1$D}E@WwTu7w|}V9Q8~6^>Z?>)e$%=^@Ue2OAQ-sl=<hv-1HdOzcyO378>tP{YzFA+'
    '1=4I4o*MxZH2F}uI$?(bXJbw<J+(1xfN=fI;S1nIcKdO0IOy(<2?vOCF~>f%yD?+pBrr0mbNFPO2|7gh?w7GQ=nvFUh>T<M8O;%F'
    'Gt`-0!;`EgYBKl}8WVR6s>Pp@+V|*?ZR`TDeHxEn_DU%N5k|D8;|-%6RXk^pksL9$6&5~h6K0y8Fl!$9GtIP$o)b#6okBV>V-35G'
    'bPix`4Z-8$foa#Z%-m(3@dy-DOrs4p0BH~{p9&iDSGyH~>4Nf}02eP7w4hZkrYLiBZiOH{8#z4*2}Cq>DUbFrL)je7GU{#7tb>%L'
    '$5#i8$i*y_4MXG&ynQnTEqe)$yFNRbh{zkDPmZrbfg9o+&wFDmHcA6-eR|H*)c}M7dvy3?X2_ihU#=?RvMr=c@PYJrzPCdJ<SxRI'
    'O=pF-<L~#T#bJk9F%n76?z0K&_|&BpZRZQNn7HSZ-{{rik!V!03rI7RLKy7|IQhwKz0pzp{dX+(0^W#x^r6q?>rL~hS>~RF1c~fm'
    'E*0yNpw^l49W-=PsSfR%j_^Y_#fn)PXQXr`ZV`#7{f>Z6U`;SV!}XjYFX9kz(N?|Rz;*0+2)n;s!wjfn7)GWQE6lcsg@8_(V)is2'
    'A#%e=E+emIl{0>UL3KMsABp$YFbz1L_Q2uwC`@AiKy|CTK|BsV%-{u}ijV$$ix344ABP#JO<oRFnPJ9#X~FXddW+=}pVP73+D~58'
    'd_VRW`+?-B-0#&9H_+U9$N*=IcCrd&=i|Ouwj+Mlao{J)aRqc`>)b&y<_X?oh3}@%n&Dt0lozW<a&sEJvA5WD%c_8@ttdb1EG9H$'
    'h)xtAJF`%iNt!NgMDy1|7h|}cB7YS!k2fRJZ$eR#llXwt+&9VtJ5vY<%IDJt_4OE003LFp;MI|JV;(Q?Ty&;2WE+^VQ-X}zn<s^#'
    'w$Rt}!hUhHm>{;22p~JoAY|O((nS{@(`pF$+-MwTun7=}xD0>TztOJk<nB*#OF>4-CPAeVk9w-llXkug63p}wjNfS2%8s5X9h!uE'
    'BbZ7oCh8vKhwt;FdO#N;C>uU0>KxF?iQ3>AhaG)D6n>H9j3!$eTD2RmnN(rMBy$UdL5BF9#BHBGvW9s8Xj}X$ahrD3>ewW(3D5bB'
    '#;xp#ubHhg0QkZV<q;<@H`LH&_r@`S^m?x3UuxX;WhMaCIci7acN({{10kOzIR<flqjB5Khq1cGva<VcL~c8waYe(2p>id9aeo!L'
    '?Iy0TH>jd~GM&Gu+;%$54v$i|hrj)zay!F}mX<fVyye>alge${v9JkSN&SPW@F$hq8g_eH#K?r5uTuD5Rc<?^d=Dx?|9AYg$Zbb%'
    'g3gj_#jo`{k=uSu!JtnLt*{Ue{G-TioMjB~mW!p&7y*a*i^y%s>$zcjFn@G<_W6GixqWF*2cSH3ReRt}`JKpZ2Zw<&jap4H8vU0d'
    'x7b|<Y%?OFzhNMMA#y7-TGJ4sBC_tk6S?hAV*6May**XEzY@9a5QAY3BI12o`JKvb_pH8QvhW<e|3>6iW;Bw}WsN3b{f)+LN5$S<'
    'A8dmMM_*&WuM0f%#5+S5P%(w;073IL#nG@xk%=tIcB24gdv@iu(qv$V*FA+ELp9P4O8%SRx5p=!Dqrgq{GDbpV=#^WTJhBK@Mcg5'
    'XuKOCyg8aDpIplign+dLO!Wh#%p<K}<dD1}J+wlNlu}WpgSfn9jG4)w7oDAxE}#M+(8N7L*MD&QT(99ne{)2Z%WY|TeaxLmJBm@j'
    'm;F^dUj)kONsQLl&+BOyL+?c%FhuL{sUAzU-pDcRm>Ps)Ebg|)-nO(jWX~J?d!7TDLNPLtVtL3el6TRNKl8Ql1*}L9xp5>|v5>r_'
    ')9?k-1CY!Lp!6Vwr!B#3C%t^Zk<0*GDCp9r8dwUwCe$&ChYy6^*fdGd+<QOq^bW<KT2krNq=x74fS8!ynraKw!WvGrMT`GH*c%6p'
    '8sT)G?K?5R0nB)Q+i?ukcCSmWq%1R486e3Jiq^QErMRKuR1ea85`D<N49Xi1nHioZ#duXyMlw7mVZHrLU2b8w+>H(<xOTh~j!>ju'
    'sA$(PqjLcf$>K?55k|l2o2g@YIq;^6iZU2wXeOf<ikfeGBcU+Um77b%)VPys0bp-}?|t>M!GIle$y_XG5k}Vs>^G)<&$J_Ihwwbm'
    '#SW;C`a3#d_kNcH!kgw92KZ%Z%VqjwNTp%6%;BXe`-U9dQ-(v$u0(l*r#O(>NOYGA-_&SGOZpq7`T(5ahAn1bAQe=CC<h6qS$3VF'
    'Az`--E+eQ#ze?<%<_0@LyN8ku0HKZ27USu9B)=#Pdk!r-=Kbz6;jvkjc;@T@jxy+}?8h5s8_8hmHwc9Nj2MoyPTDNP?pj-#><k)u'
    'L?ATnGiPoER6d^GQT3#jGBe;pp^d#ZldCX17L`)Lx}mRaeP~#gRLFueBr~fm5P;EwIzN5rW!`I#o~=P~@jzQuptEu`LSyCC!(hQV'
    '^7f3JP6i(5(^B(7Nr2oZ&H=gywZy>1KtaPNJM!gQ0;`1`)O!%%Zjd3u+HDO<@bd>l4H_=cb66a=H=qb0ljEMuNE~G*7e%BojqnHZ'
    '3jKy5rHD?a9g3_C=_d9@F#mz6Ix)yiAAd+F02sJl%`OL|8azU>Mu>#nwb(Eoqz4VDQ>lj4y<^;p%)k>irBkXk!3RUkuvn}5dwC#w'
    ')xtR79d8E>I-zMCAAukH?tp`6c%zjh<Vs*#LmO!!IqawPcxn)t9*Wb`49II<&x67J_B>>qG+^GqncX#Zmm$ymW~hN6Si;K>X+`do'
    '39&mwnug^tX;@@%=|eU_qd5RBLSiGn8PXJ+60w$TdypWoJ)8qd1v{{OHc+L#krW0Q%U~FBw0efg&wWeX2?Z@Q7D6y>xth(#>7h+K'
    'JZTz-Qml;~g?Lo6hdDay`&~DYS{iKL97#;{1qBNJ_;)=NEO2!6@r<0M!)fS}<Nh25WHnFmnJLs&p->l(KYWy>cYD0h@wzR88A{VH'
    'xk;_x<&KA84l{mI+Sx+l6f??a1<lQ3Onrr@1!GVK(#HVR`KzEENDx*?ztI3j4=|~Fjp>DaG?0k}KY^ydq^$z&K<hi{RJ6l7b$*If'
    'In&B?G9=q?puK|z4m5Yr2TQ??hG0TDo?<k^3h5xQd<KRFL=RR+oI%OB<oa|EIh~wH(XCi0%_3Eu|I6J-G-IAJl8aGT<Lse}$@=WJ'
    'yG%|(KF;l4E5?RF4zN@k)%37~8||9*iRL+Ncqp<628N8_0N&hGoGq!mLv|YVTgoR<ks8+nKF~t22-ZWH-`HCIu!KzCuwacFcPoNv'
    'p_y1M-@v@^KqCfY2arubd#SV>@X@U5g9y@k5%+{;w&_9P`Cn@ip+DOeL~=&eZ^F7D0A<D}RP^Uk+{KOOS|RN%JJcrJQ&{>6ty}ny'
    'jL>8d+Y1^d$PM)wb7C^Kprr!_0uSb8H!B1S4>pB96D&?hq0Q}mJ&c~LxiPeu65!zs_&)g4VYRylQd4M2f~jYSxwlBi$h)&<%}91@'
    'H#Qoz!Rmo#7fsg{b_UpV&VcwvXj!56yEHljkd__aK#Ky_-byj)gVe2(Q%@TYJBVh7lKEP1>f=)ntISnwsk$;d1tcbPP@GR-2(>Bs'
    '8?eha9~Zmf9Sn%UF8z=fh|y5mPTDaX3uxUvM;S*mJI;d*Mtll7(5V+A_rBIlb+Zi^bv**&U5_ED01R+tR~B@uqgteBS4aWK&XS8L'
    '=c5G{@ew0A(NnToQrJ<d#<eZH;Yvu_QUlePaoExCiWDvL)Dxkhl^2}dysEIHOBDYB6jZXmg8Dt+P6<`D35$i+R*INCn*d2j2(RJ1'
    't^8emaTI~48SDZ1&@yo!@%?$)sW7=vShQk8g3=e6NPtB)T2DJ_5=fNf*b@{SFGc5%F+b@t!#S}omI)=!yNObnr!|8LkKJ(@MaSDG'
    'jNUyDZ$QX;XXxZCGp_E^WT1%JPs=?HcGYReXC-N;-W#{qrYi(`sq?2D-<1+!O#wst{|YU@NF04XYmrmf;_VGbscx19crs$0PYVvk'
    'a7`3~Z*=TjYiy&=@`_<|S{<)h^_{M_5H12{;(#uBIYe+!W1~&?osC3RAdMbdTy}n0Kn%;MO)IFoT^P~*`$%xPpy<qMkOTFN>O0@H'
    '?3NK!B|7D^Blm%~yo0*8i9wkXdyi==xiM&d<Y0Zk?^7WtmW3wR{mdBrVNtc$1o{ftU~&}WPWkp3&9ijJ!(!;42oAmHv?bQ>dIu>G'
    'iyyvIZv)W~lz1fjLsoeVMo4V9(C4co6TH(3v7)sLGpa#yt=))W1{P>EA7}UZlDoAOSk2JNGEkvSir)Wm^Jj-=9xM}3GoS&qfawYe'
    'zlGhKS?<zrkKXb^S)o{B^ylwxXD{9TUBSlT1ZIl&q2ilsh0+p=8i3O&n#Ks=YoC#?Z@x)|s9w_yma{LA8Agt0_T1eb-FaMLj5x|S'
    'f#4uwCuw%w2I|2nJ;cU5k(9B5APy@wMnmWUAc+>=N6X~(cz`(ksF53u>M~g%%(A!QUl27sCh3_GadE&SrB-)nTn#rUbL!4;DhFMM'
    '&A=)q&qT-DpJrgqv_oAKo-chi<2N&~WJjt~j5THM`0EI)MQ_eU*#%j)wSO}KYk^g>FIZK&<oL}5EbKUJ(C9Mb<2MtqmQ}tig^a%m'
    'aq(X#VA;-1`NQgOzZrmqnGbId8QD?9{B;19>`)Y;uLCqJG|2xn0PE)UC?(N0L&dIVYTK7PHEBGuoeTc=_4&5cH2-w~)}r|zs%xeA'
    '5eETaA*vMQ4{2o|!-z}wL<I(GkwkjY0@GhE_@fF+FZov&|7HBuBE%YobK$FIbb)XgL|1&~2|L=nh$28Z&iKvvE7=WNo%oy33HM))'
    'zgnp9X%iH}iBZ2H8M-aTcbbtCc4*rkPij4>6#MJ^E7@`WT8-(}9H;fC0a$N|Du!dSGQmdAPxkBls|5th#9Z2|_YM&L*ZEhnV=5E{'
    'f7$Qae)fNn5s+x~v_s<nPw<Mxu4FC{DQb!}2I4Amte&Moq5eb>>(}{L*pcWj3!EhF?N9Ts@-fKSQ7nW9(av8Fz~b&mMLQ)RxC>F='
    'W${yF8aZFLBcla!ZB2=&p#M4p3p-Tu5gv`%G4x<-%cE_0+RCdHH_=XDp}w<M(7hgJF|}_AuxkjEJB62*c=7N?vq!+!3&@?819;d*'
    '{Qx&QGQ+G<v{-Wga6~bxT-o#dbp%#!A7$I{wJBbg5RL!i2(0LLA{+vF8r1~-{>uogo_9B@8@gHDwai~<VBNGUo?pFzdZTUYk2A3L'
    '{;pRoeQoy3`DF%HECIKn18_~Bh(V%5S(|b7yn{4bgv1_eQUhfmh6F|%6y5Tz5Xn@k3!qgI3lI(S^lN_3XFXmbp;XSddLRf*WGzB-'
    '>>wq<FKsy#`PXq-i?F`G34-<fIxOp<7I-p3VIVI)#`twuRtr0CsY2$a)2IK}VOgJJ#Pv`+pam)9Fa9tq>kpfDc?uDba4I(baah*p'
    'E2wO1von*<!);)_p;%qLlglgDtYKoi2THUkPO|waykD9d->)**qEa1zCw_9zHaeN1eck+GXnR8bM#yu|5ClLjj0z#AaE!4=#G|;o'
    'e0%hE_yByR?(Wdf5q6saqR#hw&cQP^+9eDm;KJ@uVDccalETf12r%EHf|9Sa>!wG)=}Q4`7>p$GZ_)g2J21<I1VDsGhtw3M_7z&3'
    'SUrKj;r^)TE}!m|GRZGrF(N*VQB$PGC-j3nB^kA@(bF*!8_xF?qj$g*1{4ucIL$)^2$UKtiYFzQuV9;C8K~5JD~i#dg#(fq5TOso'
    ';)l_MoOjsq?A9djeMb)^+IozqqD-=K9ecPr1w`loe=QHT5Me`)i(a8~cWRNaK;P_ynVtfY2|1SqdG~MR!Pv8)6->YYa{Y}u*z)|8'
    'ZiO^66@H@*wiur?JSSv^ddy#mgDKdeFNWw7-y6-FrkUy=Tv9q=$0l%sUFRDh#O)P_mDNS3j6oTRP@pKlnfQ%5*n%MnaS26;x<Ynv'
    '(Kb*>lysnF3<?x#W(5_7`5Sq#WojByTa0!%`Een15$rQpEQ3|LqVyWjkt#9KkHH5hC3vLr%ev4WAxL50wj@)#PZtGUz=AZB<A$?O'
    '>a~BB2is{@J?x+X1H=dn%Mn?du|*}@mt&r%BbDqP`IA7{`0ma}Ff)H|^!)rP5XRF&+}ZGrYLCu~KM90=Zx63(1b61f{gXggt^z$g'
    'aX8sz3xF7puU7zOuvUIumM8R7yiaP)z%{v?Wj&;jSo4UR;4G-B{3;RlYIf|QP5^HW-3;~rC=oWlt)^2HjXe*@`b8lux5kAfPT?Od'
    '-1VzK*!t{XWxk5v3b1y70>K?54@|oXTt;twK)TbjO%PK4PFgrm6h`|Ag%<km83<ubo$omtO;NC<dtQpIWDZ{o@-sQeFg<AT2=M?M'
    'JRYq8IQWGX5TjT)&=G&5`h`oGCJh#AIMm;$d67uba?m_g>^D+gI26WdxthVD@n5C9#!bhA5GmmS1pdI^A23d;&kTcaX@YsPyY~q-'
    'YedyLL_$EH+=-yM^g*G09hE;g99o*tiUJI$#Bn^FsY8^FHcj;8HWDKtr!uYiY-t6s%m*(lhl}JR@l~fAP*JcoZ6VamiQwVmOqZtv'
    'g*arlbQ_TA|DyO66vT;UAVkgjO4jqQCBJ0W8GQpw<L+o82K=?qDZ#-FGdgdVC;pu`M}ZML6ud|ePJGtMPf$m&X7h>@WucEiqC!Jn'
    ';=Sv&4pASPA$B^gnqr-?pi*OJg#^6LDsl9fctii-j@fGfM^Hpw>r4wBV;XlIchLTxmzy*PRI6On@1*!InqQdp;(#A4xBf=*%Vv-q'
    'VRr5i#->U3GWQOr7*_D_Cny=~A}XQ8#tr%46qy1eqmL08G()tnPn*gO^4YAX`(bWSQ|L^-FNxwA9=qwMaw-_!M9SV%`gXL#GsLH$'
    'Sb#1<;<%pq?Bq4O`bhyi4+awM2U)@jEOb1T9um8krN|o9*?qqPhi9s4`IeayyK+R0yPYptpj=|wCkF++^`Cb3=&l1sWIT}^Z~*`$'
    'rQW=nD-q-eHLE_5)TU>hw3HJ*^k36tsO3My%s_gxw0ucbQuveL^$f4;VMhn>aQESI<=@KV$Q@5w5n_B4MJWpWw64zA{@_i~AG}Q)'
    ';0e29ARE_t<6+?zHKY(q4EmWc)CLVEbU(#PhhT`ZY-c1${wQ^NH!bsU(Wl=D5on{X^DC@DqQ`TXWgl@YrFI+&!|T$H#Dx|j#t?-N'
    'HwlVj3!H!6oCh%!D-M+ytxPOVj~hJ#kDfGXC?s2CI8{x(S%}uOSfgwdU#v2+Y?@jO|14e|J+~WqnH$1zlQ9)cLqLY;+|)6r-4b;+'
    'hG1p=vUv_D6k(QId|H}T5elIpCG6-gWEBs4<X9?{v1oZl#Ud)O$0VZ*_x@X;o*oLbqlJbA6<x$1ymS?OjZb+RGRy|s&jK;*$?iJ&'
    'S*bnm?1*x1G?-9urdj$nE5Oe0F+fL1kjit5LkAS(CuZsBjfNrypeZN}8cj3I7JFrRh;5JdH>)9NO%b-9tim%hhdFR4GlW~@(K9Oi'
    'iuJVT&?Qu2<TQ(5y_{stcnV7Y=f$FA5htl19!d+q)bb(dMMibFyZJ2CZ)k1kMDO>j)}!jdQKR@dY7wmSPJXi^2EdAeRg5XUZ&se?'
    'rx`)=fP>^PP0uMo1djqj@>~YINIEup@^#R<8>lA6xdU`lKrWz%w3~Dt1R1<8D3L~E<8&peSZOZp2+a8~)zi1$mw+$~tcI9ZazB`U'
    '4B-~__>hT)MeVa!ANwPw;AJS6(vlGglrD@QFpZK){vmGw9of{Z!?(l8KpzF!i5_;Ag(HylxTi?mm=-e3@;!MyYX1b+EWaE+fTkQs'
    'ADp7#6w1M(MBc0%5C;!aFp!-=&p#=Oc1DgVW}IW)BTjViCdFH35CYwYfP`15$y_r5a8uup4m>v7>~%_e2~%ySDTezCvyS47rv*Um'
    'iVE0vVVLf(9cCzq(g4iq*<-vR#6Ri_w<mRbx^<ATWK8h-sdEDHiI6p9Q?Mggr(15;sLwH<mu5=fh%<g(ZWDSE-A6xd^dcAQRn+hH'
    'n3;a7$;`3ZnefC8aaUYEExlU+NfR!@%h@2GBHr7QoHh}i0?8_l*#jP%EKm2k-ShK{Y4uRvtyYA4kPM?`ENyj?UPVRFNvs(kFD{0h'
    '2aAIEC<##oHVJ3aS=nHQzb_tD|7|h2KhWqKX=k)&Hmjh*)Cu(kZyi%kx~GB%pKvl?LhAr9D7RR5R}1st&WOqpT3BdhY`BPNRy}?Q'
    'U@|LK#2zSUtWST#m!lVxRdKQmf!`n$XQEH}9s>d&O7>J1BQLT*x(WOrqqKPlBt%2>WP*=Nslx34mF%x-@(x9f-jdABoB${z@bzxK'
    'Vz&r_u(y@<FRgs=Aqwg3qvN7T;)-++N&=r0A_pG7r=!q4(Nl@8cMst>oGFZXv_+Dv$82@E4T{e<9u<F1>vT%z4?LR(x^L9rvV8~Q'
    '({=qKrb<9PhM(R&h%43VjGs&^$IRqy!|~%OJ%py_M5E)3rR2C_?+HqgxcnK@Eh*>}w`bjtRZe7ks0pI(^(bc?R8Z~R#dniH54=6x'
    'pPeYB1s_Pis2>Gy9~MaUckM0O{g2i5sAb1Q5t-5T?iRinjl(kRZs0~oerFTKw#pd;?@9t~)KY16=dIUl@}T-a00<4drcU$m*a6t~'
    'Bh1WxfKLI%G#oLwL^+w+4eh1E$N|qmDk~?-z?|`T-WWzZh_GlGg~b~)#FuevEl%^;UoJk-+P0bmb@G|dK-VyxbOp7mv|IcEISi@@'
    'k)c`$%gV=be{NT08Z_;AF|`M!o#|H0nLP?JI|jiyx6jEe%W7aWJ=KR}415CU8r-apmkOM4ea@Hq^|K&IcrD%fh*cibjPkCwxd;1Y'
    'U&%)3Xb{(!Crl-cW_Y^EfM3GQ4g9DMFk>M!gy9A<4}j<Wxt=J!Y!ocp!@4fSnd<RhwPu^j^rXjQJ>&<*FyNuW(mHK@s}t;H(LaF*'
    'LNt2<;h_RY8{hY<t|6d)Fduc=wJ`HT;eFNf^X^=ufReORzn*Flz$i@_*&Rbz%jzRmpDE!9Dn|Y8`&o~20c^@PD!kJHh(+r(*eEpR'
    'I8!3xTiK-W7ha44vzfotKH_q}II-sW+hnb*wf~>BKiQQW3AzN$SLxgb0vwb|a@|0^N1@QG0%}n}zklm@RMb4&ulb@g3pxFW6t`<e'
    '>L9}zs^RtJbPDm-Go`RuF0(imbNYX;gZTJ&vYvp7%1+g*czf>UXBk!^d9^rdkNv+mh)9k)O6Tl%H^>BVDmih#=MmObl0XL$HLb9|'
    'M-LHl=-Q8U)Zq+k9IQjfZ7OekUL)4>BgTw7BKdSyd%yX|wmZbvc2xtIs1y^*U&dG`$nCVIu>31`28?5u<^Y+0_cU1}Cwl{XzUvG#'
    '6rhw;?OF^!WpZ$3@3e2sXygfej9Am+TS6A^&f?=}s}`5AT@<ID56u&pXlrq0UU7~wY<=g^vEtCf!vZ6uwlZ<0v=)l%<3oLIG}-ov'
    'c&Ov)(6t<&$S!Kd&3eyR>8f4<2q1#%$gl5XaavIqqZV|wS)b&5Vx$VgTgKY>k-jsBu#xeV!{`~YtzbIZhYl)x-nKYSZi{!Y5ydky'
    '$17iSP=8?*DLM}4UnJtOU*9d95Ranp+W(b^Z|mn0G}&Tbe<XV%OV*V@ksNzU1L2Mrt;UUF<SqsKfJsmbrJEH8%t@r{k}cO@)($&p'
    '<(45N<}g-+I_BwNr~sX}Gvna+2A-d{K|QENM!u}No67@?V<GlWBnu{*VTm5qYXvk#<udI%R~!}~iL(rO%6`nO-rV<kmXZULD_I8Q'
    '-m%1d2qzn!@ZBtuZ2vddvmm{XazJ&II95nK*300{NSDl0WxY9T9;#B&YQM|!IqddGh!R5H>k3U>vq=k{>dKuhib=Za5lE=M*I1%Y'
    'G|j5phNItG^kkKv<y41*LW-6h)Ky`Gq0Ab5yV|(Mz760&va;f~Iid=tqD*_zkSA3N@Loa#G|(Ia%D~lVVFCxkyp?R;2qUvXW{}g#'
    'd43u)nR0XVZWTu$kRcw%QCqHje(8JV$&{?ZOW0QDcGOfA7GmI)5q$BB4?`4<4OZfP*)btwJkXzexxJoIh@*fIQe#PqUKz3+Pozf9'
    'ieu<!Vx5HXsl)L$@;fNMJ?ro8X8(Ex1g1*c^NJBM;j7u?BV3UQbWYc+kRu7$cw5#i;LOBG)@#bS@G54WI~IJd!=;x&iUfzS#P#gM'
    'u95KoF;x&uH3t;)`>JG(8ni|gRo4m&I!m{<Kcy!+_W6Ta8V!}DAA&SP$AkcFUzIGZI2p^mR8f7NNt4nElcy?KG_xa0=-c|K{ORbJ'
    'Fc@4CNG)|>2kZHK8t)qA0o&$ZAOt21dL~O4<c@+ZNa5UHx=~k7c6jUa`aIv=ZS0b|o@LiT_s!tyX}|tzoK=s&hU-E;-x!_S{J-88'
    'ly}S=pKFOPAuz}k!CkiXc}JX*PyM)UxmIUV?Ce>(+ca9HJRA;lf2wSEGg3zVs7&w-uwBtDr*9}b5aO>_uzmLu^XYeX$YE5`dVM>i'
    'yeRLV+lnI@9>G(*t(ieb@A%Ci;aFNeCx5m{hOSNqpVmx4FxHo94c7whI_+%tTf&r=5<=$lk(r`7s}4rJD)t;5UJN*@MA!b&OX~WO'
    'CkumC;%hIZ1EtLV(R>24XNF@l73@10VRS0H|13qVe#dU(qF7qpA}#785-@OzOEC{b%*B3$Tw%W=OX&Jh73&{au#iNew6%nm1H=p='
    'WWSeu80w_zK0Jaol-noLLkDiDkx_Pjy0rgkZ|M_XsYkt#{Ub_vM@AHv_+2{77Y$8K<*Rz~B=eYgkP;{i`IJva3_|?;rG$sp$CoGC'
    'S8FQc^v_wbFNHhq?pg6$HBcj`RS4%26gHFN6dnqD_3cNga$tnYQ%cM0!kc;B%x7dj>XCG;qci8lTXB0FQ;EQD_j3OMVy2ee-;z{6'
    'GL(CP9L6<pE?34rduV~gELlntSV4=VAySZ$BM6Kw8r(}I_Hf$AW$mpa+c9(prh6|H&h~Gv;`pszg;;E1<Ny?!IxjU$NnA(N>U$v|'
    '@5oEs;gXO0Bo-W3iUBEJ%-0Jh<*M(Fg|YbVHAl%Aqpp~`2EnwX0YUbE4f^)XoFbIUoO9Wh1JE0z_Fv<hkv4R5D1CwoQ;wi~;VY~-'
    '3No7VV|Q!|W{8#n3cX)zn7*fzfIsJv73*Y=5Z)e?b6?{iw)Hn89@Us<{fuZuGjn@Z9Cv5FL!&y|%19)t{Zoy24O1sK-O$wTuLHwS'
    '7fO@T)rUr>FZ-rM8eg!l+i_%ght&64VL@TY<siBX+!kaL1){fLwFZ$9^rx1vui*!&%ji(*n;(lEr#BTf$+j29;Eo9P6Q!eme&(s^'
    'qoK03y-1nv<V*%j9veCChExyw_UuKsY(TNtId5BI*O>T@CjbL=m2!>AME3YoN4L>&oAzs~F^e>SrqJ?sYZS><n`!f7_g9fmPWmM%'
    'j9~F$_Q3K-ur_`EKu63tA1eFX=fl9vkLNCpWg=Ixp+1x3FFFiVm-$-w<)y6V67QPp)qxa7fiU#*UR*c*6byH|e^X^<JP$aJlOKn+'
    'P65*6*u80AJp1AvdOmUEK&L5T3r;mx9EaMq-YSG)jCl6;EU%-BV5mmrRf<F-4txBjShMZbALnN(>Aq9IubF!fJOY{fEH!`|_j0@p'
    'r1Q4kK6a3%5%f!ib>-dIQWVVkXP6El@*>x)#<$Lk^o)w_w&vQAs|bp!J=KG{V%^gsKEACjrezo*1zgAy7XTQeq>4BDd?wb=R$j>j'
    'ELZ?$p-(LT?zRTtE(aRdYTB#d_j*2hcyBf4u8915cH|FA4eyHBRpdEpsl%X2wQ+0D;tOjjliq5Gsh?x)imgMNTHwo%-qk@vyYK6i'
    '1=xq{QS7fo@QQaD_T}d+9*?<&fd9-QAnHj07?N7*i=~XRObRi>x_L<K$;c^s?QM~dIT<xDDHm0V=o7pfHxg-|=M$&5XpH_Yu)O|o'
    '=WlW>X4)3hQ!joGyLH`AnLZK9_)w$a29)-X(N<ZUD1zm{Zwv!+LydZIq*Ug)YVMW0kptJgr@B#9rOFn=ryK26EB)Qu#H{r4Oi9h#'
    'ROI6}y6@$-`X7s^{!x<ieWMC^uGaj2ETZ1|GENqX8z<?2uC~8fL{XBvK;TJ*fGvKvh*IKrlX)!nXE_V}*CT3nD^D^mEjG0~oJRYL'
    'N0iQjk=x@M>&uJlza~*fg-Jce9t|h?IsWvBdOreoQ3%l@Nv`%6kEl~ZM<wq%gNyr{N0hh#6<8NMTa9{tdPIp+TpFjgsV?!=Bg*&V'
    'zd6o^cTU~^u!y=pVPlDOzJFBmzF0)<>*;~W>R?YQ#8-zXFXIhX_KIA^cZ(<*fl@Z^y-&~&Umc>X0E%o|I)dll45CIDR!~qE`|KNj'
    'b%+{q4J}{~?(!+asoyN3mVzO!tO*E`VgG3nwYHBgS4<9L-~5L^R9h{cNA;N%ab4|i{!ltg0m$5O-md=lFM}v^?TSNaO82;L#h3W6'
    'L)29*p7^?IU_(2fKOCakN5T?G5dU{1C<QS7uSe8JIy0vym9l5DQ-Ak}`ZTJ}82=`}pP-B1J)%Be?~oH_T)%d<ndW^@i-vtQwDwuN'
    'nut7wM2I-bxMk40Ki_V=EfSWOQQTjgq(pH7Ch>qVet&n8${!sMPX9soYMH{{*&S3rK0o0=dCFDuE>#v=9dK4Vcs-F_+na96@l=I}'
    '=m1Ae^Y7D>1Kv^5cN4I3by5|;>tA;P<-IV#>@dF17;S#_lF~8^T}(TVR{CGeq%4$}GxX?Kz2{FiskPX*FhRGpy6$ggQnfnGpn9yj'
    'u0rR$cVv=6VcU-XS<|UIMc@&!a`G70@19eeaxl5Eb#Yf>0X9aX7vsp2`H$(;dxcJ~!$COrL#6)1bLwqUqBr`j;5o-n%c*mQaV*h)'
    'js4~M({ZZ87&<^4SPggoZaDSY<vif7EozJHyWiBSyx5bTM%wo;c2h5diReFYTYmTFyW7-@-f1XvvFM0U`8Ttv_l(gz6HbDph5P#9'
    'HT7a0NlYUk)e2ty!)oe{3d$CbJ>!i1yVKN5R0U>$EW!5S;rwYd#d7tGD1U=F+Wz7*#fBDqxzViK&g1%OGsPfPYtIgZBznKQOuY(e'
    '`ra<H<EXyN50j}ky4BYUEj?wRznM%iQ3WbJ2`iGU_~9{?3PjlEEyI-^i~RSS$J8^!+TGK4#X>9k&2JV{_0?!Y!T<y;(tlb^tq&u}'
    '2Z{DZl<-f7sn1tyes|9c?B5Nh-tac|Xs{ws@8A8UJhcOm)7<@?t^<GAOI`I2h(%(<;lCc=-KD(u7`wo?wdvjS(_G40(`3M>M~M4w'
    'E%hF$NA--+vWgk_!&z!<1MQex*%3_qZY(8?3rPp!eV-D&`C%+&C-3g?V|s?)UyY^SE1Jnpz7$&DZKXtk^fX;hps??*QZFWFmPK=y'
    'E<u_9no1oNrV$>FEf4OWo>D7}1K_3_K&bg?DRott?mJ}v2haAKp;Ub}YCrpQ9$SQ)AAVBKTtWyQkK^b0(@tuiXUFOAS4;Z?SHHj8'
    'NxgamSjbPr*Xo}6VJDSSQbz_$Y&^`r*h#(c7^LXZjl4@z>^C>5YaOQ7?Q*(P`~7f}dghXhVG17)ANkWusunIK0>jzBfbSnxQrr5l'
    'OD`bX=coqU4<{*M&W(3cQwx;;!$`^x&}~+y<VSt?k@7fn-zedaGq+Bn-)y9wdbk_9#K=_dt!O1bOr%8JX&+_AP`WxlJfvKE<U3kW'
    '%&qWge_BYrp<`I?cpG<nzFJ7xpMVtOVmSbBzZ*zprA<5-%I4n;q$B~JP}FFE{=fT2y@t({BMpSx$4TW+`=}%+EuOcI>QXKG;T|O`'
    'iXDW}_c=+xzne!L>r_bd=iI`zZ-1IcP2cS|kj}AWb$iLx)#+#WFmhkL>sDcRr1sU0{a(^)hGLQ={^2t$1jl;{)s^=JbmNv5W}6L='
    '_lde!zTO5?_c{N7xmDD`5C}ta)FhMh9X~yxMA7^+PB#p_?otBLm4f;JkI%G382**9Gog)l$zs#hdDA8D6^1Q<zjF0e`SO4uVle*s'
    'Gtb=j-wg8htoi$=YgC)x|A`75qnU9FSA|bv)7br~Uh0bye)efv>s<KLGwP`~08SIB-mQ|DFOE^KltlxDJ7b$zncoegW?mZQ&5Q~I'
    'Z20LIHFtXt8JeV*0;eD=|22%7nbXKsTV#8&nS13#Km4Lzi2o<bYDSN}{j`g!PorRG(xAR8cF=EbQ7a7eGUUp!pzB<7Gcdr|t4EPP'
    'dhoT)KU}_drk<7*N!x4v1jh1?$+oYt=Be~<(H}V1^Egw!XlD1B3%`<Tyc@<Nt)4D>8eA#z!$ny+-kiWZrq<rWSUAv=T^VI41;aj$'
    '3D)pOg{9RE;-IZirG}2n8!qS7YVUQ}v^dw(OR7^c3Ucm)Ng#jkn2cz7YWtq04-%s{va1uk@e&30Ml&6_>X-+Pj!K(V_|CA_LRL}n'
    '-s_ECghfDGuOPVJC(|RXs9xht9Bz<N<3`$mYlBJyw@@eA%n*?+#?z1{PHC!_nGiM+k>#Tme*Zt-Pm}-nn)PU=&S_(fiT>;TR8i1^'
    '+R^V`7EJ%~eVT~om!-fFyCLH9Z~tNYbXU}yCLrEJs~qOPwojkG7{3+8!?dpY)Ap%OD+W(@28!~h@3v1P?ADn#U^k|{e%d~*FvC&B'
    'xAtKFY5P=%8cclp=;`}@b$#+f9YmO=<B?aB?l;$``Y^!8i#C?~@&1eJ(*|gqU%($|sagN#`n2MprgSRJESAMUgvzfo?g2-|L3Uk0'
    'K@s9FvCD&YFz9_>Vce`o?&K!g_vM13W%C3<I~!peIS4<2tlGyb<xkJ2%`4>CAkp9Nzga$Q!LaO;P``{)ei%M&ptm#%&X^$W=U)t;'
    'HY{~Iq`O=_*4TeKK7HbhI0+>wh^`-&PwUH_aWw&V-j{0GZ;nsv;}D#K$<~BCzB@i`s!U-1oLjw}e{p=;BKS)EMK>i3<UbsrK7aPg'
    'fh4y(TX7?PSUzom9g*kWgACpOV)?XzVg<wTT$2U#)$?i78=nH#oZtIjET1+QHjj!R6ivUMo=@}R2(68yy=x5sH~q!*X~eOknl3<l'
    'E3M$4rcWb|oD$kf^g8}#`m`}?1spPCa~PHH6M+ygsizw2TjrcCL$f3YGY->0)qgFEqfN0uxV+E4e2rkD2u7R;dM9yhtnY(yu155^'
    'Y!dL^;Qc_5`icY3GU+Z~*DO)Kjq~oCJ>3yUa^%&3(Cb^Zx&#8^acLQE5d{jD){`mix-Hi)yX?J2L?dqA%G?F}GSrxJ0KyB$?7<3y'
    'YCy2J`c{&>UFlE(cF#2rEu=N%A)?OL(b%FO98=xTpAGjj2+FNwEvN>uoxn=k*W)`|ECPc(=%tDZt3U2{-g4`0uvNqV2gfg5VJD!d'
    'kjG75anauf6Nz$H(NIA~9s5rWrZ&DHpv!EJu9`Yxm6-JaHBQi*uq~AJ*rQb6)v0slTzY3UD~`7=cDI(x>X_YWTXHrl?ErC@#qn(Z'
    ')Ndwk2esU{)E@lVWD*$yAFHn)Azoz7RsvVzB0@;ma22Xsm>d)rpE<!AQDj4+FstHwmUjCVo<~7;Hs}On57cix;8H<L*6W0S>$r%('
    'z>Z-R2KNG~=AaC3cwcckv~;S2uC3fP*zi%@5SdtUp{8y*53jcLG$`v|Zwmjl-Z@ll`QPn0Kl2(_plo2<pI>oC{vhX9nQ-3dCpb}_'
    '@d`8hB+;SuG#8Z4qTeI~>?=-6O1+XB-?EkuZkeUQUYwTgN}FFdG;r8CPd0Ja<Q$pZJvrQ)7S(<yOL>=b9{XNB19lJl`m-eeN!GUe'
    'T($<JsdPVeQIGXh?#LqGXWz+=0`g383xZk**_;BA%-hjD?&*q$n1P*3UB4bn*ACXGCl>Tp7>)XeEl4XDyNw&~Lk1-G(p$<ak-K<e'
    '8dR4-kI1Y(v=+u)DJt!5C2BuQBQlx-nydE%?pKFA)fzYj_sJx{mR|oGKd7hITwG_G8Qn%Iw8Az<R&YuvIJ0{y;Efq&UulDeO-dCV'
    'iM!%>S-~^INYq_Gl9-5={mwYLsEr)w9M*2c6$gBxldJuBE&kB7xw7mlOyw4EcK@i$D{DF{*P`dA(o0V@f;LNhrz0mH8DvkzNe2>O'
    'm?;EUd(k~HxH)Q&qP!|j*FV<4((T!(%*#jZB$%*%tnoK4M(VWcj>ZDW<|9v-I8wgjf;ic8op(vX;}~DjRzJ^s#m&~%PDFTH%D9u*'
    'DNUZ3HzoX(_h1Y%9cmBE<9J4K%d86s{#!~P`@GV{RV3|4gq2E|-EKMMQdC;@t1pRF<ISf>OQTmDh~pIrD4eNf?HA3}w-x7NrU+Z+'
    '{d(<{avQ6n8O9?^oYlC+pE9b8+qtw@wZMQO%Ua%Ygf(Fp<1{NN)}3JFX-YjunQ7+lR7IE<olCZtMl+oi>TGw#J&a7O0%{P|tB$D>'
    '4$EGCj0!Ar{W?Yv@C$sPpA``A!~s~33KhG|?64e|G;l~c7xmI=)RlpSpjJ7<pv7!g`}6w5#coSxEIBEN7nrv>$-RE8&%1+p(-50!'
    'tztGM9J{X1mrFw*UF@Act5Hp)+Jm(I%oPxXLqsACitc?09qJs*FBh94=*1njor};@f0xOy@~^pw*DEv2A@@q4waw3q@r;?C|7X36'
    '5D&+(Pp|uYtK{aA=v2laTJIL+_lm(-MDne&JWYL5_5NBasGCInP=!_k-0;kgP;S@CV^E~(9#5c-WHY#+@t<B|tXstJ?$D=nPnTiN'
    'C{PTXQ83oV;61BfA8cY_<nUe7^}WhD%{k3HZi~=GyU)tI!9hnJMWJ@>pi55dDm>4<5K_v5sKcS)KNSZ)bHgM-Kon8;L<GB``nL1)'
    'd0Q+MV5_cjszxzG5SAjXp9>EMzG4FxQ<qu~*Y%`fE9{NU0=1SB?X}uDu*&b(-%Ormv`+fGmZ<hMVk)4*`lALQWU8rmS7$?NLFNZ|'
    '>l5}wYMj5+T~JE81qjb1UaDjXb8lC6>+ZDTxW1I6P^+K!^CKMR<DcDB_G{ac5;bBe(wbjN&EFLIGHae^fRxmr+qC@pye|no?S^xE'
    '3;g;<)YZ`bS|6w31YX3V=lo?@5xxgB*gB7QMb1N(Zc&3J^ATgdmOM=QT!aQv!`<(>;8x?!<HufQd+Qd^uYw<-hgX-GA&oB9eiq^y'
    '5OW-ggw%-|E%9lcFA2NR`@3$RPJ!<Xilx*B6}D!WDCm{===0gZ2C#Se<6`wOgOAR1MY-G{h0T3R9ir*s)0(&qBUaoV8!e;Mvy4_D'
    'pR7yb2i1FdV#ul|7zju?s3L8RP4+Ami7kF(CtDReVy!zTO3%=L<*NQ{w2FGT)TN7?`N9daS)BP$vMANC@O{svWqrhPffd2Cug^;Y'
    'A`yiODcEffChbXXy4LZ@yDcBk`pO33@SDlh*ifIX4K#NJ?%nFd8(++E{-^`*<FmJqxkK^w=h5R^M9`9g<|odeksr-{uF@fhl~{?R'
    '<*faKPeHH5uy585E_d&P*WIt9aUAZOgqrK)jJpim(2(xq*Y_h39_sk^oCPm931_5Tc>nsdjJ8NaA4S!BVjY0EL-2L`{8`{>ps=?u'
    'TGDH}3zcE={yFln<rvt3Y}9P^LW|KyeD=>xfc6>guVbmK$#^&b3{y+lKPPQ8!O$y@a|xq51ii*%)gte-#dhBwrP;-d;$av=+W$Fz'
    '-7Hy+TSRqQF&F`v;B@C-jkzvR!w#9Vl{yugAK}S2)Uk?V%W$MxI%*8-QaJ-eq2aJ@<!d6|)G<flf**2Xk&Y>K*FAXYH=}wlt)@oo'
    'PT1BEcsMI-IOCF``s~whcbpA~b=yp^Cnq5yqo@*CgV#}j-;F@o6_8dTYJ;^$*+1B5Jk>VS$f5NyHrm}+To2rDC$#!ho6C;a!;psC'
    'tvKVAaWv_ao|O)mtiOT%w!#LcXSAhlK}@-TCRA75!L;ut(>0Cgkl#`rFWr`g;bf9=6%%)lF7uRW-CH#s@i^2J^iAek*&(jR?|`sE'
    'jGRY?=XU8RGpy_t2jURYHYwM#+YE~N;DJ}-jr%z&BhD%ak^57_g!7C}uVHJiyc=ak4SmF>e987`DF8{WdUS_r0~qfa&c2KKK_K-F'
    'esi8wyJnppA;{0Y(7{1(-I0yi=gqvcb%Fr~JLyj~*<+<f;5R;a75BvIHO?`gQVAy`mK@uxNB2wJYMBJP-Ij}03sCApN?&mlPs~Z2'
    'L915cm)U7f7e9T6U5@EJh0x<#=C>x3RHp%}D-K9A_IyMZ`^U5^t~{s=Gp-{m$pw=+?#nKnF{o5=wYhf0@Y~sA`jDPUnTo|<x~~Dn'
    'j-u`FQMx>qsn`y)MgChmaDCoQfDN}}{Nv@5i;{&C0Nl4e?=@*fSVMEHp6K4D8MWJd{tm-S)Ri*_aVh<d1tu#xox}Bcp|(*B)5&_P'
    'timSM@#TShuDECyk>Sw@D-Ehgf(6ps=e4^-7$}bP*_3^i?%gsDa^f|m5C=_gwdm<>)gWLH<DK-yPRr-L$+Z~O6$(FEogFj&U3FRs'
    'Pcjj(cdN^hhEr^Dk55=SBeXg0^ZAJC$0X=leRdDU-FGPP_qD?b!%zv~1T_nAFC+BKThnnXiwhEB0F+mZuqy6R?rrmgtiKB*?{4XH'
    '^f;G_^rwXmTyE*QK+?UoR9>t++7Lau=&fAU!C2#`Wn{8GF2X`uxZvci=o)IpaSj|y$bIaLs4$_#o$tNWJNVHxnl{xF-ATeiao+|S'
    'M|I&2n13glp7=UebfuaqMVD*-*^LG%>fCi#;<e*;1>Z@Id#}st(cQUY1ik%=gN?YRKg3yc=MA$@L*56kI0KLC$uzg_$oHD{ER~SG'
    '!Wd&BU+EiF9+C@=8NyTLjWEtqG&zv#i?Rciy+=K7LP&CUb0)S-41X7ND3sDOz6=$1Mzz@i#~XMyibI8fZfvEKKH{Q5J}TbOHj6@w'
    '&cfr8NXGiHV5?`Q46@-u351J@bYA|}?gHY15w?5VUSL@3hE~N<VgTORrt5P=66>wjez+-~z*7s9URg3?Y0+7pDe3zJ=y8-%#g1h~'
    'uxc!9+_D0pK^b1A{acaBMqF28A7klS3H5oeS<jv+f1RPt_Q4()N5gZhpMkebCZC?bI^%KWlHnuhln0ACo<7REd~HWuoGdVFnbPgW'
    '?~=i($xWlz&e&oprZ3paFb<80=L1o#6^7wVQI_>f0sW+0M*hImpCcan5F>u}?hA%vf`Bmllzsgk$uk!O<LkHF@zm7zz*&&5dHD1='
    '@X68&{DU7(%(KJ)y`LjA-R?cOkCLH4w80E3iT0h!QqX!#NAIV$x1P$ISzs;XXG#n<y_D;%u(4eC(7mqvI#=8qjWydDp{KeHJ>$}-'
    'k<LFG*cVD7JHNB^s5~5WaZsr_${2A5*fg=EtfjuL=jhVJp{V_sGR;_bOZUBqzyNgS!_d6z^UO|0wzfrX@+jBUEtVGJK0KdKnBRmz'
    'v_E~hmyoT0IL7tK#}X&g!CoZUQ)aIO^T}mur0nbGnv24@IV1|w;<LF{;ln)j_#p38czOhHp~>Qo4#9hrL;Q#fxW46w^)f|zqs|ny'
    'sPkUe^0f9<Lbj-&1x(Aq(${V^*xutEWCrz`iEpb+1F(sO?&>EJilKNFk>0b8(L2alb?IF*!<}dkc_GZ_>n`V%Sled&dzL1#tjj&p'
    'p(C%4&N)mH$y3vZ+G(cH&hi#Z^a-`nY{0}g&l=#$9cdxMS#?8_QdfVYBKV@KeNxtgv&ccw>n+j{?F&<0Y=pkzv}Z@Yb%%JeG`%g;'
    'Za&&SS04ujM?J-ZQmxn`Wqc!4J#{FfvR`DvRT@_bIzO?T=X-suOM}|DorP~ulnrXp8dPVflk4V_N>E^C*|IM^qAff}pSS83G!neL'
    'afU6)kMm8+ZC}<Ldgt(_T((ugPCrt;v2-Zd)pU_Nq6(A)=qwJ1-D!U;BkT!wH<_cieD3>VfjE`H)6P$;Jv^K%ivLfkFlz7X2Egjw'
    'tB3B6Is$4N%jo(Hd%2j>s@hg>JkRopWAO9Vt?~9qk7Vkz{;uaV4O;Id*Nf7N5syJ|uFpHQ`_3&A;Kd5QTU=*D+}YOWA)nygS_$PG'
    'sfTxP9ifW&e0ui=kv$OcQi*h;NORoI^_<xn&hi+w{eDaMD_opCRN2*QcLVKY*?9kam{Hpc{X+|XHL2hDOkifd(@p-484dA)o&Hbz'
    'G_(62Gbbyg-kXM`HW;SC`aA@?xKFUNDWy;r2~883Z0+i_ZPDjv9aw^*u}FxL*nNE(e7+q2a?hm%^c&-pO)I8Ek!53O#<W|C8g37f'
    'ZzRn2lp9=-sieJSRQK#B*+WtPX6pFs<A4I8N}f<$D-H`90)^au4SOm71o=<J=czr!sSpjTm$+6oV5bf<e#uDbi$~S>kgB2hpY?g;'
    '1SZ0^r)I3Dq75Tq0To?C<}GMu%${>AjhHCtz|7<fS~GRxc@XJz8QM~9C+?0X@IL)BqmN{{s_eXq1{rTbRB<EYHS#B99|vcnu{v=z'
    'vHbhDf8v;)uu)J7_T_~ebMZHVtowo*_;jZ-`}k_J!TOFZI=)E(tbphl>}ZWX%c+1yc7(8Ljw}SuO^N1a#&}%iYq!(dK9tAm&5F~J'
    'Pt)o-_d2UEA<0cdC}shj0xXI6q9#KLMpECrLt8r+W=0Dz5bc+mO1+L)u35=_A$kC*do*?Sv&f+h=QHi#UY;Q%PCG0vgQmIf$4iS_'
    '64$H`R7cgq-IDcF`*>+-0pV}gA~*sRg~V4Amj?+oEF(9Km}kWi>$r6mC8qUf^?kuRQn6JWszeX^5H_c_E-we(s5q?)7ANrrhuUfH'
    'lq|2=*T#<XDoiO@<r$Sy*~1dFKdCMAetD`7xP?sxlN$PA>GlO9ss}-B{1fNZbcC>HTi|d6>FmI})L*~=Ap^8KuJgW@t<46u=i)i~'
    'f?7gpn<WsoE!Ti3MFDtHkXq=&$%_Q>-ruGFfM-dlDi#{+^MHw>$7lRl5|0tJh1fVg;7GiB;+>9|vfa^Qk{BH52cMt&hG9Jkd{yd3'
    'R*vUzX}gH)kRZD8D$;-Ia0N;5OMaml$sj&{gA!|22+}cfvl{k=Ks`{Wu}fUYu_Say>@kdI%esG-i)9eW6O512lXxNw^M?5K`5j1d'
    'WP<KEqkmPP+v58P03*G=N+r30Dgj9L_X9v>$^|Sejb6>=eXFbVTmzqo^jtU&cmxI4`6)rS#TDcte%fO^@D~X>a9{(jcIgGbWsUxu'
    '1l?X3<R{{Y4$foZ=e~*1Z81-F8Uz=z{}7>@sq1EBKC*Wj7TYof_$fjc__kc;jcG~$E<y*5Z_-1Rt#8LlG5*w`8(~L@gtWH^5nm+e'
    'Fa=<t)$04gC;m{NdmnsZ>6N?SDt5&W0lF8(s)g5mXH|UHp9{MpQ2q>=x4-Dm;cCF+vz>?x%6IuW1d&T`ZI3bS`xp5++!ctCJ=WY$'
    'l@CAE=U$1#JK=BqtDo=kb1!+79<3*exOE!;ke_>@;lPaK&BsSH_)qn@m-NROZ)loDmBjxLpL>~K1)R#(<tZ<%-?ZoIkD|}W2bo@8'
    '-<9XkN%c)L6@JfUR`{pz+{@1*_wF9Mk>|Vc93owW@q_TIL;aiVoH_{~%pl`v)8|JUz*{E9^!(}&>cpExT!hU^RMI3OqDZY~keX(Z'
    'BEm8_??R7wMv;dx@n7X0z&A1i+|*S%#V1-n8th(RIBhP;2?88^*;VKfUv=!k!yl?RoFRZ(FZL<xxSg_$-*7yi$;j^9gRZ3rQsXR#'
    ')DZ{bQk)raTDT;$#|nE2L=?Fd_bk7P)efUTb2{qnpF;laXi6%WV^zWMns0nPHm>1sjp%!{`o|wAAv<weYg~je8Wy&S1Rhzevn<f`'
    '&4~E5e8NZm+;oG?CDO?X)4=YL0^Z78o54V)y8C|~3$9%b-8LJ=0fzuf+&P`A4EAT6@s^rn{n=YL9<QBm_W5Zx#BiR2??QcOFpmXv'
    '8WOLs7oV>tIhq-KKqNW}dcxQ78C13O&9DQm2;>%f=XvAxbAH|$qbnnOf@w?JhfxeH_r9N>&nxXQaKL-v;WP_eCZ;Ou?P}$dC3Y7U'
    '%dx9=ob6QYR+AMU%aA(boW+LB41w-QKUSPs46plGNGxB)9RC3`e44<F8$0D5AcVJ&bG%<n>)!tPyX1&A7Kwq&6?E>*dLsO{t*!}>'
    'ik)sGTQtnT_|^XBa?RZ-?d0K)WVaWumj5?OpoY`u<MK-pM`GN$K*dpF?o?0OJYF{EGR(sjY{pyEaaU)=POqt;kP@v&y=P+(RBd1s'
    'q&>v$5!gR4WxcRFRbC05bTVI>Jw&MP71t)d@jNCYHgH+qE&4*o@xe1w(vD^9*+0(X-5gDu<S2ct{El(*Ddfne7qgII6yJ4YlT~Vh'
    'Ey#M%NZZm#yG$ax+qA99)fAjIO*^WRvstK@5#st3!bCD}ybgTo;#xj2YPxmb@AdS?P5}wRv|aKzBOg<?FFB5BLBjFA8#Mn?+kql^'
    'X0cvjX|ToL;cTV0BQJiV)U@||!H+jrpKKdbw|yMvb_)CwmK7H#SFI7|w98+wC#{bd{DLX-&j2L9cr&ePS@$9G8o#;?l>c-9(LSr)'
    'sRwj$n*ljle^=AZrKUl*F4T}I06w=>XFgG)Y*W;-S7L@{zr{*$LB>@H<0i(By3Xz6Bo*Gr8)2&j*&+`W!4#?4Rf;{KH|j4v*ZQ+~'
    'oxDno&ns=@%iJ<-Ayn~+^N@(B-cRY;0p%c6^Z>e7oD>PdCNQHaZ0<NcM8|Gn#ddgjcLFS2xdfBi4pZ|jd)k<JM-`7XK`+J97o-%|'
    'Y)NlMmBH`utf`S!y}}Fui3R3it%B1I8X56D-I@ZujCQ0g{@iPkGQ_=tO6^-gyR;NEPxk=j*Xnc4lN>+qr7^aLrbj<>J3pXyR^H=='
    'K^VUmRE)&|iD&!m`49{UYG|ijQ;-(A?eLMxi82(NM1+?-1W49f&xN-T&nfa#pPm>AeH~MM?^e7eIsrUq9QL2@H-4Du<GG(TTcD>f'
    '7P;f<*UwGw`by4o&p%7l=JkSzw662<)yT$|B8FLN?Tp|_a6HE%I%*DU6-LQyu~sPIxF5LLt+T*XWkZIi@mJosduB$EKF6;!W1JPn'
    'KaI#|FX>9#m}C03C;^iG2hbUq<f;N~L*oFMlz*@D5&b>tZh*ffPXG8Q3Kw??XQyq+d55*vwU@3poiM7kj~cK4&nkW$I>*s~(m?{j'
    '|6TD*bA~H6x!OH8Dn_@4*;)%cklSyHUvtPzfL!bJi3qv;LXR0|!lnK>FzJZ!23FZ#`Q+4~+ch8PS`(VkBPVw?@7IhQhs1Hke0sd='
    '&lYtclPto-oZpm`%|ivl=x2qg<L`JhzCp}31}#SrAI!%;A7^B}BZRm~=MR@l(Z^u2uzx=9iC4JLfRKWkLj1)4ulaet9#Braz^0UC'
    '0|7MDbLuV9t-d`8$Srzt*ZjL%hF*x+K<4Z5d1<s+#*<3!beh>-Sah_+KJ=NWGwo%W^Uoaklao^LZiNEKFh6cA@mmb^`-~f3*QG#3'
    '{ZNmHgQ%Ib)8^;FE$|fI!0|o@oQ|**Zq#*|cAmkmFksws&95yL(Kpb`an_$RPG8z&4drWXfqvw<k-nW)-RHj(v3MVt=xsI2c^Ht7'
    'cp3Gq&y$v=Kh{5g_e_oQxHzwC{tf_SqMr?_e4RAAQCb|Lrzc@*L}|BMc?r3P4~pg=Kfo}{^89c#;gH96{?J;-A(ecYHP3n<Q8@Il'
    'uVXdAqeP_n$JTBB4sz&RM<&#8#U1`35vSOQSuLb>8S!F`tlql|)9ise*E2T}Qz00n%$3*I18dewlBMl)6G13oLctnb$FI)|&Ms`D'
    'xjEGH5uMr#z2V!b4zcCU3Fo5sxalA{LO)?(rUp8sX=fM@a)^}3z^!K|#op&&xXvOsGKEV?*5{axY~XVSD>u&{#%o@n7Q^#-v!q9E'
    'G@2(H=rR|Gel^Y1_x*4IZ4?7aIyf`#b*4~1ehcOkpWh4*RF-?xTd(BKPzkLsAMP}4@_xc!s<0<yIT~-<yY7&V<{W74n~WnPYr2{U'
    '&qRRM-E{;g+9(m-^XDRVcwZ*IA7b+xVWsr=TUbiI-q;UMya4y(LoK92DIa)dsdW*8l3l&C2w%qv+=1(mj8;7rD6cpKlD7Pxy^`YW'
    '<K@qt*U#Usq(|%J3RXbYu`l)sJ}35mQ`7$ELb@S{t}Pe{HP%zwC2Yrf7(nU#3!{rXM+;AtNcr>eu7<3hVRt$z2v7@-6xl=N<Wu|Y'
    'hI8F1?{9i0H66Hu+}Av<+0+Posf6Z@^eK@z-CaXp>3#a5-mXs#1&p;xx^w!&4{%zRW}P#PFopaIxN<R<)$cMV0H1w^P5Dd^DCDOl'
    'vbBdscbA;^2<vKxH&)JzqWvBLtwZBo_0=BLSC|?uilS%}B}$iSs>j|&n3BBcIzHDDa;07oXY4x%!3_#RR{#n8{TK<wAv3C2TNdAK'
    '$wOLmSZvcFN{`u4$}stu47oeL<r=w4mwiFZ0x9r($}FDbDLERKM%?WdtpABCfG*WN!x*#OEVflv#S)0>5uJ}aS;+l_5RgtO_T#=#'
    '{jST1sbqKG2sG~<o47{tY+-0FRq>wdS=bvibG)v_y=5a7Py?aZNsPL=b%P`+=I?vKB(XuJ`SqmJKX_r&BhzHIxYWduv65rDxz8}E'
    'rU4iUmx6?v+!}lCIJ=^d9%Y5#I1>__X#)_@OE@6M$#VwOa3<L@Z4MF{Xb(n~TSb27Lpx&pj~>5q#j%nFXuB5-s?Df7vQPmbObLeu'
    'i{uW{s+%>=W6XTAanoQpwt1OA^lYe7T0Z*>dy=z3Lmqb>*Fqw(#jqn^tsA?#hWjKfC9J8A;mqjdI@O=Fy02VzzVe>12x{}xyiHPO'
    'Sgd31(CEnh6Zq2>U?6+&<ZMs8@)Rj)uO>&(t#~Brklqsp@o+ALrjH4tph@H2@mnN6*2WV$oXT!|jj<5kgw0AXOY+W~_q8_0kB`jo'
    '6Cpx)FwHN65B=+FhP4dMwO;iQR~Q=9<LsS6vKw%)=^XL(p5zbn2J(FT${@~X7zIhPYKBt#{G%bsznO8Ds4Ig~LzG=RG9-IpaTz&-'
    'kDf|?`qrH@wNBig-mabutjC!NVkX}Y?xOB?h`E!2*A?w#w%_PlUiEN$9Nj=;g8y{=hU?Ea@SVe=ysA-?ZIHL1V{@@(=n)^|b1jda'
    'nYZDK?$^vBqZ1vF+7!HgoI4yOWYS}$&g75-Bj`EYQzmv#w8@P6XnsZc&8{N5Vp9Ch*2~k=0GEH7+g*!72-$^zJAQqA8071?T8;>z'
    'l#c~DmN4VCbS~`{?$Vv<_&Gg5@OvdFa0L@x`&{W1WoOfkx{LBV-HrAPkY<=O%p~$iw`~qt!j3}lerIm`z=2%Xw1{aFtn_40QF&zI'
    'xmOqx6h*`nY@$R!qu6&zz9+SDgl%9jSFn|P30)Ys%b&pnp85%z3`U7#*DSh~+2|HKyK}yF31tVB@CJHK>*37x+n@yA6=qP8hV)So'
    ';_)K&3rx*>J&gdoDF~RlpG(b6uEJLM3Qp3`G*6`<_ns>WFn*1=5dv&|8phyDup~asCEJPc@3!41e!(F*e*dnF*4|vxI)ca0I2r-<'
    'LiZ@t8O<zx7-mhNfHH*)8Xncab7w|6UVU4Nq9(rMNQq|N4CC;?2Iz`y(EO!GY{PuDH+lY8k$bE&Q&mstJ?YN)wq!hFz&gWpEp5LI'
    'BDwJL^fSnIQ9^iUSjKHsS*QaqeLMdl2!-Rg)&Y*^i$^}vk815Wx^F(?YOWbJ{--dXajvUhc!th7?y0>rkVjYyZN}q~;}qtW=DayM'
    'v{R;>52Y1U5X{`?EUhL`su)2(=M*-4@I?`+P1%pL6aj99Ibh(0JY7dU%sOdD(4@jikDaCybx&zBLD>9efF@bX#XOhUo##=X1sN8;'
    '5XAdg6Bp8$Jui6%J+fm26HVT}^zt+Zl<He5En(zVB54W8R(R_iL{hs6?tHN7BLKC>s&x4?k!p<+?!DK;0DX}Ej6*FW6mV-wS$5xx'
    '-o8F9>HHmf+0rA1wF<6dPRd6ZTCdvhiP-4OcHoH&^0ffxdosc$sAZ-wd$2(Vk)m#sJ^!#*!HwXnYd&4A<iNO00p{rQ(YOO?p)}$T'
    '%yURd%V1?M1dkiTYUC;}@vno3gEZ!unciK?mX&pcl)xnaS&gCBxpp&;nw!7_#29w`72E>U=;&$LT($8q2<U;C?X1a(u7?_hD0|%)'
    '+!(g_Z4`D#V|0s-B5|tuJj_t3n&D1;pviq2P{d>JtaBNsk1QT~+PQ$!H!E`NhO<u6lZ<xkV(inxM;v4mOat0>th<2D(2=%I;fPzL'
    'jbWx>OJ^n-8)(fNdFj%__q<KM+BE!rRE}Ci(rxYc!pPl$E_a&BmA#%iTx_%2dsP@?i`Ri@4OQ44>*#1lF2m=j1tSi+4`<Yrbk;n>'
    'UMj!mC)|1%{JA`)_lP9ODZJOTNjcnmAtz_p9r^LJ*0yUoV~iv(hCh0$6}CSS0|2nBa&<E?bHAAD^%(}~mXZxTZ0Y8siai-dxB8<*'
    '1Eq1yxSuk!!xRF0d28(V#Kawn=Y6AfQZ+Ko3hv>>Dtt1lC8ZN{w+{rGMKB@s$@zbfq9P2J^R9s0z_yV+NjtSZEbd8s(f1-rhjA6h'
    'oA$1t*J;yPxb~X4z_3U{<aX<kbuB!NmPPe9)-$KR_9?aPH7SV>$j*H)X_%y6!DPMXs(%2+y|zY|y5`oI8SaGQ=1ytcofX!;>v_zC'
    'j?hp5m&a6Nd=6ODElM$OT^3)WV)Pb(mp8eW_}`{HBL6wJ2^OU`JJiV5ONCuQt!mm_ooyD3a&}bJ{hSQP;J8V=#A2d_gYZx<F{Zo%'
    'j(q0T3DXOMLvcO#^-WaZi56^+3U~>enPP20TdkUxMFLrstLAp<Z2pkC&eQd4l-c8`(K1x^w!$Pe@={0i<=@#6c_!jZ&Wi_7>v}qL'
    '#qlOR@*5Eg`~ikYkGvqHcmhab6H<9=2U)E>XL4C`1g%KgFjAG(bwE`@>OZD>Pq0^+skhj_?6cKD>m-m(6Nd$DgU{0D*tUuq|KDa@'
    'yd`>##!bgyx!{w|Y7pHpck*fT{KDuuvjEJR#A$||`mD;s2M&LR8K0d@Hs5V^rN)EMLc%nkkSbrzOcEDp91+#y(z8Mwe2Ly%bz2;8'
    ';Jky9-QGOE<0X*h?tExTi818?IqS20bJwRkW7$!|k?v9do=c;p7ZlBi=UNoMsFFwZv~Ihb{h=cK%>J(~QnC$7yf6^g49n<{TohsK'
    'YUQPT*3o#TzTh3tAaW>Zy?a^oYTuGYrS><U?MV*=LI(xtEin2MsYM;@ed@mmJJNyPRUumq5U;3kp0L;Ry*u?@Nl?06ZSEB{8=k;>'
    'm7Q6_K=Af35K3-7Y*CjmQ@d7wl$tZ{7nV!efDo(QNTuGBb0kdnhT91~Y_IKZCUj>G)9a7&WW4p(LMoiq8}<ll$qNow&#mJw8{D3g'
    'SwrJK5^y*}lab;rP{})V@0oSYqbR}|Acv(1d^>O5%eTYyDK!f8n+Bo=AKT{&QGPv{kF-gNi$w`bT-~PUTnp({|6rEvZ#B&NlsPkV'
    'ZMm{X7+~~Rqp%=*-33yx9mD~Ky*}-VLoNmGv735XUqsfcN2|ZSTc&PcGjUxmN;ZZ2V5ugfE88j@;*1QcP3Jx`DwTyk^+(?)Fhw^~'
    'D_}IM$1VB~rfJn-CZ<TRfjdt<5Yn3#46s+9VLLMAl|Js>jsipl0+M_v(s@n>!XB&`Xj(4OMx#@Hw#W3kxuf1dHsT<}@X>%IiUJ;b'
    '9G`ym9v?0RVJlMkPJ_=Hp@&gX<FI(}U);6xuCfY%r<H1R)AKypV_24ER~fF;_2B^1O6GZf8ayRii(ZQtL)^sYX{GL(R(fX5N|ATj'
    'yvI}9WD$0yeyElA#B=_r$^baRNo=lC@8Ae6D?-QpSy22d-Td+TrZAXyFk9xDyH_0zqlSiOxWfOb=YdYK$Bzb2d|so*2u%Z3`cuou'
    '-<y7LciBW5c!0y4TEI^&${-$W1apKB@S(%vT;v;rgnLluo52W1=d=9+Si&-Bo2E4{vxXxdCs`=}_g};G#E;NT?}*DpGjR{I#nskU'
    'aiAbVJtTKC)khwU=LZyWpZZa{6eCM99Np+)U+J#pM2Ys+eXfSs9#4kD<-hl%2I~=mM6Rw+>p53;7~OHu);#}oxPj<3h4KtjAKy=K'
    'g=e7`UW49nM~|taqpyH8(L;9FgIoj##nn6lF0D2qgy1vzDaj^{I>(o1$uL&WS)UbElt7Wk*PWv|o&VVIu$``I?~Q8Xl^eCqNuNoD'
    'NoOV#RXTzJ18HivCZC+}3zP>2o4ww_I3{}(KOs0;O@z}-aS2R)SnVk@6$6(}QDlz4wcR^(#C}wL)`Bju2CtA@A_W1Dics69+n^jg'
    'Vy5^uP%5(zsz1gc4+HJ`eFpiz{eS<D|MUO#|Nh_qum9u!^MC)3|M5S*j2_!T*J~u#@Fs4g-$sweJ<{e^6-U@#U;7TR@3<n7H_o5;'
    'x6$J`I$#kY^U|U}|LL<MATtC6&c!eea64ZcKdK-jO7kL6p9lB%te~f)tFXTRx%VK$FpbE%XF@WT#=nM~ng*Ic?Vp=IO#HKg$v+ar'
    'ALZSrz1O4F<q{@s0`~b7<ww|sw#va73i=-t(o`ONZ=cj~f+FKZXQapY<i;ADzVdMe$uGS1dvp+cu8y%;Zm?G>{V!}!)~%<zr^hV&'
    ';`8*+$ntqoo(Oc&&8e^!$;a`3lV=yzgX)HZxc3}vqSVhyAr_7QC_hqHQ}CijRzaXjoTp-IbO|G4A26Y*?)+jzimWh?9+*Q|@KAAk'
    'p8XC{g!Xg&juY_w=ZTq{CLVO^^dJ-E8Xy_2gD>du-KhYRIhh}I{+m{rM`6d0u&AuY<&ekp^;Vef>P`!Tx00wcX<o-iobo+m&6p~H'
    'C41VVJR4ChZW&hCHi>VdcqQrZV=f>0EaRGSWyLM7f{4kI1KgrfBgo(m0Ee>V{3!BGl1l@vvFJpBIs`8e1*eKq==Ahq=y^W4XzdPg'
    'm3G|vtScyTl;}RvYR@ayiHLmrL~4t=r)#6(vTN+2Bc}D=4ew@|EsQSaIaMXkR}@V88yrZRj~-O|nA1*ZT17DH2yZ_nXa%_~FYQ=`'
    'U9%wg(M7x_TYiO^wQ@z{D<P^)Q{vZ6dVM~u1+mNsWE>KfD)0~2p18-aDE?F%lW>jaJ8jhq>T}OjXMKB}7Le9p)Ur7UpMij(Ucc)>'
    'oKY7bsCr!qJEfRUI&+giCd|kX&X0F(qQ*L+V>1?*FI-V(qvlM}9Q`L{_gDbbUAD=F6-1)_&`pC_5QK27Y$m*W^ok-gz&WiS(F<@+'
    'D3JrEedcAEWvDGr;fONjC9FlKnbQ~O#9H_VvE9IjLGzT;l;n6#gf3XSh;Hx6PH5aymm_RK685m$j<${poD)Ex@ur=c4VK-TBfP&q'
    'b<lBmWHoTbMaiM?fWG>k;4yV-o{(HOgAAkRJANU|AnAFZ^PKA%%5NlSVn+7Qy+yVdJDI=GJWqOX;xV{Xx#sfN(|3&$=LB1d(ncT-'
    'sgrm&HxZ@`2sQB2T#DVa`^7dH?}lwtXJ$0+6WAKp+`Nj$o{ahzlC}BhKmCeq#M`4o`_?xzJhGPb=^O*ym`KbP98P;GiVpP^?GQMX'
    '873ECVIqyGusEv3uZR55_z!p!<{D9^Tpt#IO$yI(_9O}*l1;<2O^u>Nndn6dE$%G+iuubKA+Kvn>n2RwrN_?txf8{2>4||vuiMmz'
    'abzXSwbe5lsk&YN#6tL~CmR*C)BGDKwnuJ-^t~=7DYO6oG8Hl`q;2>k(64QOq$-``o<cRkG4@EO0rJo=eF$#1KT;LwiaYLWQmJty'
    '^yH~HDDt71f#&DJH+bS>-JPO(R4gCHL6hDqO0ELmzd<~UI+^0)lkL5Zmn@JehO5Z5j@q0`phZ%CT~D~rM!L*q{Aj;Kw~+c(+<~w4'
    'M{l?zTGH{i>s%|y1rTR6Nce=w2ta6@-}Av}Z}RO!=X$??+7Z9MjJj;WbA1{RSum+Yhc9s$K179~=ze`US@mHMZg-8}%5WxZMouWx'
    '$KcC@qvm^SKg8jxeO6|!ttX9Y>wH{ffv!d4_Pys%fT5f&Ua6@>F#~|pL_9dRUSWo^2u+VF@}It?(J2?jjoIhbGQ!L#qWs`47UtxG'
    '4jDhJp4ypCP>-=FTAv_|bxb@fuU8ag0g&l9e_B3DY4&g-<SewWux%<s>@nbNfB7^fvBtErD$}<4%?!X#5?0d`T9~uXFz5=4)z375'
    '2*v)nR#2Q-VycP0_?Jf(Pa(3wn}^-<{GWq_Oi=QDMbS?=V#<d4^5@H}Afg1RhTV@@7bDGvX^pwg`lyj0;?0FEnN@~5XEdOyo4r<H'
    'Bm^*t%qA?1@2l2*Lu4*oKy?W>AP5k^4Dj#kFCX`POZj#%qJUl_&9Og^Nk`#!@axOrb(75`Li1*~NBN)a%Q3b2zdW?xkB+^9o-G&V'
    'ME&OE;BS_h>NRybzr0LyKj5Wc*N?hp515RpLwly=>w$`>1KTulU8_v(6CEQYAYlhM5{LGf7XM|<+R_9~HeS%v4I(>$wpgEbuzRAk'
    '%=h4Rj_3Pk`ub7Gk$_6UvW?x7FV@aTptYcBDhy=|(D>$Lo-ZcJjbPlwo&T@Z%Fpi?(1pmrV<MiqD#KMP<GAjBTtAmnlR!xe@7itq'
    'tyCUi<4)4QYCyPt>~FR5B(xsac)Tvw#!>0rMrHJ8xtvFLO&v;!lltpC{;ZeNkrftAw4M@1XYRLx`J8gtW7mXoMu0Ka)BTT%dCJcT'
    'yV7Jyr9Se%KT76ae>9*pm{D58?Q6k&8TsB!FJ&#q%=UjPnCC+?{n&JWqBJDm{G(z%D-3KscWUS2_h-r6Dk=$;E=V*kzL(6Gv=lKO'
    '0&{0;_N`>To_`^`ZlE==y+2Fl6@)Q`uH#2s*N>XHSJ<nNccZBKzL(4wSrCvav&3=NeXW=;{)qe{9r~n+zn9FN8A`+?2{?|N?pw*+'
    'O-G}CZd^LH!Pk=6jdf{>L8c)^{-~K-g#kb?A)?>D|EQVQX*|;A82HNOzL(6M<B3{Tji#&gy<~P}ZIR==BM{rZ)y%HLBPK@djQjPo'
    'YF?){=|d(LA+G<dn%CLx%8j8As^Hh6IiE$e7<fQs_@ioGQI4OqwZ;niUNrZp#RUiWx^VxfnfvG4hZ}H1FtAbnQ8Tamt1&f0h33lJ'
    'e-zE1%WyZS_m_c3epJopx`B~TI9VN;|9-8TlNZI&r=`RDy=?CBh|<T8AZGhnHs7`SpR7zXS_<)BtLBSiftjdwKl<(Wve|Jl_6y%5'
    ')8G4R)qJ6y6VZJ1gjpzkEt@an04U?&4<IFfuba0|7?Eh=QeDAw{$4mUdtP@0Dlr@!jot5s^94?kn<h$TGV<RF=X-W~F0xTxD97MK'
    'U;B^B`KYKP&|s7d`OBY$bE~Kw-k<*lSLLdRi6C;K!5y!#sH^yeWF7DCh4bZPA)*yVF8{edE9ZNKp+-<YF=D@dl+G0elCn{qh{XJl'
    '%6UZ*N<Pzl9eeG2<t&Vt16_yl3h(QC<$P)6x<)w+jViJIQ92XW{9i1c`|p`cd)2rR$Z!EDg?}%d&p+Dy7q=_WK$gsrMEzPjd&csg'
    '*+d4j`m=bxDh##vh~~~?7W6Fzwn_-j`R@oG$M@p-a?bF&APz)Y>PPXs7SkD)eoo7N|IGB)yJ$gxB)8h%AEk5u%ZL3@h5Y(zO>bAy'
    'K2ol~l+J!>)ZxN-pT+La%K49{c06CJEwA91a%x0j-oI4NUZ~-R94Zupztn*jD+zq~BeL}GUrOhOpmVf5r`S;asGau;%k)f+NxAj;'
    'QSaUr#%F>M4Qr%X$$lxH+ha=;J2>bNAN?;MhhPsJEejhD=6m(rfT8brL({Mv`P{eixlvz2gwX!H93o#ITZ5v$)1HcW<NdvUZrEBD'
    'lA@iD%C|S#?lji6*axta{aQaaf>o>;h`cH)|0thV(EWtdaFXVkRrb$yD~v_^EH@2Q{;ZzcUq0>ImdZCHnvc+i`Tm#c+3)05O_uMD'
    'Udh+;`R6nHa&~zB6Pk${r~&<F`MiIBo4?o3$66Rrcf8}lFTYpM7FlQd#@q;1?R)k7WyyXkdB+Z5jfl`b4${`YR?lB{(_cO-X4XA-'
    '$tYI8m(O;3L+UZ%zn|G!{(rK39!19Qmym(?twVzaI$rOe^|P$>zn9Pn9B@Z%jDFWhoWEAk=L6{Uf`-B3w7*o)XZ+0esZsZR*gQf)'
    'WjNKr7XR02bK6KF19u;^p=D#=isweDJpjg$MUhMWvv{tP)LpQrY~Eu@_kG?x!Xo&Nu!n<peJ!7xfvt-sfTMku2S4Y{BaHAV^$rEu'
    'xLLjqoJSafCmv#uyx%9z<F!)RjXOfT;=Y&9Z8{_y<AXWf&)4#~X%OvEkPPSL`^33{v4P<-6?epZpE-}Po~1&SgZ10j`nhR6!?Cq!'
    'mR#re3VMWj{EFa?9sHLHy2&wt8NpZf`mjGM=w^x<(w%<`IQ+GQZitjfNO@vBN57WPEszZ71YqLRzmJ_;RK@dT(eC#4y@+-w`$+)O'
    '$SD1L5#0bh#=_y>%fa^kRz$a$cyzdiEvjhWN6*ggar#r*h$-dw$+M`W#`=|JvR{kn+ylEth(Ucn`}fhauyJpaOF^(3PxfmW?FY=E'
    'KcSOez>FWW=N3*ngxr>A)W6T3TQr*IsGgqSUxv>uvIc;P8dS&k;j^ol{N~~D=#_o1q8pi=_%W+nK$X9i(bgkcD^0?&;lIzGZ2*cs'
    'GGpp#*Y_&A0aP4&*!}<?&-W^NY;+XLDJwhf=s&9Hm3`3)?A$Mb@}57d=>2mb$Kcb+5`C;cs_5zlp3GGPs~Ud;^x}^ydLkf&NgSsY'
    '+js{3dl`L((hMNXaUoUc?`8CSo8u0HrHnz-29onf8QtdTc+zuIAdfR4$|+y#Xi=L{<{m-+<9iuBqFhG&v?J|%d@rNVxKz;1zu0hm'
    'FQP{fL~XhPEZ4r)(1OkYnHfDns(!1XMICX|jbhUMe6OL;2+-rboYwRCy@Wn>c1c{{Q6Jv^oIa1e{l8d3-@hj>XUpqQQ(b1a{m1ax'
    'uly~0=}@P4Tv?E8zgN(HE<8P_tnsa968v-gJi?d^Zaq|6Fp{tHXA6XGE)m1~_{;S9bigz~vYoHnasFlcd}88Z4#?M#0{${969*%2'
    'eic`guhZu*pZ0Z-mv2YlLcVI2@V$igOAqS5#7M?^`CdYQd2HXN&spW1AykNOx>(<8=o4T`+T=h2KK)BEcwVMlC}zT-*uEFhBhG5l'
    'OtVpY|6W9oFg(RQM!v)|zE{0gD3mB406swHUy5j2G@5Ypj-=}Iw~qr%)zD0~`n`xgPaUs4L|c=(??v=!-GmJ?a!Y-p9}jM?Fj}Zw'
    'ZV1E{2;fH%eIEZlQ`(R)Q$QA9s_0Xj6WKIc1lSs1%jgkiy5(wBM2)-q`y6`2jq=m&j^Detzf{t~cB5WSeX;cUK8ODDao<X5-)@Ix'
    '0>2*L=|?4fe}3w=(crvj!k*s?=`YXiOC^26yGLf5vfX_=UkA}&-srbUwB><ftvn?;`<GhUTB9F5c693#*YT~E{<3nv)xS0ZnAv_j'
    'k#G50OMlr^Uq9=LO%8JPLrJZDucc3NUyKr>-2MD7SJIc1221%!yZjF%)E=c5Mrm%-mJ=LITB#Y?p0M8jt6+Fx5y6kW&Z9f45>oy='
    'qv_vf>LZLF3#pPbOk9f`a{>y?p)wUvGqT1l2t@zhaz<ZFlD$M+hUq9V;<%;IRo=G1<unLr6@mzk1SzUzR}OBLz85TYb~EWOJLXFI'
    'R#7D4ouOKyN5bGQ=_>P+o<0Y9raF>w8b=j%(7Yk65(u9QNffdVAyuL`^U%89;PA}CroEXSr?MP{v@y`i5jd9ob;qKuohuAy?v5Zu'
    'OJ*P+4RPa&eM5eLMiA-uRH%f<g-y?qjp4-P2?!%-!8wb|)}BA=y5Yr6hIk6cX=GifFuG}4C<!B*6*cLo5mub088uVZR%z#6PHI}H'
    'cPpQ2MISyn=`?O1`LvGsNOI&k>Z|Dzs^q}Oo_ivpFf?#;!`rT?@uIe9+r)uF*f_tPe_MPn?g|?RLNq!#8uVNV(T&_gLb;}PWCQE%'
    'q%HSt!NSn-Z;r;NpHNY>$_a|^E~~jXR3SSbzP)_eTAU5zvyC!&=1NfY7}j7gUvu5IK-Rj}4U?WiwuN{-?WeExaRfu?zL>2%wZ17H'
    '&~XLRT_1-7fezf%2bl^G8{v4#9c(sh$4$ejc8_$SQFwOW9bW4lZ|`}5i&HAF0g=D=O1N&Kk4gUC>l26MVg!t(c;}AUBbyR{!t~V8'
    'CDBQFl=E#*V%uSPpRk8zC>18{C8ka4@y(~b24dh(ciAwD!ic+$$T07@ik#{In<IChmYSk4(Nuu*>?LQ#?rWRMk8MS5Au=I7!Lqnx'
    'w2rtB_iOTR=AR_T!5qNG{AZ$hdnPbNe9W)p)_q3I5^{<!<(AIu_;O`N;E~Dy9Ruu^GQi^op`qC#@wMI*^Hv;-jbd|;ttskZD!*gB'
    '_anvIO|^P#R;RRn%b_Gfy<1_IuYLr%o1u{|r+(-7_ROpA3X8lXMqEl!Whs{zQbZWf``TAWcv*2qIIlEApPqp=DTS$`Ana1a(Zp1f'
    'JZfPmCFLb)*=gFBUPM&KBYYgd_QTeYtc4R~oiTCNI3j>DvgaEvE(}wc{k2JB{&QulMCPIivq48HfYY~4HSvb}_w<<0%iSI|zo*D#'
    'GK=(cnvN<bx*H=)NN0c}TC9oQ<>scXJ~Chuk4IWDTD82D?)Y9@<wVsYQPXLEa}quiCUw+8h1;9Lloxc&sZ~ha274AemyjA}-hGyk'
    'xQQIyQ|KNUuGYrR!jfM>`d4+KQK%uQ7k!f82nfxM59Eh*&ogU;QH@2=(jyK6OU<jiZ;sP-(MF4g+v3D~fQ?gHiX6=|{VT`yzPEJu'
    'UbN`Iw9Y;HmUKOic^+J$;GBj^@9ZaHI#5iCf>tkE`>XMejjXQ<rl-#XHLNwjyLw(gS0Lwi<UTCr{88rVo5TM!f2gn?&r#Hd13pPu'
    '3zwb4&1`_|U=?5zq5I!3WLHEh*m1=&=By~?fFrGQ6U{ec1v_o&wy6t$5s``x#8j$H-yH~v+RHtO_k#3ofnv2=xB1Mjm^*AaY@Z5y'
    '(C8qh5luyr<iOXHR7~wy*f8>t5_;F>^-tJG#BiX`uE~@a##Ip`39h2&o!f&aH380EXN9TO-RqGy$O1Caad$+gqN3g>EoxM}D=Rym'
    '-!Dn6r|dkg^t^b{%44o81Umg!PQcVFr^_`Qjn#_k@SgSkV+AnEk!05uWf*gl63FN#VOK=>xI?a|F~VkJ_}~d}=ljQW<0d7Gpf5}*'
    'gOeNPu9oL|wy~dTPo*$0qgY8gn@y)9VSBO}N+^>}pRfoiL$;4JA}fd*H2TSNeE#IlYe&Lm8z)A0fQj!txgdffG4Buo{LWjV`b`<2'
    '8I!KhqVXB^=a{43x#j0G1dsdmBhUI@TqX0$-za+$Z=0~k9eh^44mUs*GoQvIvIXFH*Vo6BkXFG@jjeO!Wpd|{e-Jp%`U#Bhj2zYx'
    'k)!lEsfL>$5kGj>JMT0q75*(ej|byb?`RZ>Z{3`iELbL`XQgLK_|KE?afy20&&s|iY>+c-vr+h@=MovUDM%|!S1?$!eg`BR<C_Lw'
    'f2`sno(q(to9WOtC%#No4(-=x>HrBt^}TIi=6eaF^dQ9{aX7Pc`}|0jOuqkW$*CS5DHLYzWdscYjQTpBSLQ`wWcZVELg#G-N%roT'
    'Jr%@U+MBwU#^X9!j>rnjEskqeN00us`zZqdD-2MS!!`@Llv<j<W8t}#>jKaY<=IC3CPtLH7*A+OmnXfiV~Sc9S-U-o=sjk6*c2D-'
    ';PYOOmJmHp1QUWYRn)7IdFI&YWqKb(Z0e!lqV_gRH}F!&!7>&cuhVMZ(gs17`zK@ratLu0kXNnMp*$i8zRMx=aYsy&nreEs{=`u;'
    '<|-BDsxOz(M^9B#kN5p|R^FrTd!8(hL-NIAkWBpjuGOu@U{myHhbA|dVo_K3U+2ZsqqNr836U6o5=W*`lEta3vKNKq_)bs=YQguJ'
    'FJEfDfs@Xe<K9E~rJV&Ow#}aDwZ|im(8W2G5yU+Ka5jRay(KxP3VSgkc$B^K^gA-=xk+Nt{+?-fT(KNd#~gd@`OegNSbNr%ahb-s'
    'YurB5Fw&m@AjfIgBRHS=fgJ>sO`yNdEWExTCS!akSEeJO9RzAN7n3}j$~J)zvrMPVk;9Ld&t7gCot&0>A7y!DdqFtr=Ivo&PAjf)'
    '@UY1VvzfA!a}6pITrA%2S>!$LB=mWoJr*}Pz7e0SK1!KKg}L3>_Zp|ai5e;RNqL;g>xxo2$v-owp0~;y`z~5Vb0au~9TN&)s(qpk'
    'HXa5PgbweDO12b-r)v(zsCa~B2YI@$C@C|6WYFA1wQ0&pb$7a+$Q6V4R*Xew+ZQA26U~INUDg*H3tr{jS^LzFBy4L?;viUm5(ocC'
    'zwnq>?8X6_naQQyk+3~z4Wl@-3i%_`dVUXj=aiEYcG&JA>{3^{Qx04&^8&IyW#l!YM#>4h>OXFiSGrLmk-^{c%7mSzamv$nJ`U$!'
    's$W?_nZCK;Y`6G0w)aVzL$6jh^r+5+3FAb3U2?Ul5^#dkT#@FUcCH>7Oyl^Xim)e9lzYvUDLm}!1^DCeS!1<A!OOmmI6We`Pkihi'
    '*%flbtXT*@CCl$IlO{_yEgr(+-s2%}zLZQT%5YEm@ok<#H?Q5M^L9|$sKrPc?+)mptk0suH68<v9DZBLSYL`?MyADh-Gd$>`S~2_'
    'CT9VS6gOS0$CWcbjH;4(ELB2sS;@GKv~@SLJrnk(-%MCle_)mt@zn9t@A9#_qxv~=Oij@vm67y4l6Npj*L(xd_Af+%vDqeBNm!S#'
    'neARG;|ik%GOpnk^Y4UZd>3=*x6cmJ1BPQXL8Wv%W;Jj`6w!*`%bnsekdTQ!I0XAF$B5ue*Gc(dh4I}{#l<AGG$c;YQTCtDT(%>O'
    ');I0ai|$)8<wzjGmAkB3g~8V-xA3rgGBrCzr7t_^>yHM(aK?;GqMYPhf9VR`>Z&MSQ3l~`G3OSbH_PaaUi<o;1inHjk^J;*s2)e9'
    'E$X~?g>_nTEq0jCYY%I&q!;Xs9qVT*SnqhSrP9K|kW~>+e9G*HvieQy-ss^;rJ^OcB@K_x?0Qo#RaCN$;2P;RoJUmJOoz95a6cqe'
    '_hj&FBP31)uw#RvF5ITiVgMbu0nuqqTlUfHBmdFk6StORlnlt}j~|#$I=hS*q1YH_Z3Dikq%Z*;=2dq`hgH(_&dcA<lMw0Njq`NE'
    'oH<*(ddkFPY8wZT<+9JXT@+T?eMZu<*9O&XC51uM%JNIU?T-4e)=r<dutUKX;}ZoEFf$2VTtwNsRSqVM00eCuMmp)<!4}2ZOgX;7'
    '#>s8=4)MRgX;t<#Id6!=ajvZ2;AUXKLpm_I>jmn?9p_0?`}0?I0ujyj<Z2R?_^*Q%j3oc_?dXVRi<0J*y&5L4pVFM@pPxF_JI5E<'
    'XBedrdU0o#dWBgnujYuQls`(-(ENaWWM#P?aO&*W7ip973R6b7jT+?409Z5F7wXSDU{+8w5F-*E`@UY*d%M`_!X3xGQdbalnQ5yG'
    'fQ0k`$~E$sttiuX8uOkwA@2%1qYSS@it0D><ydP+0kc;Wnh=E5c2qMvm~6&(nC0u3M=_ITqKwWTsn)uAZQnCxy7eX1$Sxi9omm+0'
    '36+zM;Jw0lheY3sqiM}bK>_(p?K6#c7m!k5Isi0iX*@Yy2v_xET^KEprt^#gX2PB*#gDY-p{ubru|D0nuZg~8)k5%TwQMr+w@!qE'
    'LeL$l*!#>@Az;n1WZYF#9Z{IBa4gHVNQBr?Pb5C2634uyp7?r>gNTlTR%rGoTLhW%zPfylTZ$dJT`{(vvI(+!dF5Uw<S{M5*nd9n'
    'J#jsz(otONz4}LVXd|Gd!$4LANGQhF4(n>|5{DW|Er<ow_c7bfJaWwCTX`D`d$D2B*O=Dz*>-krn~P1Z(9WO&LTmiV?DW8wZu*S@'
    '^^Iiit*~+YlkQV$^Q-PLHSeiL8J%4fmM&s<LehOs*O~Acuompays{;{TF&E!pk<aUKc#wP)pfHfEJ=e}Rnc|jzUZ;)C6~VLs7}}('
    '#vtNyEwC>(yI1Z+#xE6S?%-D9!P3)rMi^$yzN?m2m`M{|c>=2wYi3_+Wk!;CzNtH)PYq@=Qn@~X1$4tV%9d|M@kruia}oJEg^e7<'
    '<~bwum#8PA0qu#1<uUWoj)Q92JPw-`^~RW)1Sz(B64D(4<2I%0^PD274yVXS=yse0QI}DuVMd=y*CR{$cUq~%uPH%Xsfp;tC%0FS'
    'o7z|pd^g=Fu*aJl+&LCs{^E-xpRt(JgkYlv-kmz@gq%HB7?+>RB|_zGcIG5JZ~Do7x;ed$iO4f^6MT=^XjPc=-ZErL)Ja&ZheC%&'
    'IGeWqnhZpmS5bBZ7AxnpV>W>2l@8uKcks*8_dKJB+cWG*I!Y@2B5GTw%bQv*_#EKw{ameS;2`BpeHxS_1<7<)o@z}Ww&qLZV9xkn'
    'dg0u-JSX_bncGU4$r6n1Im6`efF#5Pf*_LH25YH)-^%dorN<io8VHLjb;AQnL8IA`Fnwpoc?@5+`PRwS*xGClj};be`EldM(08)E'
    'C-fVIZt7ACbJc3b^2*xNgmgAC8enrcOV5|7r=GPr@;Qrj_a(SuYRFzuWLO=x>byje-KHUG$XTy|Fe)|jErt(0VT|5DJmX}(!VIT#'
    'V)EOz>24FggHdwzGxHZ+G1r|_KJ%rtH6U?!y|MN6S);NUxpVaxL!D@qG?d4owmvPBc`AW=^Eq5z)hexou?yFSksxE&NAb(zW?F6N'
    ';-8Jx@UADz@b&bcHnec*ban&HeT%umz)TKMis(EDqlx(#b45U9z0Mv>kD&Z=I+B-!IVB1|Z@Ur2_*Zj1(q?nSr!T^4gJ(-cG3hY^'
    'dY^srPoYvFh;t9DzsT<HF`d6cf{J()jVVJzAkSL0Pn<&o$;sp^d47z(qflB=1_81?IL{+s-M2JN-)&l0i8?b%r%2xCUxd&<?=0l@'
    'tbJmgv~k$W9l{TJLPaI3{nW;M?tmhm2%DxG&fw;~<8XG)qVtVu;~r)^Y2<m)dDTjH9zCtX&Qv25EbdeSZ>FCNgB5KP1o2`Ct5z>9'
    '>*U9;OW5vvfghiBv{Y^odE=^h$QsyOtxfidus!Twzw*BFGhKYF3hx|Eb?S}pK_Nb{kZ1mY^G(?Z=KhHqdzHjG50vegV`NQ+O@e#Z'
    'x-i(;LzIVTokM92OA}4ai&_}uHNn5sLc~()4LGJ={_C~pTBfNQXJa8S?(sIq4N6Q&GxAvnvNrN~caFv<3;T)rhcaju0WYw6j5UqS'
    'Mv^?YFT<#Zn%VU^+dFfapgB20&i2xH#ar6z6Tp$@f9z>|Q3lSXpB_VtK<HNYp#y*9^<>tK(Q-=J$*0^UR=z7tkt&PwO)^DRZV=z*'
    '9XrR9^V6Kz;{!;D<N)0xyD;9$SW3_5yFod`^f3EGA4=H|7WGu`E<Y5g2$LYXooPrYDh{ovX~UGqHcjnF@?{L0+*kc`Pnq@g1~Rd{'
    'wCB@(Y*SV{R&^r{SqoBmX^3S8^X9wVRACvNymuAEE?8BD!jRW<?j3zaX25I-uk{n)f{^=yET5A!KZZx)ebfdG4DpWK+vUwBjPSyF'
    'Mf~Ebs9T}HcLc#;j^%J%2o@5MSj(GM`z|?!2T7FHrwq^r?<?DIU*+hd=A5rjkf0HUKI@=8|MkaApyf;VGjCTVZ<bn(@?WTOGu<;o'
    '^}8B|SJd4kRkPrfEkzlU&B!>a+XNX*0~~~mS{(<!gHEwVU7ZY*Azgr{uD`u9G;n@;$p=C4WS9nZ{@RU5yAnB)X3aIG%!z0WMs)N8'
    'O?#e|JR<q%SEEPOo?^t&gVNnrBFg@m#x~=Xx%FnTa8vJpCOU>~Pc*_^yEBvCseK<F4s!Z@9wQ7~E(3GDvnixt+X2ai&`@D}IxmJN'
    'P@cKSI@Lv-#kY1ccN`fN`o)vK8CG<f&Ia=HSdKkT4@?s_H;0-_Au3Ngu6IQRL%oMHr(@Wo;!Ql;ShdX!I>I(RxqT`QryP@lTDiJY'
    'RogMl(G4fX82+k4<5EJ~K4%r3(n7e)0BG!i9uxNff?$k}RiuEl(Q7x(?V+Y%xEX_JztqoEWbS*MMBzfy{Ib#YzD{_D^+zc{a7x<X'
    'LQ?4lZVga1>Yn`*W}vsn>$0^8>Uy$;fyno^%B*A-Crl{om=xi6w3jGIuL?>R+ubI`miVQl*S2+LhO2n3r#lJ>Srfj@j7uvlPZFkV'
    'y;A*}J+*#-T_7`BWYm1d3wkRG_W>L6a8IZGCDET4nQ;t%790G`t>1%tpH|3`X@R~%YisFtUO9%yy+`fpfIoa3>R^s_nBrc7nd@d}'
    'IEo9nMeNMFx!2}{|8+%c?ram2$if)j3?{R31qiJ@T^oAx6Y0ycTk1qDV^-p7HyH1DLm&II#>!V*q2XnJm2M^^DN^V3xiMp5eHm}?'
    'RlCJr3CqTrtGB2jjE|Y@vZCS{aVG;HtgJJ{+j~}gg-jbqa|^z9e3(8;-W1Ok&{|i*N<3)e@vMf8e=>_V1yJ-!-0yX@kS=Qs@`$4R'
    'Ge@A9!TF2Zx~Im%4%!w9=16<jw$@g~emYks8I(nrJ6@B70~gU4nS^p!Dd~n?x2LoUc+}0sal;PX)^&i1XZ8rb?KB8XJ=zA>6JNxu'
    'GH?8r7H&1~(rnR@JMXcanZ&SJ9|h{q+VP%RsJz8vvGPvQ{uEo3U;L5rl;+_9%5!DvF}X0JlwDV598l;viloXQzR$7#Ak?S+jGXk0'
    ')C`*=<M*+D-bwk|wtu-EB+uTqcS@kKWk4i|ZN^(+mztaEPK(AOPYS*rP=COs6-B)sxzWh6rJ!N!VjOJ5G?f6hJ)E`iQAdjrlCV3F'
    'uCb%H>GLM)&P8}m=6G%u7uyS3Y)>c378^BeS}J~5?kJF%@kkxQlMp__)Flkulw5V=QA*8;NHi&7N?Tyx3loN4R!EPx^H)|k(doi^'
    'MrQ;>(ISMY=PhoBWc>o!;K&|<wn2N6ZSum*JeVcfU16qhkN#hrJmjR@g3ie?t!K+6{0<3{uKSw|fL*{Am#}NPHVZRRd@&0l(<VwO'
    'g598urB=jU97V%HdJ%6A=84xALi<+0q9b-VCt+vwg~B|UzVV-tE+<H_=u~A<MooXt={Eo_uBa1Cd29g|K_1FD`a5T%U_sNZdYdeI'
    '{u%CJpkE1cnoN+OFL9b_D}KaYWsha|9rN+@n0AJVco~ypxvN=mNW&x7OP+wm@h>jsGSg^X7~!vxn#4Zz{h%MsFpl$`K1^f(|7#|t'
    '1n>sV`m~E*1wc^I&-O!B_JZWgO|C*_-p~VA*g9v0W%nL{aC^1V(vAbbd1oPbOqYTipZs*0Pt0h{#$L~2>hbY5rohjWSm74{fd`?y'
    'c*_w&6eyXKZ2Iv{FspH^oU~8t<dG8n8;b>V-P~eHfpsZUrb@Ca3}O`EV&`^0<*O$f9XNDCV}uzBvvgx2SW<`Bkl<2gT33aEc%Nx-'
    'K2IjG&SmC*`{&f~VY%ltL3VhGaq$xpIQ5R&oE9c(LvSD2)zcGn#`a7TPNTYlaIx4J12y*vfZ+ed06A>X3R8#)h%#=Dmdg}~sn#(q'
    '_VQ%inEKY^Ikwpe*Gh&09FO>2ZwYd9Lr_k?c2BX9{B&EyKMo>L^O?7E8p+AX)ARwVIVS?e^3kFg+YO>7rFz)8ocLI99BYjc(|Eu<'
    'C3G{B*0+9$Zal|YihIy<L@=K)BtpmU(EevUaBKb3@IJ}L#sWAQH!o<q<1{eN3Ol&lYf|uY5!K>Qs2;vb>mz#(iKm4xGxPEzGIwVN'
    'wsV`0F!>s)5L%<_kYg{0@W4>csjjeTqL3s8TkO%#<sfC;ujP!lUnk2brd3ZHAEue*hueHH4eWK6F;#}Ek$gM}lJ?<(V}m^FSZtvZ'
    '1D5CZeUOxxiQ{V@br3&+&W&sJc_%899>L>4I*TZ|A%%Fxbis}{K}G@L5E0$z6{S{DHM6si8XVA11P}J(sNZKi*Uu<9G6_y10vC1j'
    'Bf6;|uCT_+LLVO;Ds1-@VJ0xg@wo`8Lh3rXfx@b5I{y%eFj(u0ffBI(Gv=RUlG`{OY~DRoVY4$FVUlMO7P+K(YX$@7`erwhH*_$N'
    'K`MYNW9{)zU)M>i`%+7g%kQRI?GxwMBJ;zjcU`_3t>YK;DX5-Yc1w&RblPYM3m7Ys9(<2eC@^er9LQ+zdYfmAzt~Vwb4j7#7&@mU'
    '`t^C|U^tW;wh2@`f}tPv{(YBbNbEd&I^62B{;3lP)C6SHYAue^@Ww5AW4AHO1jDl%Eaa@GR@Scg*u3cG0N*e`bB#w`TNmqYCJO)!'
    'Rg|f(Mb)pY<u=)rjH!^xop`6OGeNIMrpNB?;^gv6qs6OER`JbJ0TRICQaxR@g)Mdoh<BaZ4-1Og*v33?uc%9Xp;3i2n>RlyGOjz%'
    'v?;DISjRWxIZnl)OI;b90xz_C9aZL_fFRlh6PBTXc104m+dfB{OO#ar1o1gJxwbTqAzBUVO4m_8l77<>4cNIycyS{EzD`><tha5s'
    'EwzTsvd|0lH_kfX$*qi!zhlK2d^J5HwptK!>q>Ei;`c(n-VumEuGx5*5^-Labqgc6#oc?$j;HhvSwYBW{!Ba9c*vS*J(FvcHdg>Y'
    'i25u}mQnH0f^U7QH0@s9`Gj;hPwtm}IZr2v>8L{|z>|)fTma^9h3QuFE<PDb6x2WZ>_-^Y6$Y~EI)N;>&Y3!<V%Vmjo3JAo$)3Ei'
    'pZ8aUr=ZlbZ=iMCb1jIcyiWIT-ik+Tq@b>uMD>}+MRLP`+EyNPs2f%C^Z_P_O#Y2V^Flhd)aVIg<I0QjCJH7Bvzc7$Sf=+U$l_rY'
    '{iZ6Cp}qIiYrT%oM;%%JI`G#7=z(b*L0WJ1C^oV$XGABCRfmBykT@_FnNgC}s4B_^G%PX<;_IUxzveJY7?3g-&*vk`^2AsdVaoGK'
    '*b$XOKx>G!IU0-dz^I+@k0z`8h_$W<e(h6LM(Sl=v6Fau<~lp%p(eLiJT*wr9$K-<kX3EJp2mhNvu9n+%yBnUhPT@01n@X8t<)^c'
    'b?-L0V^THm{LWyi!X$NOfF=h=!U9VKmNxO+D=hrtjvDgxnIdyx)@;{>o`u-a**(4~x=;hISz<+mHB;G{a35e=Z=lNKgqclZ6>nD!'
    '`+Docm_m#dWs0ypg?xOXj&w{I<%s<^qog}PoEluuo3hPD^jTp@Mc{uAE=g^G)FINSnY<jdS_r$bgF|G=czawUYRMoQ=7;g^bCgNv'
    'DORaaf_WqcQ;kPaK!tA_S89-yJ9<K}R`5CV2fWexaWKYq;Gb#o!;+fLQti2udPO*A(zyLvl^8>?y!V--38Mo_`WEOjzw=Jxm&}h+'
    'I$<cybbchB@5EJ)1N6p~F!Gpp#W_W>4o-Q7kMjrQBF-P4V$CN>Bj2h!yUzkOjP+{6GCi8dcEWTjAF5Y(&c?C77^iER&c;msq%nNl'
    'B-#7S;*ZhkIAmY!&ia{(B9Pd9+TvJ1py(Rh<H>F->>#7?$fhB@vl=zQ1J9MN)f=E)5#SaqOZL+l@w;)(zS}fr6gEwEXdLN3>1)Vu'
    'bc8_qdPN0vtC%#%j8tDEe>JLMh`_$W4tNP9t!_x0`TPOGqlVb(MOhq@{(eO(YvEWy6`(FA;y6)95AKhc_Z8CY8(=8*ye{hsiv(00'
    '@}3zsexRf(T2QkZ^9vxu#zxl`xu!{82KZjqI3m{LP&ff)JU|VZ#6kmUseyCPO?;Yrt2&`!TAOoSZ%&OHwCGu3u)*WwqoX)KEl>hR'
    'QFpa!g^hHw@3B+uk)9o4QGB@IZr3&-qS%uoIQ{Q5?pl1!eRlar3u7t<{1EU{qTn<ApRI@@q8jt-PBXqmgdi;zAHBJd=JGf*{u$c>'
    '!fT6`1?@sf<UzQpE#VYeJ7{H3=%flt2ms&Cg88Vh&;Z(DvguX@J>c74SUA7rRnjOKN3@Rjo`&Mqf;~H*8k2~6(T#3wr89Turfmnw'
    'd8dR~@+tthXQb`+30SxT^Own=9|aSojFX(_?w&;Gj@&-wueX)NP4rLz)O^}`glPdqr%j6jP=B)hI~gAk1oGm9h5IT?q`p;QW^WCg'
    'gQ5N01kWA;OG-d>z)*u3d-%#}xXnM>BoTL{T<>%JQLVf?0$umCt2o=tJC*s@=TGibQr@6GXWwERUy)w5HP+*Z=3akKEt)sajCSY9'
    'hvU!uON!|93zI`l)F43r`$To(`K51@(d4*m%#kLt;kbg^bX|PJaymdt6jMx_tyv9SBT#3@`&nknJ4e+$ff@2LV-TpCb#l8Usa~DI'
    'aRh3qu}y|uO7zs8yD5a25!_Ky;w69Tnx1A$$BF_}cbhj@gnSrUQF8R-{hXmVyG9y>nD%3mHX+zv(g<z#a1P%CmLikVYfFEA$Df~o'
    'n%O}cQ9J4$9In@V&JUx1e*!&LQgu(eY5s1AnaBKMXWYVxNpCAb@ZUN;(tu*;&-8J&*Hvd@4-}0WTid6UJsn-zWQsNxMHLo6=mYR}'
    'pHr%D+q39U%d5F9scKuO9G=0JBSVb>4Qvco8LOL84vWwRB^SsG;v%cSap0^(P9qEe)6;&k%+9czp{m+s^a>*#1LvU4o<jp>QQAW^'
    'uyXe+Vh0Tnbvj$%O4+P3TU+t-VPi$hrr}rKNyp&N{E`FJQeR(<XzUg)+&f!}^!Ju9%;(b@H|G-~K3wl3Xd>Ni9QxUxJZ2JgMU!Rr'
    '6m>)iO{C-Y%o=<o$#0~paT&q@G378)kHvU3%a7RH%R_+OubFWlAsw2|wJC)mF@GZ@>9#lv*|P;X)6R_hE2<?wxWoF`j;S}%pBycw'
    'AyqM;gDM*6tjsrn0QICRao5-11LU!)<Y@ESG<wKyj}`PPX5N{to6yb$<QD_II9~25jCyD}@o4HtsM0{p<I>cfeQOI$AlrCGoQo!m'
    '`%!nCY~Wd0S6v!ma=90CpeT{(=34PO*R#ldA`2Ykhpt|q4L8jY)p5J$5wsK4KtH8&!x=igw0o+RD+8aZzuDqmAius!o0Mv`gTtZ5'
    'SUWxLS$KhvwVJ8E6W21XkXi9}NFwWLj{)=?32!+1S=dt@bB}%LMQ@Q6@;(*cC_3g0jm`UtbL=7gw=^<$tkULGH$2+!)n=F`)OZU@'
    'qr`a<=C$L;&jqCEvN0}~mG><I>qH)sLFm@3HnP#QOb%IaM)g!WJ9GCbYp5qZ_ALx5=t-iEJ+qw)Ebh~izTLd~fW36>@{05<#>T%_'
    'P)K`}CMF~w<MN2H_8T?TYRpiw3f`7pM$MO>s7hZ|eeY@N0xHS#ujzfLC%6S9jj>rBBXD=Ud0>pG=uSKw(O#$E{MDa_WNedTG>r(Q'
    '6WfEu+52i{T_9W9E-X}{9u^1p@hS<EJgb8SaM-fT+Qd6t@p2;P@UHRB_HUY2)DY*-1mMHQznGG=DR`N_J4CG<#f)pR!3~oPpZ4NE'
    'i91L|Yz|;t*GNCzGwYBx&s1rPTKf?l$+X)dBy|Ce@`9CDR2Wf{?T+a#Puje7iq+!>L}j(wqKMT!JhFT06iWTD*^tSqXWkJ)3~9Xg'
    'Ha!v)4>7sG`&qMB@P-Mre)@C{gf+yVB~J3J9`T`VMWXcx@N~kl#+5q`J&Ai?^WIMI-curTIMvAHO*oqvF)I!ZAnrXxXPzZThSLGp'
    'y&az!f*u7h-Pl`+^5rjcnYJdr2NpqYZ*|tOPlZZkzd*{~bIr+v%egWn-=}@!gZcdu=r)9^*?fyxt8wnO&qE=wVyfWLm0frMlL69l'
    'yoj?yF=P6Xsa;W}#mP>g{iyk#5hRmuxKVVl`vM_sdjWqe>h$W#!4o1H&v%>j8t@47GiTaSh!~2va2xRS+k#rObBf$i4#^OK^bBE&'
    's0^JS+=jZa2V!_X*~})jn$WPZ?E_h71!>(VEGN4kjsHgEF2pXQfksU2rOA~Rv8lDf=_JYdLA7%k?kyv^YpM|+>EbBVuMaBRxD_Av'
    'nC7&yflf@*SZ-TLmz(jY=F505`#P`;`qYf~w(#Em+s@`8Sn8l_POTV9!@UUkZzo+p4&|0S{LM4FRf1;_4Sj)1yK#(}rf&VzNYj~m'
    '3?BF^F37Iy5DE$*eiGlP@b2&AOWlhp0;W99I#Y`_wK|d)X|LrCF1To<Z3$-tIAB^5pvdVieD}ppnGjYK<*j5cAhMykpR1%F-ZMT~'
    'jOt^oo)hb0{x@n8lBElrjCpBNP4)h6S++r_hlKi}7WfmCWVBhgoC}fLgKd>yw|j-{25ci=!l68B>x~>(>k+?u@q=Il?g$$LbWI7_'
    '$Ku1KT|{m*_eGAfQC7a^VI&WV#M8R~o_l<z@My)&lSpIZ&M>Sm1fMtTIwSJjKL=4Xj5N-!g&WkU22U_LzUm}`USct`7pk=X`$oA<'
    's(Iyl<nRPNYx`Z(`&HPPqXLLy9QE^YT#{Il8Cny?SL5FZFfxtVauS)SM<W$-f3e@tF6b0M@{~#;fQMGdQB=UOX;s#W28^<-4h3K;'
    'fIe-lMS-=xU7B$%DyH+CkZ(gmuCTO-q_$m(6Qm;3Uf*+M$4}AP^`aqXq-*18wh5=xhd(0Wc1+wf3L<qW;!eOgB^_;2M?O+nwBk%l'
    '&+vrK8p>*vjo;cM%dn`5m)ihQ4*Plfv2=h`u%>=|z8z-?k|o=Hl{vS16?qTne6h@5Qhi-JN~<9UNb}DiqTG@d=8_E)?Ah`|2|?NY'
    'hQlAx0HZE6YBlOUfuQ^|&<<2O9|?kSLb(n0AkYG7eB!&83FiD}_p6^yn&qY=`<A2f8U7WD^L~7|=$$ykCd;2&*$CdPr`xg^>swT4'
    '04u>dlgW_H0!BX5DqqSCYU1d{pXHT|-OPO8JQszSjgR~vvTA0++Z#UV8Gnub;Ufo7)9+~)LgofI%?lU{`nndQ8ay+tp;PNH+Xa)!'
    'yL<z-s5py-wBgxuArKM`0)dKMLEO`k_SR64$DUv6*ki{yb>$yRh=cRT8Ap;JB;EKM<0s9nMdLQiiLwKfZix`Nowsc7Rf3AcxL?Dq'
    'sz~rSwTK8U&SMt`(~{B2;1HQdM{G05>@7MNOPS=DkVjLHVws!6hlXjWU130!bl{Zf=S(XwYOFsu>QP~4$GNJ;+o=6~&Cw#b^AwDL'
    '%V%BL5W!nmO6(T&EXJuz3*;lN;x^p0iDJ|Y8AWK_&2jei1B~`T?TJ9X*W6ZHSbI-hR=yV#fgO(Xoo;bPVi0H}?{A-|^9q1|ywl@}'
    'uou2_+;4Qg@Absg*g)L>KhEwYXL?*q5A{@P0EvV|QW7<X19$}P*l@#u0Rx6Rp8e7DE;2HAA>AnNMxkog`s0g`cv+YCLd&#7!qD*I'
    'I`v(C`^&!}%b+&LLywaF<H%Is+&|5o?=j1nLe+dqsWV;$h(+VQe`|;|dn9Jw8OpTAbW4BtUNo{WQlB1d<{Oys{63v>mfe0Y!8(Eg'
    '$OPuQD$F#9zO_k=O7-2g6u^~!5D2}=c?OzBl=NyqmA4eYx4mA*vpMLBmE2Q_Dg5W$GA$?F&WNQZ_lv5>J(s}Iv($8^YWT3IE>Ar?'
    'CNGgthGFYg1JKii_$8fLG$tbzvOaQ>v7_GHK8@jRsp&*F+<s-|_6svS)kZx_00&kLOe%VE=h=RL)8NKQW~RC5qDs*ro&D>p;R7~Y'
    'P?nix8$x@~Jp5itx_&46mqq<7{<2oolM)&5VL!C&d#K&#3MC5k;59D0XU!W#0Xs<VzX$q^VoXQqJFX^uzfS)QO4um(DdN--2LZFU'
    '(!DLwo#a+Vz6ETIE6^ER>0^Huc$PZxJ8j>hU>&&>242t>c0iH8B&Aq0bIXSg`bR{Yw#?5N$-)!7U_mMM8>#w$&+ip$U0-14vzL}p'
    ')bG2)5n*}jZ@A5YaTR`fUefT}1kZ7~qE4ze#`2H(MP88%`!T@#w)D03622_wYuDuwz$H%<BLyC~*H%VKQUhYB^<P?s5N%HnBx~OR'
    '@it->^eyIA{NV5ZAHJME{!a}nVy%<P(oqzD8RqE0LjOLDNGRv!#uqZZ%4natc83dkA5)lHPfX{d%9CCq=W;sNi~i#;$mHM_>6wip'
    'CVd$)0&?n!rLDy@a`-Y|A{d;c4$(o|<2{y4gnt@ouw16m)_!C4e!8Iga_Tt^o)p60ns&urbM+yw*tU9X_tG|N1}5ak^{aaE0WN(4'
    ')U8Ea1KIyF#m4F+RW^W`woJ0=V@b0;cqedq6zG><=##_Qlz;KnAq$(rQ}#LHnb-eJACz|OT+NBIPIAWM5s6r4n=j7-H^O4Ap*XaF'
    '&UJax>{D%l0>3PAtHpTI+kh`oS}4NG+d~EyNwK5g0m4A0ar%fozSYPJC;3QUr2oP~IF1x}t2#=X<_fR0>)|fpzB{~9nln$N7XP8g'
    'c&4NSCZ?L%^i9qvh!a9{U$vhM;1$>c!RE7<Mn2Fqbv{RR-=8+}^J6S@j%t(Qj-FJPXk_d!X8_Ph{{pI1H}%LYgkoCVDT&e`cAzjT'
    '&4Y6!%hYpI?XYE493o65OmD_OF7UaOXwnPJ$mdqBmj^+bc?PN8U)?Kdr({kNSJtC^TOnz>gL^J!<6XER#7MVii2+eYq=!P~Xpzm+'
    'Pln8nBzrFjBKgvhOz7CDa57cAZ&q1fqEr$%yjUR2RYohSsfAHC-jOHrgoR`R_5J+0G$q|v1Qw7|@;m^&>HeIB$BN)C_*<l7FmscR'
    '#x75#=|tVynFKxQ@Ppm<)g0_0DqTN0ors}+xxLN<248s)Ad=HXe3yY|#6+d2@d#?83}-I7zlzWRF1CI$4(}ODoaIZS*7j+R%39;`'
    'xaQo)<e;>(;%K0y^G3G$+|tfqp<Ff0E!y@+;4ps#g0;d7Kh72(!nvw~Cju`=If0C&J3Vc+5i8PG9Zp#Sl40C;cUT6UxsR*nB9hSI'
    'dShF1ZxL%x7w55SuB6GLJrO1AH9;44a>K*^0+7rZ!eN%Kmvn3CSX~sllzkKU<tbvIaaqt|w0xE*HW5$6;4ciHrU1VwuLc#;@w4L~'
    '0u{&tAF!vohy#DCd?4p9?2V+MVM{N;*{gJ=qf&eS=P#}x?^lhp1MCj{;$jQUn{<vfhA>>Wse(yw#h}(HpjN@Y@&|-9+{~N4X0P<g'
    'CeS<`nL}<^?YBPOC<?`SIvi^3T2F{(#fI5O7zO9E#qS+$JA(4zb{~6o(BhjGW2rGWZySp%reW<j75MIMi4kPpqHPnU3f8D*GKU%Y'
    'P5&#70?#5A$!u_C`?AzLO!RL+>@%E{K%fA|xK4riY+ye<3`0NZSFyGcL?On;xo~gr&v64VRlTDvnZz`0R;KL*usn23kMC@bhwD`t'
    'ILP>=Nogv$!P&}v4U~|TXVJDpAa<iJ*4Yi;>ir=o=oeIVsB>axEG$U?;Vh?o0GWUca#3XCwsID4R9Iku#yigAln{-zABfStXFM2S'
    '$X%V)237F_u#}`WZH{+i)s2erDYXnnlA{*s>Lb0|au_|LA)j$qqc2nV54eR9>9ccBG-&MvBy*o79>KnY%%d!SY)HP}?3EriZz*%Q'
    'A+_N6X6?BL;Drs~3@QN+kccNur>pc5%snV9#DYQ1HkOK3FEtj2?B?nP&~l_d(1Pt?%mM1#pK)#Of%c5<^96z)CPqNLFSt`Lb*%hN'
    'h6(xtdT~AT;}Amc5McM?$oi|@lp#unRy{CkP1*ehXe{(-_<vs~->exiU70eCwuvNQW4zT^Cl<X0B3%h<pu0IKj-cp)K<O6FMR$$P'
    '@wH4fzo_SSvEYw=C+xLA8%W_n_!gMqppV^W^n$nrXENX8vw4^S&)+5pTC39Cryyw7#lecojH+$sUyK#gW4cSv<TV!3+Ay5lVUg=o'
    'ho-lhJiL#kzIB%hs51ep3T-G}XLptOMBhTBpVvNy{GZ=uJ7k9=K!xLp-$0I(^LJW(m82C^Ao`O1IgC1ixEA9Fmk@kf*V=0ir0TmZ'
    'T6pNGVfWnB_};0eUMc^K9u>v-*&Uk{A@9_Gn&}c0aKqS~*qhpHv!r0SBe8bgb;caI3aDZ*X!y-^FaE0RcH8P1aK$m|bJC18AU1+U'
    'O@t~xQ{~4`<_YU|jy*?a@d;ulEnUtA>6M)}(LDE19T~<E@UQ`_0{+Dbbt#?4k2ML<2C@Di0oU0aT$i@^kLY+r5{vw!re^-;1>)NQ'
    'O^$c-IRRLV#yML(bs2nBLI9eS&vMhUCt=YNA(Hu<|B>pEUXOLZkJ!Ijtg$~ltIoL~KuC8j(;}1WGY6YTS#p-#CISB-k&d4Y)fELk'
    'f(W4gOPmq<Avmy-ZW&aK7*%(IGqdRRElpx}#X1Mu#3Tw$H}uv>su=TRPIliB^cH|X7%9~|{>gI7`Z!;oG}u)TxMj;_NC-4V%qBtt'
    '_y`Z;Vz1x86UF6o210pPqkQOebFW1aYC8^axd2$>TB7(P)jkY<-@am+e#T|ERH+XG`;%Sc#gFBk(%xv(M?$N5r8<O@7cMw+UtwP<'
    'dLNm>yysc$pzp0Yzf;<8XEgsM6Dw9dRp1ix=8{2ut!<yRDB@ZA>beYcd-``;%*V6C?i8w#`8rA{)`>t*mBeRT$*JN)4}yYsRp<nG'
    'sRo)ZyekTH`qm_y<61(LKoi!MLC;)aUmj_x6_Gsds|=04-yYwXYvt-!G^&PfXvQN?EI*NXpKH%OzOblRJF%d;M1jP_XhTlF%LpKe'
    '!Sm<Lbv7d&0lEPavHah@{G`P!3_Q{+x5cph=M3V0`@_631-i{9V&jk*Bs>xD@zUF7{qh|TJ;@rJOmYR>t=qlyE?tY*C7>}dzkQXg'
    '8ZZ~#1}+fy5?POT1kb(iz@e2@g69_kRNlf~j}LShkR~zar4$FVLK`(&>p#B=<&Kl@yRJ*PDlibxBbD2>UO=sjCd4tTNp<JY!_b(k'
    ';VY~Ib!6seaqIXVaajz<_-wyVi&kH2PzKQm(Bp%f9ZuliS91*G(UKHP#}}j;a5Fu*{Wx^H4RV-tm8i7=p3B}6`aN7=I*F)tle3f;'
    '6<kw*z5972@wIr3QhS}=r<;r{()%;O04RYH)&!`78NjHOjQ!8@2NPBui%2+1kjfq#nF7}pY84?WjNnwRr8wYLhdDIC*z5ND>->~%'
    'Iw40XhVu&_(Vf0Zw(6o90!_i5gQ`oFEcin-zu$XTzc+m98yZ5jkK+>Unc+)~71d?h+R9F>65O=-&rCCSv1%+z?0lrnSuFeSUM4n;'
    'uCfbcjZwDQ8kSXy+%5CWaO01CZZzX_U<Y%Ddj1>+^sN{ECxvgm*MUVe@8Tn|m8ZdpDzOV%OvxGbK|U+h<=3zw!+)&N!WR}|ot`++'
    'sOVAMsAYFX3v+IJ$@!*JNsc)Z{JreXfn9Cc9cDs)1f@bePX=Sloe^KDF5#8wIRV9TcFA_Sqg$jOar~|n!}L>W5?S7)VBlt?@mSil'
    'eT~hGuj%?lE-^@Y8Gm!f&V9u~@a7EQf|65+GC`z({eZd6DuHo$qN}e$p--zoFC95@MQI#5s<^Z#4Sq7qC%wHLz(&BWaBvagD7b68'
    '<LYwt6nZ~Dv?)6`(|hJDHv6T)tA<&l!9kW2ON5yVzl~HPGP!TVg_kzB30p^UVIR}Zx&|~5XFvnR(v>nzr{h6^VZ`5#-goeWQB=Qo'
    '*q5PFh>rBnD5)D)vVJBg?!CgySU|%m^_Eraj3t_h0}YB579|SxAbW?gyoPMJJL=>6)4;{PgH#dolnZPIZtaYC!?C?Py%4G-Cdj$3'
    'XKCZ2O858oH#KwI!WglwY<RCTrZH3&cG&HhMdd;QFZp*_b6kJg5>*mrzSA=S&j=S&=nhn*!z}Hmh9dH<Ni*DJFQqHeiTr$N`hU=%'
    'HU#H4+GOy3Uncag4z(C8C-riv{e3RqI>WHg{O?%J{N16pQ?$HVkYgEM{4ry&!{PyMZcY1z9TJT1w&kWXgvqs_&fd&7R@e;-U^as}'
    'c>e(%;yn3QjSk@R*QcHQ7$dm!ZB*zG4R7AQyesAoLv)C7J@AS!1NMk6#?o_zIsTa_O4t9OH*R3`9TjJ~jCm8^KGimxAqv9}P7>Hp'
    'xJ74l)mK<FC!VM%;Jb3gNUJUaDoap)z<{y`jZR;O<$ulcEV#qqqVzY15{SZzHalreVZ_IEejnJsvBE~uiF3pQYX~C(e*;wG3$_);'
    '<;xSoy1)Q><B|-apH)|zhHaxa+M)xr!gN*L!2Nue!)xO`FHeXnjM<&WoYYbqYtIV@@i5k%Bmq+VzHAO)cX>tiWs>Qh(4ZX=6waR{'
    '%7YMhP!8F~q6%Zpz&Kmxp&btPhU2v^$dL}ReDKtN{5E}zNyvevw{>oVS{)$@u5m3FWKjUDkT<EiV4%0^UitDSY{C>cy<+-u^}Q4*'
    'Pb@r)%6XSe>UYw*HLQ(sF8xq$q+gw4Eiz6$VSCBqx9#tliJ(^pi8E6&&7jdP;LH^@qXZS7Ic*)=1pO2I1q5K*1E1#K-FEu!;Osfg'
    'R0bu6YTJ@Htpl{CFYT)RTbVbZvKlIVLASU6#5wN#{$LM~U(rsrvh64!Oj0=@Ej?imCGduAu`rFpWS;1e>;d28kBHjCal{YeT28~r'
    'N^ephWRvfV1hHdpH9UAz!4=jc_e6Rs1Eq;=&+#J4->WVj0Y{wS6LCtM!tT=6Lm@2sL&B!U2N>^}Uyx}@jN-U<oxe|W*+kP1iAWeQ'
    '^h>AEkNAa2wRHPnb3`GgQ(8~+YF|GsmA<k@KVR6Z;(c@3tg4K|G(g2&f<)ew<XOfF>-@c}{XAs$Iq~4g`X7<LAF;#M{NARnkW7JU'
    '8q?>)&=Y#J!CNs);{A#&qZ9{75e4@4FbfPeWJN{)%aW4ZButN*LB>IZa)+gbe8g5lr-Qts#~R$#wMMX6wXIB`;8{hTq>x}>uf7e7'
    'gD3vp9E@OujG_TKf?z)IyMDI1q<xJIzZYTQ8jBYKmbAtFGwIc5ihoQFvoFl;6#lj3vTuWF<*(+hvSlWW#FiNjR>C%zro4Vh&veWZ'
    'MF}xFJXj3toC4;!XdcclGrjhQ0f8c}F1PBQ8YWqEEb8j3ooT#3?!~^(*_kd4+L1}3ABwC#NM;jDTc<XBJKn86>6@qarUQLs%=fIQ'
    '!yFr`8&N(V*7Skm7R+mY-#Z3>6z+g}^3~LP*A>R%GRYizk>7SytvQCRj+wIij1|qkUv;*q5<+;MS+=q^!UB5m<9DSKrSMVT!W>z*'
    '9hKgla<x@Ed|^$Kl;BASio&EkF&_k;tD9dE*0N#2N$%{=EAG3P+~XHTVD~`jr)+xFX3yy#_)KlQu72+EI%WoH;~Bbe$p|E3>F0LR'
    'Jno%f2EEP;;37(;Z)DgLb=NI9QIg4U2<u)F+a{>E`kRVWUb7PS?=v1@t_vgQ97X2}Q*)d3kJx%TO7Gywm^iBD6PD2(i_#~;(YG)V'
    '5?|uW3YURkuR@Y*VWCQAu*Bc-zzuqJdB1xQ!7#Q*IHb>0SH=-n=Tp&mt}q%pw6LKibNe*p>Dl5IR9~$9$vzi0Aw*bFGHw^p+yJI<'
    'dZ7TK7XH<!@%+LjrBE^VZ*=P-9cYh&2mBE*@GuPx+rE;Zt{Z;^tb~rxlWPn)5wHlIuWU}z2!Tm<2cN=zib{Wx7SXkW+;!|((Jc|2'
    'pHSuzIVGKSry%uW0?>{Dc>O+%Rv7=$rp&ymSZTS)o(Pf8h%9|!2wl_-7$V*)iuDG9ztS>t5>&|I_cyL(KiZxp>&^D+%a=-BhH9YB'
    'K`xOM1{CI-Hr@Q{#D7oTpCcPpdy|I9!A+2$uIYC{21f|mWaz3R*zQnZO%3=uKPl`RS(ehfz6;pV9PmmJs9gUb&`5oiBb}DjOu#tS'
    ')?-G7NqQ|KhZX=L63V;6i1U$(y$LrJ_Y`an*S$tpf<Vsl3P@tzrJx77bE)&6cmIF`R}{>Gs!~<<L4292oy%CHUG$OR5ecE*<<kp>'
    'Oo2mPQfph73Ye5VErIk=XV8=s!{p{G%)IA{us{T64E)TMjHSW_++lzX@eBNZW`MJIt}F#aUuKo{X`I)B`Fo@5WK2zs00yb=uV(0T'
    '2U~Qv*c)9T=BSJAMHk5rrRCQn(Ud52$dU2Recby+9XhgU1)s~ERI@b_xkPLBJ2+*EM)gK+0UIA-KK7D%-R~e`%rCVrcU+LmoFt?('
    '<hGu@I*!2ixz0c3>=voLn1>PoT49-Hb25!`Vjxa#p=;>_?S(6Q$2-F23lhq))uKNs=~~<1dy<g*I8jeIw!IAh5G7eR|27p!uX4tk'
    '2<!5B@?qg+t*fj>6x@mPWKdGtYXI=@6+YnI8$S1zs%8<QT8y@HwO6w#XNNhMl|a%VpmvnkZ{rzJRz(nb0gr3aW<1(5GSk(3<Nn(A'
    'xpqdF8hGaz#k@12qB~6<rS3(#Fzn|QL})-^&y<M9UFe1t<(^ZE#gS|*60K_}-Qtp5&B2`B9yD8v`?ZZMnKl;Q8s3C{GXD!cZ3dv%'
    '!~c5%B&~PQ!_3klC7*K?Fsw^0G<ev!RUy?Qp2w+~YF$0HxL0%f=r~U+3Ykk*O+xR?W0NbwkG?sM_l<W)6@VP<Q<PRH@z~_he5uF#'
    'U9;=}bcxMovp$YM50o(wmMaSHUQeU!YifM>rGQg|fvDEX0B8`Qo0*vxuUpR)E*NL2s`YM5E<A!Wwal&4duy!ro^`!^>4`ESQvn#3'
    'S&b<ou9Q5kWhvX~SYeeBWIf*EAE(EjQE!lqD~_C;4o^IYOXTqwne9ah>RG816*t$!h@V6TYu^tgfS@6H>@ejmanxQsy>#1;7-a`('
    'xUxEZg8=U?S!@)#dsun_#+7(@2lzl|<5%9(c~vVQ)Z|DhdBJ3oQEt;RmpFvh@EtM4u;~w6`_n=rQ&_~&J?a2~5K)6V)>+w+JuNMm'
    '9t6*{UJrm};4vM~o#iUMJq{DGNO?zBogB=)3@JOZDmA?k9MZ_mK@8$9g!a<>{=#C~5g+ma(#jk5O**BYvV)Y&I$Pnj&QfyaajpmY'
    '7KkNbO-)Ol{7Vuurt3#!)B$9Voy%Xv8!)?n@8wJEz9iQ-7F@9hjS<HXK-HeE{C6S%E5f8+ZMP2bx!6N=CKQG1KCBl5__kaEt1^h<'
    'Ew`9rTsUwqV+A0Xxn9)wK}x5X+LV~p8NmW?X<3Z*q-;m*wEcx-JZu{1NGNdD>zpKX6mO2%2y%SC1rWs)s-&>3TF`^9KsppfrDS~H'
    'nU_Zce61iwv}U^<1&$LahG`3kIAra)c9gS);lvC&q@ZZ$MR)4p5wZ92$g~5IF-D)l7%O%S3tH%VyNB``<C&|R?BHWS-QeKfb$DPa'
    'V!@E>JVuRwS~N#!IhUHfVubXcc`)Vw43lI;QRU#gvTGK0I7fu#-m#D=w@E5<wY~4Yt<3^c%9@@?r2c68V-AkxvDcBv;4~39&u7{C'
    'F%Zq)V=TGCIAMU*#1W$eR%EZxk#`Mx)iqQhP5U|H1xc3y04Z1b><$A$3m5^gAS=k6=LpE7w1Y$$KHpd1spnZrP^8s}z@b6xn}s}*'
    '{s%j<f)Mc#*Qet^y4D$oQwqMIJm;wCxTfAnr(}6PtAP0FoZ&yu0%&<Z4sR3wzN5&GWyC^Vu7s4({_q&a;;E3W>(Q7nziP#7fU#^*'
    'a`>{>XI;m}Z}ITc(Jk>W69RdT0qw53%yZF|p+?RUijF)QmE-R`eRr6<CT1S*s9!*3hL9DVnzaXxKtG&n_UyBLwH`i3=cawh6j~&P'
    '10$+A9nPSwmzm#A6<Gb~*|pdL1``HYLh7K;eWn4QV+pt%P|cqBHj@+x)8N?o1iwL+B2#i#>@YZqnE}B0D|=)7^j%2Dwa+R%I^(e?'
    '&b)gO>B?$(lAz3|L2p2Mf%mNbL?x>yMhlq)I|an~(V2DTte_dK23I+69B0*~8_d7l-d-EUDfhjQ@AOuV<v<vqL!r~H(O?e}D+kHL'
    'K&>c6wi07Yqujmi-t<i)309NpHsa)^LDqk#3t{~)`+*?63N<z`$eq7vDZ3*wgI5a1zE@Zj!?f{$WOv4)eT^8#^7g5bJSfb|v0yuz'
    'I!3ifA2UO`jtd3NV$TS!{|;q$3?Aio%*8ZO3$Q~#IQ*7R+86dfeA6T**c0`}^efNkp06>q>%s*137f2ykAdzSiVh#;w!?5`O`$1#'
    'yt9gTi3$MAvpg7c%d)R(%8hd)wCQUDVt-q3Po%8RJNkleTVD3oK`YU|zXn$wijaocIm;vBJCLrBRW?9aXRx7RLN3Vb3JFM5oo_gU'
    'nRkUzBxW^+2l#G|q2Aj?TC%Nf<ac&a_99hXf>zY;biDy?kKNgfQjfOZTUPc-U1fLl6zW(uwTh@vk9%S-r7cCg(njNGMRB-e+!aoB'
    '>G(~h!t<s>xu;g9FIj_co!wTb$*S2?+l|@7eRs#5r`@Hv5A_w1`>|4GVPEFsl5OVW1%N_`$+KS=oe`zz#)19dITOPbX|#;e^l(R!'
    'QX=wn!Se^ut0PEpCxr0*ENC%bZ@L9WQu0SXIt({JoBd$Jgq|LH^$KJMhY@PznD$E|RIVHUC}Lttl~I}=!<I2IgOs&7cc?Rj{%d6)'
    'Rc<bqpb^|fR9@0~h;jfJrf!P1;GT|7UJW|gGLr!4fILh{-SmAe*_)z7e2MiiLvi!3^z4s4MmkL6CZMMT_nk}78}Z`6cX<BlKZBRk'
    'eMg~8t3bMdQ^?ACCz&_U5%45DMmhyA2{;Qe=fch(aZd*@+4C&90!bPRUo6X=W=4(PQD`ftQ*hfePn@7vR0cRaMRX7YL$@VDr{{0E'
    'bBX6qjd)ZJ`U+3c@3aYwP_L!Zlgu#J!VwZn)x0_daTqvuTT0IN#=GN)s#mIeU48>ge7tub-ipO1Ev^|9BXLCx!x0J1Yd4_n#0;0b'
    '!Crj13836keC`VmgTr!r@t;y?XE=A!Qn~uG?=m(f%zQ#Y4IRqFo;or`pMA*&2j|4mD+tXgWDpWd_U+D^e5EK4ooDHj+(`=GNOAUG'
    'Zbb$;g2T$PP^+leDM%$EbLAY=wq{HyRq_c_h8pTnZk?+q0=__XK*8@FgwN%mcmiXr9U6&b<C#oVTVJA3BlZqPjlae*sfG^tG9ruy'
    '1Z+$<G-67eKm8`MtpwAdTZ+%sO*vdCeN8)}2MO5t{fhR!OEW_C1<4dAv)!lr7HR-2M=?h!RfM}f!UC;QRzouL-xwP#xrOiS;snv!'
    '<|5Kl909L!ySrPhHcb3h?1E}`wBeA~Dg<YS2~V5rptk~Cw9H-`tP6J#xK_r-(Qb%YlX7#bXtXc2d1PIu!SK1ZpF~aR`X0|}z!6EH'
    '=95L(XZn88Z5?TpFN`92L)d31p0H}7#BwQZZ#pGw_}#$RB)GxbXNADXC#4Rwc)bN;6L(Jk^Ni&PONywr5%GFgZ>^*U+)|k4<u8DO'
    'Lp&d%wAM!i*a(O!Cl3d`vagiFF~!!ybrVj)DTJWzaw9_qe@e3WSe;j@2ya}$W6XUQdW?#Yx)lL!hn;aX>AKoi)JIW8(z7<S-G3Av'
    'P=`SWtRx(O+(EWdneLwugT@}0(`TlBFc+IlYXK|g4kI3UXp<e!(ghxY)vCmPzmuKF4VOO7R?P{F_VnBO@1rK&df%(V^anD?1A^HY'
    'H_5)<fP&HicF2!YG&0-)_LylN>=)&$M*LEJmkQKDrw%#xGoya25Hv7>1WG~#p3I)=W@WRN5X_O12t>0?zj$~MAh}?(_JRb8xnhZ1'
    'dIW#~Nb-Ju+pC))_1VJ^YBf-zu9&e)TZI`Je;y6--!gO)6^ZlHav4kdijF@;Prc-`1mf?wQJ}=g!B-=l(-NurXeokEJnk;zjXRQ1'
    'D+oLk?|@JXYKMF9&EdpTsqd2mjyal5rK9!4T)hbR8p3;Kqt0{}lGy|8oB<kRZ$5fi<2OEGZhgh1_z2)iPp}6D^nKkuR?wx7Ya-9L'
    'R~XsLG|i*u`I~gPxKLh!0E0yWA2b4O%M>7Ug(m<snhIYI5ujQN*b_7E{mu0B34+Ng;{Po50fTN5iu*D!Ba!SF@YLWn)L&&OE%RsJ'
    'EQ$tQD$h<7x7~Q0Xy07xI*SuZ+)|xYgrD^AWLIX<yBY_wf1xg;e?+{>O*uKE9V=Vw#59|BPV69q4Z1ytP=|Fa*QKpQVu>ozdajy#'
    'Ye2%zJ<I+)!{zVejtJ&6_?vNOCPrp$tVgC!omUCT;x#`e_YoaW8}DqpZxym6E_A$5rm4{#<4wo+v+K_oK=D9KtrswlgI;4<6MPqz'
    'nw6JEfgdsgchJg7U*lYU$1nvU*@NX@vQhvX+NUkTAosfyMBhYqp2IYV6Q@}$iNDpj8^LT`C|$B6p9ONsetihQoo$zRREV!IHgGHd'
    'h^_8d{`!wO(FT9eb`LPr)%b<Iiu;Up_?j+U%4wJh<fs?VW+TFJ1=UQVu}c<)i_rTm_5;EiFd#qI5PMgZWO^t^GMZ`$i?%_Ag=1NH'
    '!ptDL>AYq3DGdF3w9+MA__$25ueeal6|RJ7ZA-JyrNuUKbbL=O+OV4OqI9u(j)nW!7(j%rSUWq{-}*2$HOs$uJ{xHSJ;-nmfd9#3'
    'BSm;bprAj`#x1daH0WxfLi?S_-ZDDEBpU=ZBTfFs3w&0XZ$uAi9Q}s_BoxwP$#cvz&lXi0#7C2KM?uVSbWw5Ui#ek)oIwv4)N#q`'
    'ka^0$!s-Ae*1v45nK!0wq(KiNI<KeJkUrK!h@xLV?6@n7Y8nW_f<OTVsgaH)zz2wq2XRFl?8v$`T)rWNFatMSo#_STpcE)UBS8TH'
    '^E^wnRn$yzg(0ow8LV37eUJ;s>i=I11+I*)NWB2oa5mNq@oYCPAKNb8Ip5E6d_M(8iXxidw5c@*5|nzALoRE<ApCB}^o$Sm<^qt}'
    'S8vhLID;U<$$<-*#8TfC#_L1d{fW;_fJSi+J579-1P|_>Qb<eg&g2T>v4(&r9M}48XXaqN==6r0(L2<AV`9`d9Y(j4#S_`W@3<}q'
    '5lbz78d%jG^&KskC($|%fT(e}Mr%11_|P{y>jFI^Yv3xN1OEMgIy}bQ50^x9GtednCn}gF_gFs{1jn;|%973)_)9e1QEm)1dz=w|'
    'Z|dSgqfgmDpfXN{^fu|e+I~~$TQtvIn2*bouPTClvWmTksL{b!9FdOA9h<@d3;9~T$nY%gs9%%K4Ho=~q6C@CzM2I#fr@l!Ji@*Q'
    'Sxz|8z*;i2H{OWy*m&a>oGjr$1zHL8{R4I?Or*p;uq!!7z-yFBpVg-Z*<?5<pMyazeA9elc>K2I%^)m_9cma8_DXb2U!43rcs3qc'
    '8O$vs;yMXC;FwIzfqmxh?9*m{qXc^gE;XYWHO{b-HhdD302I83KPn8Voxk_@J2r&XR5y6IH`P;8x+`GJ@x){HU17=JIlaN^-@#}('
    'LJf>L=Ztk_=)s^P3?!`z3xgKS>RIANV3rSF_=6yLuTMJ)36BI?SFJvsrq>aNgt$h1VQGQfc`R)=&6<(`Ge9e@*LTAie9dt0v4Q(<'
    'eo@?qzVhA={T|^#8z;HbisCHCW|1Y@m9GYQ*v$`PkF&z`7t{sE9YFq!07Haspy_rLyQ7)AyX(v%66yFxB7CmPfUu(^gQSlhzA)1i'
    '?kU6H++lb#J*@9mxP1j)Y`_Ps+wQ<U05Hmj=t5g-jkKo|omKY=qj04a%P^_f3GDymNm7VCsHW&eK<z>4$~J(Ujyh<JUiP3`ovCLJ'
    '6<U;n9w{od)oS!+gwFW}DAth6*3%qkm5_PF?)rtAc2{YieQe76y>SLT_x@(afq<fx!WDV~`z{jc1ke{?!v->TgjIT5l6`}RK=a2k'
    'e#;Di@aPHr_Z>B1xGd+kh|O%&!5c_4c|-Oeb*kYjoJJVy=m<C=;)#P#M4f8Nqn6zAUJmF!tvHEM;tH$4b~fv0#&-Xv6RskZDlmW?'
    '%Zy*r^-UhNf2Q;0+dw&8bH;lrH*4Xe9s6Nm%|~e&R9aMQ!$v7xZ=68j<pKRQqlwv5+H(GV2v_V5uGyR9_9BjaB~0CUr7!lwOc3Uw'
    'D|M_th+m=St6RIfycgfl=&s{kR8-Fa7w5kpy-4A&6Q>w|Q}{elL?JKz{+6|*nbPn<5;0L(Pb#_1z7-ZRQ-T$c;sM`c6lljsWn+gy'
    'Z-cLCSmuGLXrD_B_1t^G$_D|lBU6<R`~G)%iPY}+{mwYdGWYS81LOrcJcAnjuIB$B32l&oKN-Y_J^t1If9IghNVtF)@;nST%5I})'
    '7z@P54fZz*ng%=?%D0ch&MPF(NxAmYEPx>Teum!OcNJ^tqh(*EAZ&65Z}^zOTWhdbC0q{kG~QqV4as0o$u=Ydh;&uQ=yPrN5*7!!'
    'Nn0kuPou)FrRAiDQ`!z^G!^yZMzx@Cz9RZg%+6l0nv$^hv{4?}v3_9}Hk;)93GTm;Z$>qdYJIq}R8-GYGpu;s?^3Hif@pZ!f}LKr'
    '=N0S#;j31%d4n|&uOOp^igJ>jFbq7<Mm{V8XgAy&3zkuF2X&cANH(zeh<oWtMGV?7*TY3I50vbtH_+d-$Bk>x%oJkkT46`X((e`F'
    'xazh)<kJi)zNMF(l(c{{NA<(tcgYcJ(Y_&tWG_%Vi%w3<)mQ@L&l|m$$Ym7^FhuSMuzYXSWT(E{%h)rst}=;>+L=BQ&w%e3drOb~'
    'iew!8Wr7B-K8DhaOj12u`qL`DPHv{6l#AbO=XAOXd}wG#Z$u^5R}@80>@Ue{xg|(tba#$uiH{0vfx*3DV?Y_j$`{h%IY;DWSKRSL'
    'A&A0cfP1t{zzim-tda8V$~h*nL=(<r%@mUhgU6+SxL4R6!xT8;qs)|*iUFFldOX*kq%VWe6Dd=KSR)@~9m(+ug02LJ#l<*7u4OjT'
    'gD=0!iNdc0xboTY6$&``&~|sD_EMWAAqNy~lNcG7WJU%>-}_8rQc+LX<#WmCWfG~>I-+Vb_Ob|O3PtdpTQQ?7f2hC}L7uJ#&?jJG'
    'B(uYnequM37H9p%ySPHStq?y~IRbun4CHMX2(^K~!wyXy)3ld+=>wdN$SE;i+k85dpGaCnL+6TIPSe51;9f^YsOChpNCA~cu8Uef'
    '76$OD^XJh0={$H1rOL22l28hEJOyD&ISpS*0er8wm#&nDDn-_Ws7c9Pxp41Bv027FgQQMl%P?c;SSaI<1(=8@ih;61tF5SL@9Cb-'
    '7~p;1D^m=M@SXd6HPcKOUZjh&jDR5{F4)c_?t<(nYS(8wm#MHkHtwnDN_F^;2zIf}j+S8*%XDRl2+q3EFUmgAH>8tu$FJE)TnD=_'
    'Ujgu5YMUpuuyt3EP%_<d+5l5}*AXiz%h);dfcQ0cx>AEjPZE-glYB5mh-)`cIY|jtMA6PJt{64Ri=%Ig)oQ!TNdz^A6&3b&MWJiu'
    'YaTf|Gg~UjcB6v6KI_U104lPV#(xjx&W|B664)X&5cg-h(xioAXDOrg24vm)3hFr!W4#678Cj)HsNIl93vq`*tC4O!p28?cXpw9{'
    'RD;)F)Vgia*^3h<iJw-IZ@8HId);xXqsH+pMWS~GW?TyX>qoYz&r{`iqXTE621EuztjRUjBRfn(N$EaYElD5v)-Ip#zTH?bKZM1#'
    '?dDb5OWDX;CWTZX+9H!z9WhWy5cbH6#Bx=i>MDLF;2qX)3C6>dCZEM4X#3tJyX?dJDE0YxD52E1tETT3kC|0KnAcNRgYEMAi)K9c'
    'T8P6v8UOk6ZU^)=*fS13);c6AgzIMzTnbL7@dHR;>&MPPkdk?OL|?GT2rUv<4yO{QyR=6mN&7g=M;-(LTD}udjw@&e`g0uyTX!-j'
    '1HkVE>Pnt9t)uT6ww9bj`@KY?NE;&==vki?CO4wqtOZyX)@h*{pN=I2n+Y}aAun-#tU_<h_|Y;@s~Xd79XMbQ1t9ZYKz}mC0rK|>'
    '0@icTfjV5d*H9r5)ev8@C8L%V%hvCAUsqY}nE8Pmaqzw?h(f>^GnnC?gQ5ieQSf`Q5bpSthV(&aIO<It0cRAA(I)H64_?pgg__(I'
    'b`qlVaU(x7E_n7~-Xg?pwM1wdv;opM;LTn^cTxuv)jNqbr#Xl0{e91MNIPvccnD|2_}T?&UqC3Fz4(mA(nPThQ0KdVO9UhIXZ7}i'
    'Z;B#FkJ#H8-f<XH#kbW6D`81L=Z<@v2@94vWU7n{x~wmmY4hQX&my1q_O}3jVf+TjykdgzDUIU3#Y^Mer=5^=&Ry=s-VnO=F*M>3'
    'd<@0E2xw^DEPfw2?^ze9wZT^XsRUjW{h|!X$(h#$D!oacs}@55*hVs8oD&ZdMN_VZa5Zgs($qSX#1EUOGXJJfI^wQgUKjbSZ^2J;'
    'J}sAjoV!o*8g~tkBCF%a+@@Pg0f?|Ll}PV1<vc3{pg@wbx?#%}QxA5uSiHRTq{=5bI$*PWRcY(Tgh<ybD-<>=4jmCaK7%_mI;S6d'
    'N1>vkObgDq2R?W1#dHPfQO(MYqsFPLL^1sVFm-t*7f;;0R}>jq!q;tv5-0O62YJZXOk8}07dk&p+?hL(CKMrY%5=3+qsBhaElA0g'
    '+0JE@=7&%gd@3pzVkSD28|y5x9|6Ti`Om{vyvaz-nsO*l3J)2z%<3J8d7_D`@jObsc$9Ai^vhi-*ByMTal=IdWGVhpF7fswF}lK@'
    'sG9~HSNhx}IHIWW7H-`yM7>9ip9WGXSTPEFyk)Lc{yy<_BlUz!Ue)6?qoBP<1aU?6e5FPxV)Vr}OCOLmU4e=De`s$!s1UWCPmd<!'
    '*wz+3%&U&suUQ=v&2nKPk^naIt_4V);7MlV@9ugV+}>~QY0ko-V1>1iCg1y9AR<{tEL6%UBMSY<S0hp|rB--I7fC*}a<Ktc`ErGr'
    '2&DyF=5tVZP{JH2YhT2)#F!GYzud~Ms6sr^HLecDOB0B1Dv#awUC9*c2dpY9+nf-TnWau{>%MNWa8Bs;z<@jzWeWR*6FHVcBr!=^'
    'Cf{Q&bSky1F!jDi@w~k#RgP7F5%}+Soe@veQW!8Ckv@v*zT0k|#}Yb?a&pEF@kh>Wp~+7h_DSwtL18sT0sp-#%DW027dUT4U16b;'
    '&KqUh3VX%?t}XMz$QSiE>d<39+EV&uzRMdmXLrh-Os!{B$8%TM{5%m{wslVO-_<)m19-a%ql-}=Cy%k7LiDP5AZn*y;Xb8Sh3eHD'
    'vI3cHm^ZR&BVPntbW;qEE%H+jikC9KS?k`|D7>fEsow<d77k+|F^Ca2o8hPIEDSfUi06-L!N+xk>}7aX{6Y~9BI&HJ^;BiR4CPWL'
    'J1f1TsHq(>uj7SRKrtf<gu@XsR66kO&v=ubWfPx*%OK!3&+^}?1eVBKAm-Pz=!<&yZ~Sy)ic(}IGkb9TvmhaQ?I3Rik4&dRB2WyE'
    ')SOj^kmdRQkC*(2d#0>Vx<kM*P>fYWx;qCyL4tlp?aqd=Hsp$_Iw#=Qo6a)AMk|5z=L)iN#Ii;dZ0!^Gs*_rOsPpG2nYE}_d54qx'
    'ScA}`?etX59O5w^lH0CV6f^;qV{?=QX_DOzmiWF3;wIw~!Lau;L+LjXG(}MPCMqeR(#oL{=}U;0K=5QfMO>TKC<aHyuhkZSNHQcU'
    '6H!5idK!+ch>2%?6uVE7$shotobfI)o&XFD^R*iAl>uQZ5GB+K$jS``Pu5Zt%2(LWBxdrp2;t!G(T5FrCf)+^lz3QqtRNzf@|oCb'
    'SE?1xb2jXex*^zwF-;kX?-mPWLIIuM#kGt#g1k^d>c^<#YSF}@7lXItekX>bP9~{?xCFw{>EuX^r5Y>hi2@VmSzk)Zh|3z+Fd<h3'
    '#n1}UlW<k&HChNv5We%~T;D2Vro(VS&J`kqsd|rx&vmu^_i)?ki(Y}+rNC8AnXHwxw<x<oD?7u75|!r6{+>Ct-u(+z`dBDNT1!L0'
    'pAUq1eU#JW!B#PYF5@ftQY@&JVP$YO5zzstT+9g^>?r=wxmwSmK@AWtoV<9WA79$*h^56t_YN`bFu+I6@B%ORzLcDe@=vV?$V=nP'
    '*SP%6VS37bB%Zx`HdYOvjoTUthXgt7D@DL?c_*!<rBQY&%noGDP&F8RJdtiIYZ8h%?(s)$OZ7A-d|A$*xFvg_S#-W3ZQ+_exdvn}'
    '5jwh`!i5sTk=Ch-CA;}rNATDj7T&UT4f2E{U={ZFTN>!}xv@9S%2#F>!t=}l_^?<IMf1k?f)7}KG2*U7KPaT-3iFa<-Fg->dIp@<'
    'Vs&mpn5c-`7FNGUg8}>v4AT%1Ql}L8m5Faul=})ANY%Qy`M?U&G0(yLq#AV|nY6nJCNfc?qUWuWp#ok}5UDPhD67_YKNzSt)1mcA'
    '1LrMm1OuA{Y2QZXxIZhXhpEq9^epLlkYjfq5!E_D5@b!8u#R#s-~eId1-UZUNh;md^*Lv)zLQ>)3-Zy5uV=s(GX@Y7T(CA_?A4w~'
    '^2~~gnyMQms&L_z>e+$fu)11NEml%e7l^A|zO<Sn{c3!)qAr=tl^J|m$X#_P$xtTkkCHK7x;*E)q3^8N05^(Vn2);CsEcMsoqhzn'
    '*$$XU?9Xb^A|pQZ=1i6)5j)pmN*~HEgeQ(7xEWTC+fa&I@M~i&zV9dj{~X31Rc-SUu&l$=IM;K3qYs=N+e!qN)!uigs4K@>R=k`D'
    'd#OnC2TSk<dQGxgQO2$;fxm@%jHmoWT=+*Z;@6ATVLYNU)6V*fA*J)%BgJvA<@cQv^eZfsGEw80PU6F^Tz?SSXXetmM=2=lCww0T'
    'm2zclG9?}3$c$e4)0P_w7!T&;+NwB^vsYWqZ>lfPlgr4jl^56-#i-#-9(gPW8C`D2zJXWzmvcFzK^VZymlvJ^axkPv`Fk4BQ>!Cq'
    'VPu}G73|SbFro!m>5*n7!84$`yNKl%vULqZlO%#*%_I1o>)gHqgckiRqVbijK=pgTY}f9nKch_pJgDGX_3mdF(V<%&C4`av)98?C'
    'YSq*S)`FHDX=lC%xm+uIR}gadsi<C5{5y@3Ty>K5TOvQpjF>yDhkOR}`Bv0vgPn>I3%a5-s*DRy7U6aC+^#BUj5UsZOl`k<L?LND'
    '6t)4;aYS>*o4I+wW^jv*HgbVyfJEk^1&vXf$dEcx`zT_}47R{+jwoT{{$=5S5J}HUIC|VEo<>OGEs}$81rdjvKx|aJ&oBhx6*Got'
    'WrV@C5r#u+rq8>EAt*oJ6FWSMicx=|-hjks7Q*lfy{{Qst?$Gk1Hd=Vr7b;4cg_=%PYtz1MS+j9*Nk8KB{exR!^|XWMNz8MGthAh'
    '>o3O9v0|U4Hyjdxe!8h_*De??d^%J-V&DDy__(sq;xd*-jZTQM4N~F$fx)$Fy1Ri&(KlUE_jap6p{ghXo%DC%K=piditbpoRk95B'
    '6h|>&wr33`LPOP-#SUBR%EWz=`>TmN*rQVux>1^03t3OkQ#fb}RF54>B1$>2zgfFN*2U18Z}wH{LE8RLI&jb0VPC1i+@3<tUHu8L'
    'SLGZX&FbgOGwcqN1arswX0+{tly~j*bwHFlNI1w9Wte%L)fX6*F)N_l1d&-go(;5cxCKDFqtf1C63QbYA9f=xMXh%U0(_?+a|(^n'
    'X%Cn4T+^MBw-xntvXl*v8?C1dc;n9VgpY9i5)nQ=Zrw5R7P*S(b)VpOecfX%U<z!l^L$HG3f{iwuN6E2!dI_NtD~nYH%ugA$;a)s'
    'uMCh1{bXyh4JCrq{7z*+rb<P0NDj_07dxvN1}nPPi3czjKO_o`M|^~c$z(dvk0daWd#&e5Af^Xr_O$%K6p<)`x-tdkkm}QMy3at4'
    'pIPc)S2PzXM!&0?c_mr!`cu)Feh-2!<cvl?h|xiF7NXCZ=ARl}N@8zK-Z&Q_@@P?YqN02QZx#}qkQL=8#m|nqOA(<V8DE7LpGO>N'
    '8|r?-o<BKGSqufz4EQ{}*q6i3La1@;GRDv@S86XcPfQJj;a>gtgk6!gK^yw=n}o?B__2QPvvkXZy>K}Yq)ZoQl+2xH{WpLTWqymW'
    'MtHG)f!XgICCM{(n6wDie54tYABrFe{lk{b4}InCC48&?Fl)d6tg=3nyYiBFqh6_Zh9G+^k6|@1Tb`$g@$VHTky&C;;N@f5Yd}n|'
    'IW4L8&aED&JmvdaW=soLWWaM)6p3-d4L#%T)PQ6Tf*PWZRA0;O2`t@~%CtFX(^1LHHaW>VLl5L$Y<6?!?x&^BK$&PvS{3h`-iSuz'
    '8Wu>4!yHG>A<$7#w=P-qY2IE|M^EJaQxesph(%e5;j|zs?K&eLO&x!s;g2u|zqj_iG=1!3gNl-oEN(864>VkK2T5rVyp`xt;$=*N'
    'U$z$YQKB3gjd27q@F6sMrG0+wjpRs(IYE0$VPfRbvopDt1mj_LbE!o`8*AwjakjvKenLH4VGbgmT<t2ggzp?M+jLdUWo~=Kl?i3k'
    'Eb{Kx>LwY2y9D+=k_bbBM<UTAx7tZ0ko4!C0->^&gDN$}!obNllO9@~inX?)v@{-s2e7dEoo|}?`Y6Zxn{mD4kc#!&@9+^()uTlX'
    'Lv*h&`spJI*g6X}0z;KPszLRvFhuS*rbPE!HXd3IRACrdpF1qzv+qA(IAuf9nTj59!tF)M<?m;2Q!Gx#ResBaMxMx$_kFIgHI3^S'
    'xvtVwf`i3zxt1=MD4t#P8}Hbt^yFj#DaUhsM`_7|v?3{Fk0Uj=SakLKuRp2XHSn9<IB6|C@lPe=Thq+^fCh|1t#BSCs^n0<bCBOl'
    '7~;qT>!dFggZFAsKLp^}P2I~Nz{Ay;y19h($Yf9#2HtoA2`d^$UeyfXfT~(K50cTPDHp!*@5PgaGd>F1(h-E|je+$2%k`!%*%-QD'
    'F5EW<6$80Oaqn45PCWEzgGF)cS&aZL6BIS{&WllTnC0TkbMg)U8?D&<4{+KD_TAe6!1oP*qP6NO3~B&o7H826zNmONL!caW%+By}'
    'oyYB6_Z)#h<I*Q4mo?#rCksg@-0`)G)o{^;)Wo_=hg1WC#l=yw5JyicXSUlI1UzNi7vJnP1zYD!)GFY1(IAV6{ic!d=xY|8-^pj`'
    '&{4;-j;QGc-GYA1wQR01JC+^nGts$Anr=p6)6A;$4ZZ`CA@dz;qoRoS@TOlVq~#5DRG%^GF6f0d4LXAwW%aTo>W?!LQ_yLh<aN0)'
    '#?vIU|C*`@n=(pZ%_9Un11N-F_GRer`;S7o0O5uj8VMEehg>{lQ!#uU-WgRklfBeY_+KOpVhK_;a~`g?O$cj*J%hL4GEI--`r9i&'
    'B{ymK)?R=c8avRan!%;Amd|2FB^Mw{6j)h{F9S{a#Y_|CKU5nc{2XZjDy_#6ea(V^`vIWXCeD6Yq*g3qETcs%@hsGiUhYHDD<Br4'
    '44N<NcFptWk>>za-4v`$hY0U0Gl>=ES_^6a%t*VlP(#SIC9dDaNp)BMP3}}MRc}$57cI6OhTkQXia%7U1BG^KZl}gxW+N;BBWK;R'
    'Dwc9;UGYZ#-PU?aSo_ahATPtA*=snn7myLWyCNk?gfHT%-T85}nserN-UXvT>ME%Ul{9>zulMx*Q*W-UIwu5&Do&>A@Fq&MKW^SZ'
    '{VJ|necY22;Wj^bj$exGMt`HoewHt}n@+of{qDKnx|)+L(dn?roSY=-Y|#x`#0y6UyC?{SBb=x^f)i)-_2we|AE9iJFb@&G)M-ve'
    'EOAI(YHUY*b)!gl>9Nle+c@Mt)J@vClZkJ^!<G-4I|WW8(+oCkRx)>*pn0a&R`@+xAllWg4#|4kVOrwsPrZqwJbS>ROhim6_J!v*'
    ';+=|0GnY+}hHU_<{ddWZ5@|N^FGva?i@~@S^SduuyfVf)9NucLf14%v_#<=ugqdUA8H1z5j~p;s7!dk1eTo&P?QW=<#n#H_l{70<'
    '6p=k)TtPXC8s2&+Y3xJ7q3@eJ)H!sXf0ijE+V)vf2{*$P-?NoWoDdAu-sB*#6m?<CP7ko#C75)w`9YcG)2jgi5p<@Me^qVu{Z9gi'
    ')At`?>_$c-TmO#W#3E0hv?`1ZId44~rvlc;#5{8A#Z?t{>%OBz<1dyyF>X9VdddYm%!z3Xk@O_F1e#GyOi=QEVeIoXqV6ZZ)3CN_'
    'pP*gM-`|8A=6el7SDvu|EMySAO@FVjOfO<)OF||oM~j>`{rg4F<d;p6jF-_f7FsS+xWvBT5Z7BDtyCMYj6iZ<m<%bsAQfw=8Ebvz'
    '>zg6-`^+lmJ>2-3{Oa6j8*;>JQ8kD0K$+tob8gGQBY$D4-*u<1Y$>@HorP=91BAi0s><0=_O!!rh%O3b{o0wgN<ka;GO22%hQk_K'
    'd3_S$`Q=tox<Yt1<to;KUR0M__Gh08PwYGCte%?!F;jYWvWhEN9;J#|&RhMBics46EUYqrTnE+@^FR(AH6}Xqs(NPb&(d;A;$*f7'
    '$cVaDWDh-yR>qRQBbOqnJ#}XST%uKmhMI)Oas_pZIy++KV@rpIV#A-2`B~a+2MJvFK<;P^<mgdhw57^w>lQ+F0nWe54>Q70PR=Kf'
    'WO?JLX4ObD*?WKQr89-mObqrdhXR$c0m-1({+?IKOi|akV?kRJsxPW~pgsEdv%Z<3tp>!m>{A=RL2UL|ylG(-!N=AZ>Hj2IR@QfO'
    'TpaQCgpm^n_jg8y+OdK%7-#$jWLsn#>XIqVwSKFQkOtJFKa3GyWE;Tmuey^-jf$G;V(=*Rf=#yhPPy3BS5x(U(s~6xjhJ3p@y-$~'
    'G7*_82+qm1&iu20%l<*qFNwm~ZI{S&C#5L-)j=H{9rsztqkPziYbXf7b5+N22BnIyef+)`R*z;pS*l!Pw3^>2HC>q#`;Fgv(`cPl'
    'wgEckr~zG_g<^W6B;BDOfrQVx>_`VA?NA0i>)D?vi4~(QQnFX<qdf%Mc~sEQ**@tPj3lfG4jLn=b^E)bXrIH7Q#>wr^oUeHu|+HV'
    '`5Wbp2s)l2^2G%KBnm8y9m4v9%5i2`NE$(ozCct@nE20rTF})pdGp<C7G;N`=n*M`XFV+<+)>p|>7gGL3iKoMSZ}%{zj#eWY>a~1'
    'O%p-x@TT$q-sxP<WV7#EAM_oEr;0!Ql?uAU=;Aeh#0B@sEJrsV;%}^|Zwt1&tT;ziFt4!*nR1hbr=q^=+_dbZ{548fOA-<*tGQZm'
    'UDuwgkfSL{1Mxb|U|L%{C^8TvMwxmj(Z2tko-)4Q?~`KQWf~U^11LKK&+lUh;Uzcn%_G1(yu$Y=drDBsjKh|C%c~=PYER#R%_o;J'
    'Ev06p8Qj;Sip~-Z(C58Ntz1_-Y6Hi;J_%?a0upliEw#)Hl3cVkxOoBSpgLQET3KsGZV)N<DNflJrE&vuGOfwq(_iZmi|N%8d0FFX'
    'o@L6#R7=!r=wbRwDzuj8L9EyHe>w|NX;b(3u5ggsee_Wk>NQO+L}CN3Zn1(a0ZFZ0h9JoNX{hHhybLcKFweD)?I?xOqBPf-^{n`Y'
    'Pd+m9__Z{B3oRdN8fiMXnSpwP6KgBX_UoukC3)_Pp<5Ay_)hYB{4O4z^lCwTf_fCPH2etM`gM&lrT>a=l;5MC7`KNzLNDJ|+hOfn'
    'N630-nSI?6dr8rV8}jQDFz1+&EjjN}e2!XD=wtV@3%Hk`%VbtF-(XG9vk^YXU*Es_IW35n7bXIJCbEuK_t?8^s}4p)ZyMBZ)=YZc'
    'N+YAea|<TB{Cmb$W{9+Dq}2AM;SB$h-6t?+F>-OOmgXFDWMCkmupJfBVp{H`(UNN3bj=(o<NB3lk)8mw)zmHBeAbt^EKbIqzI<2i'
    'ENg_c&Sg2+n(T=jJ-cK4t(e22QNR^MtSK?ia!%h-PrT?4+?!z1bk-$JhsN*Dm|F53LUKK{K9l;3=Y%21^IX3VGtre8$LBahqT~Zi'
    'f{x#x^qh6AjLy@q#~@{FrQN!oY!7jeF_6S+1QPSDO~oz()!BEi>`S;+hI$n5wE+oe^0P%%Zcmsn`tpsHdF7~WY$-$S&t5{5Xbmo='
    '6tYGM<{f0$w;_Rdu2q-$WwlWwkM~C0gP2$UrH?O7%QtGBy-<j8ZZW&qFWq!Bmpyx_CFiH!#W#V(efOtP*v0^}-Di+7@D@qN5cA(('
    'OQ&BE>Wa}${-|5zDU$5Fn-jENFS#LP!?`d*S6HE6Ch+{##*5B%)DnBE=i#K+-+h*Shu&efw8q4Y+f<i2KcQ;KD)vD%;uCn7`;B^|'
    'y?6#BOYUo*eL*oII+i`a!JZpkn;`g_3jvc{L7vT7{q858D<Oqtx@vetVt@$UOpkzabRgRhO-qjOHS@bw7mz4-Z?#R{*dHJj9qR_b'
    'nareH2eUwu`0DQPv&IcBlS8*aSq_aDE-Fv=v(!n?b;W6$EAUe{FF+sS6ByoHDcD88?TC=)clK3p)QR1aepS2YrRVg-)Dt?PpVew$'
    'pm&qaKO^k%Mne+Thc0vI^xu8$KMb=q&GT8d>O<AYWgLRY$iK6^49IFA=ZrnHSEiz^43!wLpv8p|kOyJeNRepe!*-Pc5{=+$`&U7s'
    'l^mGTmpVV;bhJ?2)y0<!rWQnmaRY_&Eatg%X7QsR3Qu+0e^F-y)gtnCKULF75N4X@IqqH_aeSk&Bi)6G3MLaJh}hzSNybBpW|B5T'
    'G>tE?S{3-cXy0%Ez*(^U^qBG|&-i-*4M4ywEFoagQ>F&*Rn?AnLjscC^tt{hU35)P=W!K9@q1u#M=RvqAJ!E?Z>R(HFsNpj!ceMy'
    'HX2~)|HZ|3mKLp5K`7~w0zC`M%8=`O=@~W$$j}4Irnpl?T8^bpbVU=D-mfly=d<#b+z}5(b+N4gcNiVrnX{J0S-V#d&^8*;O|_}`'
    'o-gJ=@jn(i9gx1X0g;7kRmAbh>P%aAVLqB6oNMr0Sd>%4lOaoQH7)`lIe8*I6pP-Hx}NcOx?-}IZZn~k=cRkyqRgE#KMV@`k8$K$'
    'AiB_soF3ASyheZVj(x-eQ%6|m^yff)`VyM}=CLfkM1R5Kkf0<8x%E;@8#*053C3F>RR5BMk-uRom5Q6rR9JVTgsTAGo;X?%_-P4J'
    'c^+r@5gX8^x(x8rysN~fn-xSRWoDlNI*}VuDH;|1S_<A|I*=<0vH0;K^~qO9fv^u^hp|x6Qex@-EhSI%jkpLqnRFi^Hb&89oCm-{'
    '1meef3@Poso1^SynI%54jf=#1y`Ph?SiIz~8r>UB!<;)Kb+DI+O5|ft_6W0r%2gq11m`FkS(Mw@dntR0fP~9Tj`9XIFKks<FGp5*'
    'N)>oa-yznQ#E{eXRu_WzsB|lc@wE?;iuLTDq%|5T7D-#&DO3DN0nW1&Y-Hl@S!&ExI{++1x)6JaXlMEWJ+|L>%y$>X>igyw73db-'
    'tQ_PwKE@NNi$H-yfm53J$wW$V1FSS4e|?`7rS^IN;zkr!Vtv|i1BiUj#aXq|0>~T4$Qd=!(jX^cH@3w!bKWz7h%;FrQI5eweXze*'
    '#vEA3*?UK6kJzkmAST{#vD=;)4a{K2j=Q=mG2XHl&XlE@GanfTT!v+diUM26Zs!7pTAA`A*xT8wPgz*C@6dijJ5fj^(>+)sjRK+p'
    'KuF+wMAjCcn3I)**PwV*FRDjp|40dcRao+r??=YMC#O<|9VS<c&^`fs2R(@|fqdqui|UF&HWt8+I@~-h0M@gvGeYx`P39#ri#th0'
    'ipBR6&%Kh#L5Mt3g_b@N3<Q2M-RkowF&);`M?{~Lsuk6JdBTtY!1q${nc*D}*?AY;n+PoPvhTk>mwt~XV2}D%>5g1~j?hnM)aL86'
    '_<)@uNEhDNN+SB}tT_S;NDubTC|@F44}zpL%+6EVEOq-2_H<Kg{HQ9xb}9Sq+jOlQ5+Y9sA>;5{A9kdPewL%rSfe%q*$j|Mh$21o'
    '_GC&=LB58Hcj2X}RkcmpPv3yH>rvwI7@}qo(0X4EdsY~1=ZNZ(Y2Z@ZFptLYDAcYs9-sDcqy{Q_DC=<Gb;a`fle%);8{IeAKT;<&'
    '4ItH`PWParyM;O!_(kM^YeZxtTh(B`J?EkC5WM5Lo;1S0(WM3RyZ?haVhz+8wEEQ|{8q-_WyGS#OKkpHwI*S3$TsFa6SeC37a1`c'
    'mQf`lE_iBAfyq(dV!jeW+V>-vlczsH<8=gv^+-lTk<`3PRT_0o)8&^brJRW{;t{!?C#<0KJV)q1Efjv$d!jC>(1=h;Ds=AfdH{@o'
    'P$DBD&L9=kl^bOQ+6U;O3tnv!dsz20NL*djXUY>ox`#{epzutyimYIUyVS?RBCIeRAB5F6446NPUfHE5QR{swik@1gnr{fw$uT%e'
    'I)AAS5%BnuWYSfGoh1DaQG)^b#aw8v7>ZVL*NL@2ga<QF_s!ikqKxrR-<k(XY`9y&3XdXmoE7xKX!i_vq;ivj{;Tm4I)0wkrAk)l'
    'oJc2Ubno1v`jSyFt(Y(8h#XKjTalktF+$*k1=>miOP|fi_70LDx_tmo126BcxjYFhGR11#v}s0!aU-=ZNBeT=cPWBhSIz0-dL{~^'
    'f}YzTo!*xO*#*Gv0Fy^tCB<vT6O==)s|)u9vh)o+^Ui0{RBZ9~HvL)>Y6lpMP7x7+oBA&Sr|`?w?o0pXjI;`JxnfC_Rz9Evar-Uv'
    '^WAAjHodF(jo|QsR0Ho^yv1ws-@Qvn?1;cSOd-c<r|n%h#)!7*GFQv`DwlM<C87ZtUe(K1fPf29S95Hl{KyK(<|?IXozD1>NB^Oh'
    'M>^3)s}JHhZSJASp+VikR6Fw%VHZgp+!-;5!pV*p7yk8GKe5acrBH_IqCCRTab^%JcgfCcvs<cHx$%x1rQdS$v;)%1^9pC-qS!IB'
    '!nibj*XuYl|AUCh!;g>zz2POQF;eZe2>(9N<%vQbdf}w5Qo|kki5QI|iD11*xDZ7R@!ssTc!9kf97sb%eLQB2&@wuwWh5B?F&Y2}'
    'NFbM4)J_DNXXJU3N;5qpLusoqR?0$*4;5_BOj5z^9*fV%9C3e9Y>|s~g7e|a9|T~!%eHz3`&Uwtr0FFwrFPnb@SH)fr}r2kO><m&'
    'tA>(ZH{0BD)v;PaOq{{VEuYv{D2MIAi=y%^(!9z5k&YA)NA+_$rmug2UvD1?l2*s+j%{~7D=hi%Jw^?M7|X1N<_J6dE+{8w12CbJ'
    '5wyXCD9bRK{iX|opwsZv-F~$9OU*jad4h<&re&R(F%vPferP@CDiek`Eu&U_xmYEi*uhE!FyRuBJy2}Pk`>REXAwzIElnKovY#M4'
    '5_+Yhp`wVGS~MQoGjewr^Z792hd^$)J-dsKY?EgxM&tQ*+(yKqUSZnE{1tjJ0;35W5>&%8D4J4p)qNSL^dk0s(KJq{o%`Uov{%%{'
    'ohV;U8GpOGp(Qj?-@=>wD8dc=GU;XZn2sn(&Bp<Rvv*sP^FFy2KH+&LyU=CzRIlY!#lR^Zm(*cfFridfqOWpj+GO>67>IaM*W)Nh'
    'nlBlNF;C3GMtW*_v;p|yoS(iv#8B&5K}WUV*<&~4#qNG+v5>g}WsG=!1m!9$)_zECH7<+hz-60IyZ(0JT?<Gbmf#$vv$H_wX(E_#'
    '^fCdp%s6qIQNTMCd^$upEkJ%Y6$Rl(yXJv5yhAVi)_;cfG!24~VW4SLli3Vtb*PGTwOd*aB}~phlf4KcDKyhtB+=53q^FmTO$@m$'
    'V-%th`J;$J_$RWF!dP_^1btDez(*24*(<Pr^VI5%^K<=PHi1QJ<t!ZvY-@Aq0~&Me1LGZe3{)km|1K@WZ*iz!6~$K01cBp1>0Z2X'
    'Ll69*%6-0=EzZ^>;(YIFs~=G^gkJA;-dQDK2Dpe9)sg`9caY(3Toq+_54#J0FxQm9**#J+?{gS+4F{Fx_EE0Enu_Nc5J~Ov=g;yZ'
    'h2p$>S@XUj7sy<kcNOKly<)Tq$GqJ?)#J3|sw3Dlzb_1+;pDZRtGRA3dg2Nz??puoZdhItLOkSARJTP%wFQ)6M&tZQ*!TbEh8iKg'
    'yRJ70ILt1A;g+Dtx#N=_Z(%Oj2I84qY2Ngn#WS(QDaT#QWG*f!ceoHwbX7|RBnBU(42r=&VroMQ30C4>>K8cZF^)R-Mc*h|XvtD>'
    'npbUIdNWVdx06tFu=IjJ9%w0@IR{##_Gno=)raJiqOcg@nx1v0MC*-Z2I|15DAo!_G%bAL9Ag2UwL6B1v!Z73G?bU_IueoeE~2F&'
    ';R%w^X7gnx)$eOtESWV+b5eqn;}3|HRtxEmI4tRApl%q4RFDGX4m$$<>yHp*B`%i=zx)J-I~=duF>}Hel8RxXWFGjI#q}42njgsz'
    'jwfg2);T(8S}2p>6(#$zXL|0hlqu|rM#l6l$!o$$o3bl~nT~7HfXm`3^OpCSD8y}J6gha$6^^Px9}&)f?l0CzXHLubsC<A@M%0Yn'
    'CE>>9;QN<H)M5CRM@Jow86FsCZUvDiW!s>TDzSCqF;y5<GkjdJO$BfxP4)H_mf5(9vgWfRGDk3r5{!5&`HRsr{{9HCTScJ|N-vFo'
    '%RtJ#H^>5f$6{Z9@`4<+;c+fUWi#awc5Zo1Q7-D6)S=`tiHax27YELLe}59AAz6^7;5~!R4YY>R(~2eN`@_$ZkB?AtmIdlr7!a=2'
    '^)T+-9wnaGw~qkHmNRZ$6$OnC_+=LJJ}J>P8wk165~<A=^QkaLzWXxH;gg-N*2GN8*?w=_Le)3IWlwIwD$^*%vRyj_wk*D4MjU5s'
    '&kXW!CCyckeA~_7*OpQ0<P=~Qjr1y~x!3+CfPBZqn+8VCl%gBHId8|>;JE>N#2|EHazfqVrF;h&AB+m)I;$k3a&R9-Rhx{&nDc(;'
    '(X12da@y%E1x1|mbwo1@tmB#MxO4B=URNxOa_&PBf<s`owK_Sa2dc{W9@Yq&7$oOUVoCQphOHCn{d44H%F?wp;2{faGRkz*P0%P_'
    '<&zF4xz0RN`?^BjCmO57&zS6F8f<DobI)Hr*G<E~D=LTIi@28ye4zkg7Vf&W%t~23pSc~wxMC)YUIE4RtV-&Pac;U4QR0ZIDhm@w'
    'XO$1}2fJf}VB#3mM-(Ah$GvqOu@%cgL?dYl!RwBd%A>bmF%GbpjBqUrAL}LRdFG-IpzF&QF6v1ml*;I0Vr>~l8+BiE=N|eQU^7?C'
    'fGVFAExB)ZEcH9J))}{8Ii&L=->bX`zRdw{RAG=W^i>9ZntYgs_feMLrL)vav|q)2m~liVMRrw?;k(2RS-;+37tuz84K0WDGdNCH'
    'Wy+AQwkEu+f!~5}U@RBmwBzDTuu@W2a@GK>W?(JUBx!EAlrqawlc6U#JlH>#b)y`0UXcx3neua8;g;!UhhzJoI)&*`8iwjIX}&v('
    'u7B^v=98VgHF9eec4s$U88yvX&sQ2&lA`hMPm4GrEU`kO;1u{alnA-Bt+GdH8L2cKwZe^<Y&asKF1gA!sV90Yq%r@sD5%{Ld6A4<'
    't2!EF6hW_E(6{1KHeRb76yC9-WG}2UivL+z5ya*hA%zs`Uz9}}-bg7$*9rDU#WXd(C>~0ZN4>bGWbgu$ge4{D+0)Gy_MKA!dFcMM'
    'oSGW*mUcWbci0h~vH^xO?rQSRc)+*#v8*U`g*-Oq5OMEmTp{7IzlVNS)LUttD%X)4j~un-QxNNCRk{ZW4R_e7q;wqtRfJO;YmbU*'
    'Ku$+72pQn&-`;kc?EWfgQI&2m;2|HvB9v96-TUn)EdKq{HO3B$cJ#2(V*=r2@IEU#w-xk2HW|N%==(=T&WdIuihUMj@&)DiE#_cl'
    '<woQMo3Y8LmR&b&{oY$@y9rWJzA!hK6zF+%FMC|KzC7P8qVb&$Z8)puJ96t)D}LWp4$q3?N|X|fF5v4mofQR3YLMn)yvu(@Yryn&'
    'tYNMb<NM!?a__jerMYCpbqCfo>vm8DIs{;e?|5~MNF}&ZCo0b>0)ys`6a>lHG{#U$OczciP(?ioYg!korgTEjs9>4*_5xR>ywjDr'
    'BJIXp6QdhcNXkR^wxXc-f}m!(ckGtqrH89Bx!3g|hlcGKaX}M>H5>~!{?5C;3*I@an6b(qrSD{Ce)sjFvMTUKyq@FNcQ#Q4>7yia'
    'S2Cb*0|UZqGJHAmVWzoSyIw=+oAI?VGxbNV$S06z2;z4xZ7;RfBcbc@7>gIC@#ME9jWP<$A^C{?kG<eYiV9trAR?&6U71WMl?}2Q'
    '(vNb&F(Z4ag*xt)u=U~;$X4CnWZmf8Ua@<)+e%9#9eT!(P~R-#6?!OM`T3OCAg@M(2S*fK-X0wZ4-V>=tlqua(2??1o-inkaiTOw'
    '4IP`4y9Op&se0UyO;>$0I<XP2xsNh&zt9p;(<uA-@8iPQY78<AAJ%Zfj(MWI(CDg(!sIgbC7-oA@@D(9l;ugR%;*ex%{|cK<#}NG'
    '14bC}sVGty<@1X(j(nFb4&yuuQY{+4`H|cx-^likb4`c6t@u%~)ybm(6(bo4>$GK!GfN8Ri33BTz?Ym(=_74P=IC>v)U<l|=as%Y'
    'jBMr9cR=1qk}la<c9d}V3_PE}WYz>6&Ond8Dn;x9h>y6rl&<cLO~pCRejyYT<JRv0B_S_qU7E%i3DAL!R_aqGu;|z5Gjo3_P=z-p'
    'FemP?oiP!6Z#>VZ1n}`S*aNx4DAR}{)Obg7u+Mu7A3qsN&5-DCdr`Uh#L&AJph(n6|Cdq``kakTb1`ZDy&N?jm_lO|HS2kn3*{C6'
    '=V%zu^}SfWDI{rXj0`W3?k{7r<E}=vM{4DT3qe+K4TbD!U79*@N>2I&y`I_(8F2ue-jVt~#}=>#3V~rVILd^^;L?+Tk3QCV=<!21'
    ';^^??>}|n1a1Uxr+u1Pb2{GRSe)CypNE~vwS&%~XP9rorKe{OSiArE%mI|-2r1VwdXVJ%YRJ44Fo_vSs9^E^!wMM>k{Cw)O&L~#o'
    'Kv_-zkOcS=Pr!`zy)3Vx!tLdr0#TMbq2)K#ozPG-F`-8ZyE9nO7W}R*+v?5zqVCWyxnj4tU8RhO&d49;%Tp)1BH*t>vOJ|Qcfl>6'
    '5eu`cWC7*226f9qLU!8q)N+2*gXk%rUH{ker*gnC9DO{Wo|_hc<V=Q9E(RPo!k+8KRSF$ZPA)(`1E+0L0&fc?qla0xq!BSw95|e2'
    'op9RRQcGTxXB<vRDaesDHuhxF@hy##s<vMCapqann+s%i$xtuDldP|q#N>_=T`)Lj`2p#;Lo23v_#Sa-GnNLp3p#fh5Fu|wptUIm'
    'zI=&5JmW4S^mm=%Pja-vkssBKX<0BPhfg-+WtyB(-xW65O!CDjMh6+kZHHy&wUk7-C&orFsFM=@Ta%tEp7Z`5+aBr@a!k8QSEbbe'
    ';Zk6MRYXvY+>|j-<cLhPRag}j?v8}YXtI1kc@HyUiH_u&{|C#>WPu}$tep4)10j^pAC@4tHL{+0)s%!BnILEAvw#q8TsmpAjGq!j'
    'Ec_?j;kB^~4o*pUTrWyRI3BfB+-t6J@zeb72!siGfYlUX_NLCKEil)&*Z1j9_)fj#99`&edow`IdJ>nSgIx!umXdQcN@d_{dU{n9'
    'aV5pW49BwECIHNnRMjB#dqF30Ug8!6aB3<8$O7F0a9u%zcak|F)N(6}C8;crh*3@3E1ENqXwkDOgQyOM?1VU$D*!t%-a{o;f0hu?'
    'kn+?_p)K33kS^~Kmr5=AE89@KIi_yMFvo#oUQ~^psNq4hQluNp%IvD7>-%r6_Es@xCMs<)pBNid0kR@ZA_;sXEEC38Iq??A^upyg'
    'vZ8n!gA)DnJ4J|x{H&c}ZvG-LgAuB1Z>11`LyI`q_J6}4Bw&JmpU(o0V`_9o9k6yb85~4;Lh5E%cf6_Tm&C1Ud*Sg)$LKzz7X#-?'
    '{R2{&Uifwk!azlCH}cM!Ka|8hcFAX*;bH7)Z;-(_^X1<Nb!it|%P;TEFo72vOw~DS2brF*5Fab+y;6!s!K(!=oFD04h7LT#0$LYG'
    '<Eo(v!6-A2Vn%zo1@OFs+%!61X}>1ws0t^A?D7KQ1ryX9gSoNZ(Uk<wTD(^nCke|}f->?m?=%LmQI4Ic!qD~TO2U1nM={fi!FJHf'
    'U6yTc%yv>#)=neNJfgY1U^|z}mqgQH_+Ex>@n~`rLshL4`iQIz944{1G=C5dHC@SMuGNaD3KbdcrSz@1JyDW$JhrvdC<v6jq7F-1'
    'Wl<WBPT;y<oY2t9&R-%mMKhr~ANSMqT}RFvld?c-=5>|Iwlhs%-<h}$rcP3&gWy2*MFmOkSAU_S^;MXa14B&us)%|)!9WRUEN|Qn'
    'Vvm(?=o&^MwTc%)%Eang=Y6`vOpju-6xIsi(>s!6CC`3QV+dATQ>%>%)2;v%@s7&s>!6@y+QKl+^jY@pDO{1Fs-DypoLhq$$5p;Z'
    '!sN=|rblra0muo1gB$S@ep|T1sM+7@X>4TYj)J2JNP_1<eVG0<lDh%ayAg8QBQaTcig!cdif3MrS8+wbopqXCh4ZU0h26L}x%-Nk'
    'R2vbF_g(TA)Bi#nKlhJ3VsJ&d-Jw^GO~YUlqj-&hG{QBRXnEs3M%u^(4frj#?;8Zzs8aDrA+a0*q<i79?&^E`@)3=@@*K~r7}*?@'
    'B0yJ?tsaEw9%0Idfk3Fn8c~{yeGQ(<JRTS1idAhZt?(wZ;&ZvYK~I{*EvlrhvspGAKJ^Gp;8;uS0eInth-7t^VUeGl*K4WNs-`fH'
    'r}`Dc?_C5j>N(gx<QCg6*Xgo6UN)t{7Q<H1<>kEKQjX1{L_pS?p*S*=Sr^#A-fb~zVHTwAT%+?RSc;dZ%fdR&YL&)A4>-vne#9Xb'
    '_;H?V84@DR081+_>^!h}mYtXXan_6M5CW6G@_ARAm?HKWO?G4HYESgsYtid^^B`IrGj9{h=Uo`tw9Y+R8h|B?Ooa4%^UZW>L+RWe'
    'W~ubWp5pXot_Jf`duU_=Zp@E`(2AmN@AX*5{5A2r9DdN*bcwROsKzh#k323zI$We9n9IACszo1k+Mvn0hRV@!J7StTK(V<U$+iZK'
    'gSO_yaM}7}#O+&@id}tQmBm@6+T}Gj#}0tsDpS@w4TVg&+7AZ^km8UVXhgFN+d?9Xf8Jeftr(jGXbkHg^S6*I>4DDD=1%hq0g=Qa'
    'i=8s+nK71}R@t$JYVay}MlF)bMg8FLbc0o$saS{e_vF&*kkFEjDw0;b#sJ9cLKK=YtC22E?UGoE-k~bF$c%$S0txcB#HCwNSIldi'
    'g)kv^P1T%SG!nn#@+@yhIKfzJ(A{5AXAs)xUuN_n1e$mntzWW*t2&ReSSYRU{O$#oKhw!2xI1gY+o`|3B)O;`x2vc=>KSuLsJLtO'
    'L@5Ww9#x9H+?NqEqpjBq`PuJid#lxR85M7+Dz3Df`ide$4H~87IU`2${b?7^gd;dNum}5u^q8!z7=h`kF$4Sd$FsV~#E4|P5iTx~'
    'l&>HHMdT2$q9FU3x4dZp7dzt0oGrNLySm#RJh1B#GDM=zu%*EF?rUMM?r<*wsGM6NWRQoXL*$IP_dM(=rDi65A+Utqk^Jo|N=t#;'
    'NbJ>eJqzqp9~Q%bo=HfJ7F23@RXBVA>G@*jjL#9k_8N8RP?RL{uoV;LU8i|>jNcR`<HE2I5Iyq9WRKyL)zB}a77e1qG>6h=(P1)W'
    '(zid~JyJ@G3J0DP(-qB_GwLUvh3{Ko&|VD1Z<{}#*0F0_c*rwLw#7kINfK)?D!e!)OrL`6f<jnvU><Rg>lz#RxF<s5K(#k(ZgF>T'
    ';lWJ1b4t%<mbbfBNY#^H7!H*V8ZiG-$b;b~o6m<Z*un<t9KwMf<=cC)Pc+O8H?D%rwxCR$QTJ8d=%Qxc>DoWx+E&;Rij@}Mh_Cf`'
    'U8ekIS^ccN-e7#_Pfc^}_7v?3!0Qe-Jbqaf*Y7x4e3>R&)6h>38Vt&`@2<Kk%3ESeCryTcK^s#H_cNT`dRaO;nzkv$$B2=c(wVvP'
    '^X_3Hqcko(EDXK+xKVrOFSs8i;`L!r<#(J9>ZuVYRi0@_yydVa>XybiiBtr+QSR7Of(;&pbMVb<M&b|T&7P<1(;nqI^M&(TPXit7'
    'TOer<v@6MC^w@KN-35YfT-IENCk)*??$W{}AC!6SNM6%`H{4cuXNGUNgr)LsBI4=Uea(oARe{DR<E*H=T+x#<$Kj+=@15o=9)*VT'
    'Re~~4@=5d#a@G}QVfA3S2<j*Ir~5?FE@^T_<%%X(6W;7q+9t&6be&ep*i!GGptVM@I+JK~fi%MEA=^|K=>w>4P`)FXCGiis=O`zm'
    'w%(EU#&?mJG0w=heCPiYIzNHGyTba&bn(c*u%u1-RXOpyyS%Lp-(#KT0gx2R(|F>KX{9}BIyOY1oB`VE;mMLyjl5v9D$g})CY8yL'
    '^o^p$7D~O#c&lA&RE{p8FfvblNB$&j8j{VWhE!qjI}9XSaAx<iG>_Z|*YvxhuBe|qP#hUVS!g4G^QcDeA^4?*4h{z`)~XQV2|f(c'
    'u48>OlfPjKM~ihNU78VZBs^6@yS|vL4yrd6Or=18Zphee++#ls{d3(!cDcP|QU}EgZm@Ko*TVqV;`(DRm&GlTWiwEEmiL+`YtZ=M'
    '?tC8^1*-#dA64sF`y~8H&}Dal*;dYjHy3-d==CbG$1ROa#h+wykrl#$lg_LYUNul+S9<JaTFMVPQw<pG3Ts?i^(RwO<P3t+^l(Cr'
    '@9Vy3At*&*FnYY^9Zpq8<5As5VWv-Kz_(84GR@FN_Zmj|jrybIGK<3ezC|6To24<@d#Ul*0rXa3pON8a*^DDMP(D6w<_g0x0Mek#'
    '(u?meXO0nFFEW<L;To8c4m|G2q-Cn#a3xxasd=_AdfIR-YI<94<j7LASz+ZXF5DT7wr?c?$A-&GE&5I_-q(6O!Rz49?36NAB?#;a'
    'RC2GiL5s#{*=j^IMEX5q-S)&Hc&)TM_I`IbVB_v3fZ79zfw(EkGE|8sh_=mimla)HgCOJOw@|>qGbH?pl$ttj-%%rnpn1>Dd4L<D'
    '3Y2wvC5a5b1zH#Zc!eQYW7skqU$&`NBr*<2%6lO^0yww>&{=X3d~fMrbtQ9KcoD+vToCADjUvW^-0E2A7Z$J~TBL6OFCqC3sjK7_'
    '4J{atw3>eQGp@#63&y~@m2Mv;E7Oi=fg}jfFdyQ1j#E<deis%H*|m2;PhRK|wBd0sChiq}(W93=e`pa;!RCP<oQqG5F$a3H^bNp8'
    'ut>or-CM`{`t*RbJ4eYmcHRM*0>t%gmPP;~=MiV&UOB>-o)clEtaF$`&U*fo=CwO<h87>-@MugQu9OXAnOjV0M@&7cYybk5Ze5WT'
    'tp((wJ0q#Ff+V*ZX+Vu5t7p{K<d3*eboAO-$_~n{S6^bh=1>E{PW`e#hosTd{i57Zw(8Nq*8gC8cP#{C?BncrXKwi-$G%*fp%h~~'
    'qO2YL9lx>7$$3E5*A`|)vmleIGfi@yH(V1~_ncLNljs_&RHT!_HzSf_XUQ0b!Gw-kHEb^zQWHsC+$)j;<_!37*h68(L52dcMr9-H'
    '^q5WSGwPn>Q;jNhgVB79XUyp85~IjG%{fXHMsaQH2f=HbCH2C$g;D*!|0?=rKX%McyJpl5zUBE+SgaWR{78Z*SCaunR$umGko@jW'
    '#8Vng<hvJ8laBF`X5q2W&Kf{U9%`o5DU#$dTS8cB3k3|^VHRiXU+~0#ii+5K^fFY|={jLw&va5t#R>43O?nuDW%=2obPuikC}viN'
    'L=*CiTt<0aBAgIn(x85-9rh1V^fCs~+;5YYS^Yo!!EkXVIFLTtbN};~XWZcuA-6foiS!>H#P~DUbui<-{4q4A?qJcMND7_*9K|DW'
    'I;tVWzhpM<7`WGI)L>ftD>?rE`|tnb|NQZ9|LMQ}@BjH<{@efhxAXer-_)A_K$1V}Qk0KSef`$TztH5*w;Xi74SZ+NHUH@L+uMUi'
    '?i6*#zYyiWN8%OH&`65$<*W`0t(Keeb0L95Jpfqt0(I#j>WVnDSsYdR9Y;Oy`)*ilp0y^5l$g$F+$8Q5cLlEMfF#x>F6kW)o?e;0'
    'C_=>4{T*;$N#k^)>Or{gOT06B6UH%*;s#hq`+h>q<@E$KsFp<#QPTOhFLDXfTVs;Ual6ELzc3S<v7bt!AO}MLJxa{>jGC=659-ha'
    'Nfvej8sSE_G7c3+aa6Ypmg2kdd^L?C^Id*vbA_3sUcICqu8}YnEF1--!SzS!-Ub2y&Z$81Jj#Cd{^5dzeP<mIPzh$_mBt+vl2X(8'
    'T47FkSHPnan0HD^+IS}-e0_y|Z@6dA1&Eqgk4w*E{Ckww4jToL(MBRv6aHC5moMUdD@Zo2nA4UX`2lAVSKjt}ye_U>>(_humT?(z'
    'AF(W1P7-e%P|9A_h1>qfbvc7A{vu1DP!#Iq>6a63`XfMh_wmeES<lwJ2mJ3QHEH@oGwy^%kJ<KI5AFUlCk|nLdY@C+`S(}cuir0l'
    '+G|B$_GxFoNR2I`V^5t;c_LUhU{@%vU0l=|((}E~vYHcj#S)xfCDxX2hpG)jak|lW7(VLvghIr9@^Ro(3fJfhoO^|sk+_JpOY?Dr'
    'FI_$W#bx~Q2Df8xM=8vwF^UMa@j@~_b{H|x*sGg8UcxlACQy23le)sbPdc7JJ{=?p3uA;h*<9XRZ!DqZn%WJ7n1r#m8gZd}+YTd<'
    'ao6Y(P$OZ|{&?`(gX?hcylg6sx0yu}HzMVSa(JIK(XPpZqY>8w`x>ZU@1h#!)Z&M8jHEC1IAZ1lT)}8{pOr1nKfoI-4Lw{e0MZ$6'
    '@J}o5tzk4hEG=#CY6j1l{%<vj4oaoR8ADdmTJ`EX8p5o0%(cRZ%#*$)zL)i88slVRu-$f)W~5dzu!^UaYZb%)igL;Rn+}Bx*v)*h'
    'jIhjYGq3%v672vJm-i@9nXhFx(9n!vI$GVm;^;${tsc}~uB8#s35V3xgX17W8HGGL#TikzHaZa|VtDV4nvshe@s$!a%tJ|~pbn;x'
    'BStHg<l$$ZKf+QsUUEvqy&aY=_nFbC(+wg^MU25Qf1h>#?a&^Apg&?#egUgrI}WUyb5)W=aRW~Uc28K_VJ((?;I&u&q;neZ@IbXV'
    '_CwS3-%3B;71j>-g<${$Z?_*VUWU})e0_?e;LamOEmvc1agZnusyKBDQ<G@yDrO74x!(O#1X^Y-J=O=bVptX}!R@Rh?z?fm{7#?m'
    'x5ku7XH8@H8NY7_mvL+1VS{vWAucvegIN-7S>?vbtZwyO687zwlk#1ICwlhgVzu*F(EZG9bi`0t@@B4b{Su7tEIw((8-w4%;yXFx'
    '6mTwCT06R@tMM50y6u_4-IRPHr*^Ch+5q7zP+50iItVj#T7%x!_9@~(A!kAGC*O^Yp2WOr$$i_?0HZ1nCXk=XwSuW@-8TDJ#oE#v'
    '>v(h()-sKasM9_NeW{pLpa9k%HQ84p$-H+WLJ|Hd=b`UTN|;f|#7E6IY~Kv8PAb^|cF1`kt;M1wW@~L<N09uFI_ukmd2Y+T%#~)('
    'K9O-c>my)B*xSSHkKeug*Ms@qXWsZ7<Cz&y{ffIGc@F&|@)E5U8Ym{0Vd(vpx5182(!NGA(~S#E(xPFdpZUD|^Fnf9XahQ%ZSXA&'
    '-B8noxzm9jC<!lQvVGZnq$qo2l$UA8i>!Tu3rWczJNYmJ(mEpKx9*@wJ9r$gZr*k0T)4x_=oxxFD-4r}0YZEr>n!5J1MGph{|j>j'
    'r?6&ZkOT0}{Ev!MTM5}01_aO~2luF>KA1bg9S-09*z`w(Y<KwP;)t^meH#O)bN_@$T$pmv$;;hmnjc#k^ramJA%xQ8FC^@W*5awV'
    'wai*PU7(mAyPckt>_y=rPWwE|wkz8B8jjx?<1nt2GA7Mz4K1YKo2L~&={vsUJ0!C8PC?wxUxv4{76Kl}Rb@iiFAx2_-?}t&az>F>'
    'NiOc?ff85nUgh7vh=RG|KvZx5g}FKJy%%DOyUr3n0o$Is*ejn~LKDgC8GghQiO9XUN0r}D49=yA{-%k^&Tl2J!cbC!_XY<1RUJgo'
    '<Ef$;OBlcbA7T@L9d<`bl4-`5V^r98l*f(iT}p3tT!o;S=Em7qSlp$a*b=P6?}#mgzM8@yVYF3&F|-=n&a?=!MD2`^Si%4>-!uLo'
    'yQDLT`|^Sj`Oy5$FF)0p!p{57-u*{an%@&Jo*q?(WxmGqBd$dI)^O=*x}NBq-a-!=XU3FhCl<yKPQz#b_Ijs^U|GmrYAd<X4joV?'
    'N-fKcM|K4HZQJYGH(D~zbqXH|LvNBl8;P|2M@iU*p5I%oqbwf+P1fqUuhClqGO1tdLZ_yq7xZOwz<pzfJ;D7QF-4szzaw67W(L)N'
    '34;<Ch#L<mCBHiJ%hu1iQG$uXgqZP|ne}NvPz)z;W8wMB+J2XQPrgpoO~Zwl&KeCIfNHCHJC58yB%t<91IWBz74OyG^35M@+O8*+'
    '|L>6c&tF_sSTrM3U(u*=T1KDx%{cbF_CAg1BJe5fK=PS4>R3^S02um}rhmPx+#X8f*jwrC9KSO6$QV|~J}KTAZ<wT%)Xd)gtJf%B'
    'GuP?F%sPKN&2HQ%OM9O-cZPg)6cI>r9XTwi9MYBj)pey!17naD2O(|hTvwDx`q6&Zx4(xuB6H3qc!s}E%xLe2xUR#G9S}pg+>TPj'
    'r)o^pY8Q4b>K<A@y^^w5+t;?Co4zhC=gsS|?fPnSUC{w^e=A*by%QQeD`&~~q?`~|7&l-xrpr|M4fl<(N;ZDGR}{lo!$c>^E&#C#'
    'T8z8<^VA>3T(_2;oWEmf;$%y=uS(s%1n6budzr($`y^?9dyRQ;e>D=M<-e9x+zlKXrm2-4Py3nP#TrG53*aDi5tde7gl3j&Dr~0R'
    'FKf!-J5#PBZ^D45M7O@{{8v)Ozs;7tR#NVag*m69@%%brbmhq2#oZ?*1OEm$`C}0J`?0i26brcyvWR1Hr}We+*-`p8VeIuh5xAW('
    'c7w0&eVsA_)C8qP4s>`|^&RFeK92ZLks<&7h$wY|w&a94zJ4b#)uGDkk^u3l2}Ya9-2N=n{zj%HXN9nte&R|B_c<*$4@6WJElp|~'
    'f*8@7+t05GXBQ(yg0>UJZw#?F>FRz_0M#jVz^>9*{la5uG{PwTHA+qQ%dEp{gYHH;nPi{Z&XK)$!s4KDu(Q>tHBjeFj#Ry`!EX^_'
    'bPsDHDIDS4BSH$LaGN!GJGY4sGA^l}lp6L-mVW=5xE>BkN|3YO#6@!by-R)RSDt{h1AW4wr1tMDp&tPE#Vn{kjU5teVK5AFhNO*#'
    '+~_+yGu(k_;SHPF+W$4qR)$yWbh`8H)MnI7F$aE)R{((DUd_j~68p#5>A$|(jJJrNLG&}vq;UspXpYbMJANrC#H1~W=s&)OCq#6x'
    'HO4r3S*gM)HAvEaHwbfJ_#23|G&wk>QObZ+9Q$VYD@QbAPx_9O@+-x5*r5vN5s$qgteavPEa=((zT4?4lZt$==ggPWiE~0*$9-Re'
    'XE4r}3X|xk+9EUlOZxbXU)$0o5TAyULbjIK>2U^>uRr_$IJvms3^EG3z<uZVcasYW>Fhmjou|8+KMx7AgIuH8+x_n*7xwpGNqH5J'
    'SFT6$Z|6PM?d0e=b6ErWoQc!<{`alj<Imq+k8_-R=Wmy3*{Ht2uM8h}henXyiEY$t?&1(B8$PZR|9@*|mL18mTiFR|<+8pRjOIU$'
    'vV8!UJISCbm3sQBx(^w_aJL4{X^>2Th7RCJCowt+be@p)^=2W>kVcyV>N<vFRnD?pv8*O{?Ahn?I9n8j2V9x#$fJ{i&=nW^@F;a}'
    '2PG@G7oDF{d7|8K6gH0<<vSP)8Hrh2fy^FA3RgGmG-0SxllgAcuk=RHvxn41!r>hmKpCL5<QKy+3(;~S$=JwPx?h|?JOCgYM>bib'
    'o7t|V95wqN$JXKzokveoLi>BMQB3e5`?9Y<s5Mi=ba1N|i;&hv<Buk&$4RC>V|s?u%T#ts0YWA!WOa@(Np8!qFsc1ZuQLJm?m*}w'
    'Y6F*mF~)^Qn5H0-l5yQS3p;-lT0Ts0^qsn?HX?h=ZxoJl=`C1_L7vO}3M{rKm=TszH1e{IOkfy@F{Hs-JYUGVNDPrFbQQ}CUf`^G'
    'nHtX*`2q62T{PdKSoYrGhKU%jD{(KwSvkK{U(3aV%>`)4n&Wk04_G*|MGI2>V$On`s(r5b^OBlx^em>2=x7{cm5ywpci6eeVdQ3+'
    'kxZM>v76}uu}%EruwTTM8c#gbNNq}|P4DB1yVT_%KB(zIY}n^<QPMeIUTzjV+h{Uw4B3ax-;jn7Sf$^GT+qZGw;8tV*BVMmov`Bj'
    'kVX+N9KxPnEoU!CSdjBQqL?HAsv0s?)s#+BpVAB89`vpm?6uP6IVZ79A=b0?k&;0)LGns^{UTFt1U%M`?*u%A^$V&I_Hk?sSYCsH'
    'cpNvy+jkI&tp=mrO8<&ZW&CZ$E^yQeSDv<nJ9{KcT);0C%oeb^OA-OJIi1FWxR`=as1f!aq^Wg82Zle4HtO~R6C6yEi#^Mmu-9ao'
    'i!tITBWS!~3Z{?S^8KPOwGHR0<DB#gTTeQ&dRGwTX-}UYkIt6I;S~W>0o977=PTVW*pX?w?=Gi4DnblXAX@oL6}1*Gjj`iOqQ6k7'
    '5CBiuAQz4e3O{f_iibfcW^6=n#Kyu>P@vwfF3L_AMZxU>Pish^RpPCpdxtd8(~xtQg7DWGB9AWvifVy~y^A!GmfHmCCe;zV7;?X>'
    'l4PEH02nu27Ys-MM$&nT^}$pI_v|G79&6&9{RGPt73L9}o~8il4-@-QtR++>Ze(d!!~tkZz&p^HvaS{lPl<`Tx%w{JF~EeRuIk+?'
    'G!{_cnmsPJC2fAZFqcYO>G$&z&WT^#M{y%PhQ%{%y5*fC$uPkw-GU*+B`EXOMqht=Q>$s>p6O`cLlyCAk}eV|y#rEGxlFQ~?@<n3'
    '5Y7PeS-k_`bzm>IJaOV?;2J`a<UDJlfDWO@n2^?*9wh5FC~G*7S)Y=F^el3GUT2RF!~2e|7Qk}rY0>wR$Wd!M?kuj&2hXAN&!+Em'
    '9A}RU5Z$<Ohi0}5UcH|bU%I&GnF4ASrcHHkCNgplLj?!r5v+D>kGB2-cqj_I(~vQ8k*T$?1%6&>veF~0zdlXJLS%UQw1^s#6J$Si'
    'n=TK-Xaj7?emV1<lTHA7p|uzSfipS5p#u&bVK`!<hu826K-Qf0Hv%Q7_qF>oVdQduK_=7`9g#P+u3C$S0q$DP<T4nn!oWTMEnWaO'
    'G80VtbV{Q5gQ}?b$!+WPI@PjZ5M69ijkop^j%7vAIawrbDybQLBTAUqUS}y0#X<u}$oYz9pt8j!BswzTOif~KCvbznh&!{d%5r3U'
    '$vYdKL1~~tM!aQNSgfeo;NZ|VSpF;uB$MYhv`H!kXtbf#y}8%1{B&)dsuw4{5BLI%Zq_~3j0}LCu}?^)D78#UCblshy83jdRRZv}'
    'k$bguSLC}K8Gj$g<%N<JLLszA;+&@sbAFnoi1UAn8_!j$b{wkHU`hr9t=a#ziW?9<B!`8p#n~5MiZ}@nae2ck*vP?9GDs5%cJDbc'
    '^Vb><Q5KBnfjojH);evnlJME8wgzDgyulHJ+_9~Jkeb{ak{!a>4B+2JX^yOwvUqCX!rWuwOcbBi@NM8G*);8SQi#w+0|+tK_&l&}'
    'TgJ;v>xOd&oir41U8R$-iD@OKV;~hQqux~DbZE~hzCCOsuZ6jqJnbC{hPY6cQnVHWDm&=%AmA(84!g{`Adn=Wwe4Z-5N7I`(ndE9'
    'grM{I>DkVnJq*WfwS16ewYd_4(FHyZb&SFUSd_6ExCFadN!Nf{lK0q+gL2f_4noM7Zns7}!czdGHL5>hLt>DWELpjz4UEuXt!h1a'
    '*k+pomhW%_{0c_&qDykm!X^%|jUi=4V9joQ4r_`%H2a%}iO$ZUPIhlULH@I*iV;z03u14L&gNd0xsaR>V0EkBIFxRniK7dam3cwo'
    'RgY8dwDwcch<v7Rc57NsfqH6rOmpKZMzq~AfJ~SuO0YNeFpwHzn9CB^meH1^6{<|8MwF%cHlTDg5Y(3GH^(%}Rneoi#6A(?q1$EY'
    'FJv)@9(1&IY%dsAKzK7%Q8Tm^y*5Y(XvUgV3URsOSc~otstekJ1`G54XM7%6bAa-Sft6;TG5xO|Ro=i$g(0Wq$AHo6?ZcqI0;WCh'
    '(FWZOkOx@G?LT!h2x3n{kLp?I9CBJ@HqK#~_PoCo!(aq%VMQ{7w;kF<!r$@S(DU?jHrq&_*~##;Gu|n)p@N{0g!|M%*UJO%!(eH|'
    'OWm?agb3kR0G<m=j;jzzs>i`07J~%QVGSuZ+K2G2lY2$8+QjTAKq0m_vRI!Ii}4N>VtB6%DyuDK<LCFRfF+KmU1mfKT*+V>j7O)`'
    'TKe4zv^Xc`;fRjvHi5*1d&{6<kmK`)%sSyYV%?zI2@x<PSpcQi*w0Lfm^RUX+XjDGQqo0Fe;6l&IIE-3z|6&NF_3U*o)k@d+C4_p'
    'elc5!;cyxrn*^Ks^sxELNT)^Fnl~KD@-Sw)GXH3Fbo|o_J>2u&hW9<t&}5J$`&%>u4C})=h-Q}h({ZvUXw&ELgWqF!HVSa^Xu`@g'
    'j(u7~Xt{JfSbKWVwiutEl^tR9yb}c)qf1S*XyQr{6Xw33t<q|u%Qb19R)a|~*xHhgzPAH~4s%dCuQozsz{D-En+%LSjwUGZeEO{l'
    'qd@_MxylB}qsZ=&0Lcg%*?12bgqdU>=p#=q!epX5iDsLP+R#1k5?rp`4+-v7T8)69P#aMCq>ik#b<e$juW2|whz%h>VIx#sHOQWF'
    '>qJ~P*;rwahT-X26EYJ9tS=N&U|4ljU|DTXB%|?X(1m86$O=2jFT`T>K-7?hRmgyh9Q8&C>BqMi{6pPRVaQD5DWaY>hfPvmwNgGC'
    'RwM5v0eiTZk}|F~6HrT5BJtgu8pLru<MF$={B1x+)&X?@m|cY77mb{RBx7|XqL-veAh&LO+^IqM$0S#K>El33cP7e=C`PO~X_0Ce'
    '>S?j;<IThqmY2sN1Cw=2R&@_JJAp>?@0#QAS?cdDr?PR{><>Ai$IeO8Cu0BX)$NGo+Mc>g&99U=)Xn3+HN|E5-Bn~!PnHwe3;jm`'
    'TwWk@6!VWHI_z+FQXw=o0a?y&qik-?Q>&oEp3QqpsgRTorgGpFv+P#PLOjROB*zKdVr9Y`6Ymn}zxc2%MUXAyfEokuOB;xDI0Gat'
    'PB5?^z|?3tUNgebQUP0P4v{{{t`dL(6tq074=`)qbkoCqcLMLHN&T!KW_<4FX#;9R;Or}t;S;z_5Ht{IR&^b(9wZR(B*=Y{<0MlZ'
    '(9w~)fi@bHeHwM$0Sdb6pg@s$qkzm*IipdXq=>xYaz$X11}(?354F&4!y@yfn|<G0j&h)?cCR)`W8w=p7PX#x3Byrgw2wiR4XPkR'
    'OCYv*^Gjg@JahD^Re}I9j>iz?&1+Lp{3b4zB_n6B;<QvHRYzs_%P;6q(s|%XzRdgc<KVi$M(gB9CpozZB*Sm=Yo<^J*MS{Civ%uH'
    'WC!vZmo9O07*3aSHH`*0k<bezk8SdS8rB!3m3O`r-cPy9XsCG~jazkk%<TsjMfW}$%PpbPfw{-BPdiTmEC_SvbwACN@QRU=tb3|u'
    '?9K8h9MG~tU)-?i^N)a<WjbTVHx;VNGRLEdY&}-+H_p$A>wdmF|G&)}NFS)xM8T@ol+(>N<*^k93_!;zg$Lwk{14+BG0%u(ZwQA7'
    'jTw{D>OJBv?>kuPDNa*(?I@ph;gF)^3}v|?SbhsZT26G6U|JY54B_65jG}xs;?%`S8LRRnsV&KjlbE4IifUk-;jbJs>08Uw23+$V'
    ';?0aLvGZ64^psgUn-h9MTrejoR%QzmMr|~F#`pPI%<KET)=qwORs#qnWqO@a7|My=I^YpjhS4Qa($UUi`i6o?f(EoBEXgT#Len(V'
    '1TNTs7|Gvu{B4|esw8mI(VdHS;;<ecKG*+|iTL?DzxGlvJg@2xz?a@J565|ru3r8|<ioB&3)bX1=P%Q6!VvX~0pKsgaKg4c5FLX0'
    'c^W>^Z-7<Cja;l__F))4g*2tF%(aR~>*r}WW(qb~Nb0$_&(m;h12JJ9<mjXpAE)7XF3?j%9)_k-{X7lF4VUu03(-`{=VAEDk~Ic('
    'G=#1FJPeo9QGr*4K31ypmuWbj3zh)u@2kH}!?Dh#XIp7u0OI;Q4M+I*ykdNSkw7ZH48!H&fDKr+ifMfwhM%xP26&Pfgu|^z{&N~m'
    '7+e~J!Pp1=^E6yxBx7EKmXFhLqL_p^`ZCR5#^Fnur}G0ETHl|?;W%hwLyo8qpxoca;Vb_MG9^RT`pY;R&19<h-3$_6ei?`J{wYjZ'
    'Wmri3HV$8^WSCva)clueI2O!kWOHTV_f&qFhI3S076-04zuituC-Gl_6f>G#VqgWh<mX!6vq%z16bh12<gojRJ|N_z<~aHFa}fJ!'
    '7Jhc&M%}7)2Jt!lG7O*4kfodq&~xw4)9@)A<nwlZ8HTg-7m}ZXNY?$!FdUDtjleJ#s(9Rd9)=V4oP)`}_2)DkQ@e9=;Y)@VOl!YP'
    '!-=CIhpa9&(dS_}Q6(^&rS#9k@QGZBR1a5{vF$IzaE|FjE&y*A8>r92@F|97mk%FYX039X3zA#w5_<ADGEW@S;o0Z<c^J;A&qNoA'
    'L2<-C55tiM$A}Z8fe4FQNKpO3AU5~m)7?-dy1ZmHl0Of_%}?E+bv(ZQc^J;~1uc;&>8o<(PvdY_60>iPszMv<^E`aYN(nz*>_lhQ'
    'Mjcoe$&zMF@3yiT5_%ufPO}lfhk>|kfDr7)?aGgb5A*OvOXnN~O`cK1HtNrTxRl&+CfU$6)|#Iu;v6=-7r>UZJ3kM^PZT^%ighdt'
    '^KS!j`NF>^&z~pax(Cs+SSEb+%S3!h5P3cm`(H-l+zwk=0HVLRj(r@8V>M6ZF7dnJ501uzu$%a`jJRy*G{Y%Ev3Y+UisMO-L`<+9'
    'KF`Dv`bYFC60P#fOdM+@SyPd!&tV9ipEGehso$Az|2PvT>S5URJU-9FaVkg>w1+Z7pZ(KJoG3`g*y*7+TR+dl^_?f1!bgU4`twMf'
    'C^`*bWJs$&kHmQxK;NdEHkWZmP|$((pES0)&ul*z-uyTe$Do^m135prQ~5j;*XvXwC0h_nxxNp@Ss9hNhoqSeBmHwGPErH-8%K~m'
    'gn9fl6K8d^=1^IJ=r}(Q#mPZXPe;SG2yOLgCeERdWzg;Q>gSobu4Uk9j)eGaCO#$T!OBCTRp8l=GjT4-OZi->{WcS45e1X<Y@|8<'
    'KJMeJ+pIY+ORl#6Ar9fbSkmP`I1{J4*1?J=CGX$rILs@XTIYz+SPKwkI27&qgYtJ=GjccxyD=dthLK>Pk4h#?ks6}~$>vDe0*@9n'
    'y-f>s>7`KS<l=Elw9-*<IaL@uP96iRv(^aX81CF9^lv(G5QZy+eWW;S9z@*3`z`i)<&E~af8My9t+MRTON@8#95v#a5qlj3@L#y>'
    ';X6;G8-3IG+7g-@6iSsa)WDrklJ1X1H&b|290dzuxZhy4$MJ3*_lcQ!rpa%U)XX1eH0wyFMtmHiC#MWq%;Nc}jBwdr?EmRO(z1d6'
    'hV@F*lfy|@!cCHsx<7%;-TxkY6V88mTCOKdSvIu=Qmp#8A>_XpKx4+AhP}?Iy%|F=G2-<Psd`NDPi8zg&(Kdn%|PY19m4TgA28Pc'
    'A`Tsa_cOlB(}%^hviGO3e+Qu;`b>8ivxsjS4h2u9O|0Q9(KiVuLs2era+u#+Cxa$8jdtJ_4OdMj7bIoOauBVzH7Nfpk{E%L%5d%<'
    '!X)SVM_a<9CWe<VcaS;Pi8&?oP4O9X21$fT6#_`C&R-h-(ydLAM#%~6H3m_CB@hU9@F{Hl!O;8GM$NeIl$eyFCH^wB0){jk6P$I^'
    'c0ghf&l{iu%fq6dCPb;x`HC38ns0lraL9kI+@m1)d~g9U`e@ziEM5pMT(qlE;FuQo>RL7rD>M^uPa_Q}Hd6tCur)xm@)Sk1_XDuM'
    '4ynebvU?kB<b>U!1<T*&8}dC0Qs?xzFLF#a;YjmE-n3l_+vF0XyG;)t<*4GyMHBf57EMDPy4ahb_r|y%%J=eJnV@J7HRXp~2sGiS'
    'g6o}X))&c?UQ1`7E@^M|us}MHA2U_*2GE3Ul1XJaAFC-5FxJC93(HMElL=#mQ8ihkpdiUlHDXUGz7#<^QVoy~8iddul8(5})(8_<'
    'D+DP_h-E$W-S{*?6p#Qs>5FK1$laiKWJ*FFMI}?D3TSAAN?FXqWCCi&l6nhfP>bB%G|e1PIvP0Q|CeKtfVIL@Z!rK@8;%J%wGk|j'
    '?NLnckn1ma08XR2(Of56&8F8vSQSsWF+RX(k4`ZT49u3L=^V?PhX#RaBux^Kd?Ke?fG%*&ifscnoHtVp;YD1qpqCGrwF~b(X4uSj'
    '`(DhP+uhSCotn_}!)(qpARI#YZ%$#8DzM32Em|PW8k3Kz*@_d6j9|$DBn|rwtQ91B&)@5fL>+|Is9U<y)D8XmkUZ|i?-o1cWDn8P'
    'K(Wn!s>HD`KdT#d)L5s6c8pJ}Z)rAzoxem#e8J^EE}AA6)jt0^Ors#v^U3Iz`-5}Qk|Y_|U!p+OJ&I!XPA?YOL<{0I&?mrP76gDv'
    'Na0Y=_Cxo0#2SHwHl)i>E5}94x=g&znK|R-(?v$XA9-Qxt)AlnLNtcw>welqj!CwZg3zHC+#vWMABkFEEKJ!jNI1c0O9*Jw4Zt-d'
    'b{2fbEt~R`td&IP7J8DbJ*;GB(?IaV-T=HywYZdp$HVD1!ca*iM;yxZ6~^EY_G<Cz)sVv*qDN?<E^BZXv7Cpx`Q?5Ze=V&ZbXARM'
    'A~Sdsr(G)!Ulv-Es!VD|_e#pnfz@zk-a~pQYd9xY@7B%7TxNpiLccl1;l*5@pGEItTbCZP6X;At>*6HjTEUkG)}0A?(SD;}s5{xC'
    '-h>~6#5&8#N;;3i<GTo!fl-c6ueL<Is4H45@-O%!ZTlrbgpIh_s5cI@9}^k5B52>E#7c=<dmO(~i~`<E=b~AqiVixC$Do%y_2Xt#'
    'QA)>YE*%fF0wpL-hbeYo6SI`IFC;BduWL&(RilFvQIL#KDw#6T1@uDJgtCCV&^-)CvQ^|tf|WewaYEFl;|aQJeCInW7zT|wwZ|2('
    'o6o0FObz+ObiYsG%j3(}@AE(&opgX^lnH)m8p3C>mwcMW0~zu)J6|-W;~5wOBbxw2twbF9=1F)%k#r!5$;+7O)AkC1BoK%wLYQhw'
    'qJ7-Y8x)YSmxz*3&PI(5qPj8`;95B8oFp*admJ@GK(k$3152n-<7HKM_jM!=s`z=f45YfjR8IZ{;tyj-THJRxkU1l+YaO5@K=9;v'
    'TWFrgLI)>>cc@sB`aCQRDqH&O^m!AnEF(%TG%U>oc>^zV&L}F-9f{l*{FTa=45Bh=+Tj(QnUj&oGC;6uC^K<rWTx<@BNqkjWNhTU'
    'v#Dxj&B^c(8S`G{=bh5%6ox7^x&)v@M%-X8oYPbj2q-1FT?#FDemI~2+STi(@w637G6OOD4eT{^62a-Ns0y%=JwJ>j%32CSeW3cv'
    'p;qIT{-T&;$W6ATENWZ3w=|A~o#YtD0PBrt2|{Aqyt=r5A(eB;AsnL@*6A6b+1G$xL>$P5E0bw>rZ02)=GXqFm_d?G7N1s*tnWqm'
    'P^0vjAX>|4-qw&0naLu?g>5LsVSDQKp`=(Q1W(-A$^D{XP1<WE6Ys>I(QB_E2^SU3)Vsrn(NCu|{<`+Yo)}#4>apb%&m<IBGKfYc'
    '=z%+H(a0oU5;YT4lGGzK#>~<a&|Li=OXej&G#{*&m%fqjC9FS~dyoqW&P+-QxrSdtQ}BDq3^|;Hq*sJyyG^_JGXpm62~RN*yP@{Q'
    'GRE}8skutA(O(HuUD&}$G9gvXv@4P8;2$v})y+C??xfRF1r!%Dd8c0lxG!Dd-z*Iz_%$v_teyXBn9$63uIFLWxv3hc8B?Uogclp+'
    ';?kzb@S}x+JJL#~jtnsf)FXMmzg<8I1qJ+*kSwEApUW0tJn&N2!QhGUAp+8sVUutgT_`Y#gEc*Dnb5Ea<~e2gUAWsS<`!gzF~C~k'
    'a8jkum#^T-^spLiU%f(;$fD}xi$`|!+W>*zAKbr9iQau43!^HF-N{As_i-PaPW+0O*wNocjX%+Rw7Q}F<Mv@5Nk%50;8W3j-95NE'
    'TR-Y#ILbS^oZ>*gofBbx-8mg_E|@Oh#5q-0%SCwk<Y<i6wD5XYO^B8c@G&D?G<ZuvAT1uo8bflwYh<XQ46_j|Yx%F+!)AG~skYj0'
    'A4pm?9!3?`CZefJueZznG)He#Z>`IjH#u_DWDp=?J*bHYtKXO^jJnrrVjpo0T{HA4L9W{8(c{IAoOw|9ushXN0jaPq|3^%kicOX}'
    'C^^vU=SQ{Kt)jScruazuw@x@^uV%3hozN^|M?N3-UGVvAq;GIq{KmZ&R*%zonW~uK5rB$_-}-Ku7~>6pv3@Tp4@0Z^7SAd?%1cW$'
    'zLZfavhxK^7qvMs`IH3-IKdWgm6Q)!Dblg_okeD4Sw~8{YvctNbD`lYY<3P>4+9BPVEIhhAX1=Y(0h~wT$!<ch4HT@Az}pzs&HW1'
    'WTqBj80tvoW^N-4!FHz~HN=1MFey=BRFS!~)%SUNDBGsf>@8eSQ0~med&SM*eI3V7#r*V&)hh0bTHlPYmpr6l|MGiH{}%S~c)|{t'
    'dm{*Ae;syS4E(zIy~DrM$9b+E@>fBuqIc)!pVfSDa)T2id+2kOeLWCO`v#r{$R(A3Ny%{H{2biCUyj5g^-FRdj1IS<$7LvsbENc|'
    '^mEFe&_A3xhL((;mV8Z;LyqL#ia!o+P@IdFS9WC=)TQSCoy`XM>_Kq*RhkausrZy+#xt|W$5k0fc67s9c4=bS24)$MTK*}!WXaeq'
    '%}*_hMuKZI+wC?*$2uN_0ni22wVsrpsDy$Fhm^++`C3wbv=|%GdBG1Bk;Vu+i93Fa9O7b_NJ$y4XamV>qbGcJfqa0TXHIG=!5~`j'
    '4$9T^*9d#Ts@1}zo_SzouCCSTUT<-NLjBY}uC?H$dl=bkVQO{$hizmk<Y<R5t=<P{`_Isr8ymyvg24rJ6mk`%h6zQZbjt#(Wr#+_'
    'ADtdLCt0_7dSf054hP-UWU7UX5O(LJp?p)6u%?u4R(|O1%f%XLcrg0e!(QX%VKa{RAkuD=6E=V}HmS~TV>Tq9RdNiX(KbB}4SO)U'
    '%w$c+u>z6dx%5c0u;zvB3TlTNMJt`55|p9ypItt%$@u*7;IJY7ODrfpj5Zl&RWheCPGi!ji2<2eu_+9B$p*0&)W2!;VP0G0xSry<'
    'Nt&mKo7L4o!ITO!Cd?fiU`5!|=1umcfvHrEz3!(i2K`N*s%q|ZneW1ra3Caq8s72HHP3=DG53kr0H7TVd?E_vvd-@ZKc?=~V)Vvg'
    'O#?a}S|@KQcy1W(o9Pr1gH*NS{(uS*3M-9dWn%k!cgLRww@b}iMvJ;M8_Y2#AsWZV`amM5s+T|AJ3wucs^Om9`zH*(izF1tw!EQB'
    '-VRR<bzooNiDm@p(s_1M$)U}h(8q*{<6)RW<(IZ0=E^_b0X8e(AVZYcGNBb>!D+{rVk~f>NrC^VPn?G>d6yR29e5=whfEJfbH&-P'
    '4S3O*@L6)G7IMt;;;1P=m`Q1I@UdJI#QN4vvf|*PZwqh_zL$fH`Arm7X_);1VNeN~(u02Ko{_3kiE-m{UJ-`lN#=vt%4Xx+Eba)z'
    'B&C`baZ*iL<k=<rT`i~e^Eb1<?pe-gh&uqHlTytoEE|B171ta3nwT>qAu~NmN89ZDrQATqTi^nLPldl5IDfr{t`tX?)b=L=6i&+9'
    's7yLzh(`_BP;F_CqHlP`u1#4X5HTk@qPSvEbOqOKxh)F2sLJM$Oy_papv-W)KGkfs#1M(rjP$u1L+Z9?gTr7Hc+AWt#E^s81yoUS'
    'U@wv|tI*_4O9B&O94JmI;WGJ{utQ-aPsT%7y=J6zW!G06$Vn89cZw{iPt9hUxK}a!+NSMnVJBH;Ca*tHw9fIe2(rIT8&Go_==IJf'
    '|0RxLomf~&mrRksQbPkAC(jaBTb8|YGZzZQ$<G2vIG%7RK2MG{)Mr}+P+K#En*Dm*s8!NZH2Frh=`x)Hbo`-L^c6cFm?Byt0HZ8Z'
    '0z1T;ZfuepH*_H5(vn=I7WZTJ3{8)F-Ylt;p7Raxt{QdVjG(NI;_bYSd@GG5S^l^;gZzq_T#$N=I3ZYwxN;-KS&bBrf-BA9E(4R;'
    '`wS~H{MYXNX5m}0>crkV-`oaGOH6c#Hxz=FihKUVpND-M9^x|I8!l#Cgy238+q#1s5mg7yxmR1YCM>$bTmvidE8>Va*S#bY8VP!L'
    'YCpq^E|D#pnVdNF!-~vMw+T06Q`9AlwS1DmQL<&f%E2JjRouo+Gp|y++lYX(1cD_$8Nh?3)S!uA&Vhr8Z#`RcaPpnyoGr~*FU&<G'
    '%1M0i?z$|-oUUe|$AmIPru-F*uT}hm62K-CD1n@84};rmz%mz&7;)4ou(K&6oUnba%y~7aofyp*CkdaRGBQf_xfIhHZd=!Q*6%2^'
    '?EumF2}NTZ{j4Gr#CRz9WT|5U3*2A<0A`2OU@S-D5wqu@7{J^a-ZVv!h01>2^Ll;xxymEv+dSmH*zqV}D33@l&F>n^sY@JY8K6rw'
    '9RlrVJ<&qU&&7nc!1?jQR2r>xZl76?8H=gFb$~MDlBZ0g8P57&96N`}_f_UI>xYM&-1@y-k+(MbnG`5H!!XCT$zvck;v1-JVJtU4'
    'KwIp7EIC_A!Wa7ld~-_C|DBGp<us`>qAzgv?Bmcy<0L8Km;2GgH_-fnLGPwanBEn%L6KRAgIE@61)AjYHV#V|IUIWD&7<({T^I$_'
    'WMGQh4}vlL)GJFZ7im`L#Y3(@XGn)Z{As{C&L2jHacl>AbQXh%x{+2D!OOk%WRu)?LLEt3UN3~0HA>#@WI4jV_!kLr@otAl*rRlB'
    'UR+FQuS<o)wAp^&KkQr7KT{;9Y+sd1)3Ny4XlNj_D|#+cp)}wKWK-Em<H!1KY=IXfNE|cmTQ+GxGseg=#qGdO*bJ5_zsu-1Ur>}D'
    'Mz8biMa}>L+u*HMRgaXPRtBHHvP7c5{MULl{y|KZmPY~XzP;<NUPoQ>aRiy|LDNb-It&I2S>|hJy~2nRx##RqJUUDW3%VFCM-n);'
    'Fi;>HpwKxJfnQs0%@GdIbNMOJ_~|d_FZ1HVtYoUD9(K{SE~|5luDR4LFU6mt%c~VzPKz5T@=i)9baf2N0g)D4>BW3tdYHtV0KuZM'
    'r#}wY9=U`Jy%~=~ZhM%B#kMnyL>n=#x?~;Waq`K)`H8HmJ4do2Oa>od#n%FrkrNIE_Btjo7oF@hCSCEZOylTmHi(?AbHq@DKN%ID'
    ';c+Nv(U(JsbUDeG`<n|WIRT@IVCVhc?DMy`6OuPJu)G)&ESkBwoXAqU0biaH_guqh1j}qX#U#+SAtm-eRy6G%CJe$gYDjI{=0<yF'
    'ah%F9y+2`vW<2f<!$5;5<-)E@U^OF5jH+{lpL%syQxlOha*`E7gk>n0w7kuGq)6IYV;Z?+#{&^2k%O%b>j=tL8&YdUqa<DznpA^Z'
    '27ZjeEy*Cch1I65&-+@;P7sN7^D~@GiXP={sEj}I0yv9{1Jk4eu}^8Zu%lJB;=Mw|$K?n(p(lydo*i&k+Vd{XipT-iGZJR%G0~nL'
    'sJ5Z{8-E@gVqg=na;%F7@CFD0T>fPh;@M-{+?y6XHB<k2Yk68Oal(e=-*GPlMrRE*CMQ$avzB7ZLS7NXZVUEIdyc9XTouPte5<@7'
    'vaG7w^yVScV&o~aPgKvTGr;XI6gc7D?bD`4x&ur3=5d_NLY9%tS=>TOs9;pGoJiEL5|p+W*}lO|<d?i9{$Jut6M49#BD+aqsW7A4'
    '0t7h@>P5+T{yD<FChCGb2~|X=4>CQBx@Q7W?~oGo8ZaLN^8)wV>UnMvhO8Zp5fJEltw>s;4M+;$XA?u!hh$)YW~U)&(lCFE`Y;xd'
    'H}rV)5B@q#{JiM~8uj_ko4sU-Pyc1uIW%wQvm(`_1iZ<c04pA-mwlVV87f?~sJJAze_j)131nn$<|#t`fTb7qh~2lp@t;uK0+Hor'
    'JdCB_i(}6iui@p-W5AGS3<DTAK5cNfBkDu_=;H<1H5Z8~jQBhZJAol5$%&}8Lh);$^~S%LvF0!@WaKpsB&%8tg#04kbH5GleJTsI'
    '3=rrkUi$IeIHORPjSVrOkMak>F!xdt?E(lnP`qM;L1sUfFjG&1ILQoT3x$<h>>FOsc^+WITgV9k%vY1O+-n{8NpK%vmX}KyLEeWC'
    '3<YIHmH;R)sj)Z=F@?AWt9Wx)#34ZozVd2G0!`J6T8V8<Eqdc<1<<AIn0pujtgnYDT_c;Y7PWC!&1PZp8dZpTiFm@`4nyG8<X>Tz'
    'J9%!WaZf}oGMWb<c&aTGR22qjhw}?pBqur&F@aynZT~3eIQfCf?l{;P5p^D5t*%dG{q%~j?DjW{mXyXF3CS752B9q@tuyG}k(*$9'
    'kJvC%Pcz5aRYb`10$Yj?D<XobnIxUFVpRuOBvs-~u#hO{f?;-$6}RMmJk{CR_pU3FKLbSPTCHf(Rpu#-S>tLd^4=A|TwNG)3G{`|'
    '|8G?Hb|Q=h=-RrNESX^FOlb<E--|z<$XTcfm=PdjYteHMcO(DDr;#wh@X1)(TcHk46rQ}mEb(bcvYq6*eH#jv+dyt8*oVd<!I7>T'
    'u-S&kK)|3=sjk0E4%7inM-mK$A*2fRn%URB3wW#FKS&#Vn$FObe3AbacPmIfhR!sk^<j_pCaMu}1A}hl){#wts#giL7(_S5OXyLb'
    'Q<%9Y+t}gYjN2H9y2Bwm|5XdPb@GqW`h<yftHjr}1t1xKI>ilU#VN-GN?t~11KL-L#zE^By^r{?#C(YTrU{z?8bAe}KQBey0-2+d'
    '=S}KiYl7hZGif}+=uQzg;em^8u$;*YD~bVyte11d32nC};Ny~cjC`6@2~J@VCpw4Gd2WCutHGL+(y5`QXML_Y9cUd!Qp(2DWkMi$'
    'M9dYr<hlUf=elXxs^Rne5hY|M@!a~R!UZI(nW9XVjse8k7XItH_klW;B^|6`uEO*!M%PX7&x}+WY-o(4m4_JR{8~2Gh3dfM#6+6k'
    'rfw&)aGr0-LhD=IEX4~Ft*OH{O-FRYzC;wS8q7%kfUJy4u32nOC)rz;J+2BKRVNoQ&KIK?IY;E_ENWAUDC9O0<ussU!@&a<rlCoN'
    ');(;<Km%dFxwbWIVD-}A$iA-7387CVjM5N915a)%b^y!U&5kt5?9hQ2Etyq3IVnUl@XS8j#K@7JA#lQ^@9gTWa*h?)KHH<X2ho>8'
    'JIg)|)+AQ}`^bL))Did}fSr~`!ldu$9ibmLeA8B#BWDr8&pmI!sPG!4L)T{1?;nR3AH)eENUCGA1}6&5ITz)rj3ZAb3Nd|Siyreb'
    '`j0qXw)j%;w1asySyK0TSy!hDLV-@Py8n33&k$zbynsUGt&#3wG@{1sZ5c8PK?rGrShw*+kwl%-mK(Dg4TXf3e`(gw+C4T!$jE7*'
    '$6+0sPDTc2b^wy{FaUwj_ZgWa8-bpi3RXjtb(x2OHyvbupwNu_qDCoK8n|5#n=r-Y)m@fPaajwLO&qx`zLn$7MN_i1{+56YlC}2<'
    'M-$u`Iw8EeY!{BIk|vynZK{@)a#Oz1&~!n93gQTt#1<V+Yv#(;aS2J;1j8=sh%+GaD16-EcrY6<?ZUHG0Iq4dMUdc~Xt^-<QCm%_'
    'Fp~SsPgt)S&+$OqVjX3@2H7=5+L{F$m(gUh`HUnM=nn$!C?y^SC&tj2E>Bk@MGSY*Jy~&ik&?@pi0{=<fJqq?`?X2GTl{TVxl+l3'
    'lq`crV2!nDY4(xh4eTX>P6+x|8sI7lKWIrv#NX#eGK<ETE@h)qRP-ug%OpqK^WNP9b0!U|`TSEg^SjA4yGH?dsKOOfq*@-&lBx`e'
    'a*Wd$YP*oOv_wR>7;n?;h(k(nO8z~V+qcu-n%8m^*;HTD*LA3O5MZ6h=df<IF=W(d&3Pa;9hX4w*GJeSMeGj4@7`f3{79<qh-%|e'
    'M>l#zF;YLZSN6wN@!rf_mJ{}``G=x1gD|lnNNOBM%s#W%c-FAMY$67+^&W1t#5#%^^J+NTGAEnu&r#VSID-fq{<XLPWi&=Mm%PVi'
    'Rp=N|<~6-f!ZC?9C6JThCpm!9v6Y9E<s~|;MYvL!fmM$KOrFsOK*n1I8c1Oj57C#q7eixS`Jilh&#1`96OC^Li|L(1SM&qJ`@jL?'
    '(o$Lr9;>8gf1NVGZ>O|`%^o*G8>hw_>^jrqN=2CqMG|_}Ru`fWHw1lgaEW9l2XkFAtZjz5QcpPFaE=c~NO9fE`w=$-0}C_5+IX6E'
    'hAQ6gMds#w6zV;4ned`t&dy3++$Tk;$dDV)?%SG{>i-BPxV-VEyoOUp%CFsQ5h;eaq&X&sN98S@FzKvYYm;%xS&IyN`iSg@sluQq'
    'b225%4?)qfbQ)%}<$l_E*XIDo@Yf2jv*ajh$u+6?tgC{+)uQmId?-o~6oyOY@UlIbHyeS1#p_8%{m$5bf&?yG$|fEr%mD=+%_pO?'
    'P&}Nxf^l+>bprMoCSaRJqM3}oPjzMe_*lbK*JmG6HB=XLq{Qe&$CK6PQp>sk@MSvr0#`#LVp1C^&`CxB+0nK$Mh?n&h$J(Mt`WvM'
    '0L91Tz^MB2sGw&78ac)O2W@jsEEH>&aquyi=u9<%y+#gHf|pEN#U}G#WnMk5y=heLZu~NL9`hbM6Zl3(R&_?-h1^UYB<&tz;QY7@'
    '0ZR<;;y~cz#ERFjfxM9woQw5b&4w?aU~TB(o(-Jt*?Cd@qm}p-FD20UJQRf)ZXlj!`!GF_i@xsno;Oc&i}YwQBV?uq?1*#NpEN$c'
    '*N;QSMZ>6yu)x$%&kk1NIswC($+gebV*nG`3(zQmmKzC^=J!{m#efLwCF>X$Y<`<)7wZf*sxQNFMxI8xD~*FL$w_$<2U<1txQD?K'
    'KT?m{ImnuYSX_=2l9d?)b{lN`P?T$OMF{_j)!jNZMxeOEM;Ps&po{5mW2*g?iP6;9Z{R&qeqJ`5IkyE9abeElha!be`m=x`RqM_e'
    'ON1J1+~*6x5eZhFvv+5ZWdtFNEYN)-JaieA0OL|2jMq&gcdh%Tw<6U6&o0F!vR=sKT;tP7mst5r`j6%}%)r808!np3%Lky2)^s=V'
    '3V;-hNt%I)p4<e{Dg0~JGE=LUc+Q+rKTH_VRRq@6oUnmmMWOPK-HP^ub-IOj3nMLl1#Qx~V*%F-pG3XZ3P+9?sK+Pm^;;N66P)5u'
    '*x$~?=P<;cv?D4UVF3KFDUm&>wO-zWY<@(n7Y@>DJ<Ob$22&2lp8k2_SR9?LEl6h^V3|L(fB?|R4<l|M!<ay-ST#}w6Gl}HKECtQ'
    'x!&N{kg3mcD^aOUcAN1VtHAXUa?JTY9M+UTIG;<M!W%<Xk~;h`SgcRIEXqUZy}S*_NFd_}MjKKKj9<f2RC&JOV(;jfpSMyYHI^m{'
    '0}<QM+;Fm$R)R2n^>P$<AV_C9^w0MyO)SY3@||vW^x=-KVmohC=rJISixBpXi1M6N)@+3`h)4^?Wd9siun*60HZ^RU?VlN-@>PbY'
    'F1?6vqDg9>org3T7+R4jxoNQWh@*4Ne`^T|PYO|$6fL;V92S?mVv8Ae+iR3<423T`-U@?~M5`O8(2*<`pECPVf7;c;)VT#a$xRdm'
    '3KVIE4|Fhn7|HLEy?E(j$%h+FLIr~qx_WMpKO(X@OcAm>?^GEgp`Sjd!;mE*g+?Im18a%913h&MhAR;=g&~7NJ>0+nI)P${h7V_j'
    'jJJ5)7pkUN`P^dxKKzKdL{h6v$Y(FOurQQb_$5palZHS7Y3o<^sn#pQ1f~)zf;cES2=Ij8CSP@y0|rHOG)BL1f@CxBkllHgdGES1'
    'Z60?15HBXyDt{mKlc)6YEB`8N{&`7~Cj&RBZT~{fm>TO#%lx;fkKbv6_;D1kzmNLxFg|_dUxnpA49Fh3Z>-&+YqT11+5{dpiW1R;'
    'h`1LmyIqHr`S9It+*@B~x)jz6<A1kmd;RBPAc>b1Sc$#5-!DfQ=L_*4**_PheIdvc%MlsY0P`>zz~*s`c_?Cm30N)hR2F1_zq|_>'
    'n>a;*^T4Ahqd*NX#xycsa8+<3N&n1^BkONVJ|bj)``bwi@qsA-&Xvr<lmJR8Bb~*`K;-*Li(AR5<l+J8y<h`%F_`v?PEGoHrD?eS'
    'L3<Fm-Qy%g8%k2kSaiT|0!}bIu0UCNF<*so85iQ~XIT+N?48llrh1Xa?Dzq|1I&af6hedg6b;)K(jy0R^UJ#A`zrGZ!=&hnr<cyM'
    '_IwMRI-^%QfoRa`{ek=G06*XpPmg0cHg44h64UMrS{q0tk!D#O%n*tHNeJC8vnFpW(v0D(ds(Srzr{sr-W_T!0eS&(fP8_+WudAD'
    '_|<F(92gYnVl1^0^m7ZaRAno;q-Fm+l#nWEL4msDaRYv&$Xz>Z#8|v^<iNhg$MLMP)FSj*6s+PY(6qLS5v5D9zJ?myhDeul8es0E'
    'DY@bn{)~+ACZew1Rs^^<k*qkUjG@gC*yIH<*ek$A^!_(%YZ_C1d6;^~s05uL^P7WsnbGc?!w>I*r1?1-1}Zhv^kxBj7u~DVhp+_>'
    '7dl%@KXCh6pC)W{(l`ejo;a{E6nG1Qi%B*D@nChG7wx8BWy$XsKNK}D47hH8l~m+QL?wBTvHZ;kOR5?S+OT1=@0|QBItV9~oFeG3'
    'GvRq@eBF$XKp1lL?C28T$-_bNf>xtLxrw6~g8+4wv1XH;E${;krhor5+?GsR%v_0J*MMW9?NM(SLQGvOqiLOexEDBM4Pi;*v5iJr'
    '076a1%$f$D1A+(HqvOeI5VHl8+xg3<PcQ}wyV3%V=SG)5vc+MTb%YeQG0IB3EM%i;jL?$S<w&1Ews1OhJPI?b^R+|mPAiVU05Z_7'
    'A&rJQEbAE+N<PFWa>9v6J?@(!nMs@t&NUul(_&Ji8sDQ>gJ*4Yb&L#*3U+rflH88aVEYZaAK5)6Ol2V@zZG3_vY=FS?sGONpJ8;c'
    'MP7-$-0trB#Nlv02j~vuW5?%mcP_U9SaH_KNzyRKPLN{-x-MY%D3}l{Ye?B`o=-V*7F!hy!=u3dap;}ud!-fxIY78uZ6y!e{q05U'
    '{5aA|h+fs{PjXnp6rQ$g@nK{}td~ocA-qRbROim}21Vgyc5YBmCKrY%2CTHJ*v)C%oOB@N1Dt!_1D}Bw#LnD|qX=#b=qB*!`*&SU'
    '1L$haCb;zhWyj5yIIX%SWUj)8Xb%8R#<S&Klw3GiX(kSGBhk^&l+6b7p}2UNU}A*KY}Z5rL7dTGg@1GJ@dcKKMaceBt(&PkA$G4Y'
    'z7zWAB~)rAsxpFeqE3ki@=|I{{e!!phn@fD`9D(+v8ovD2E7?Fh!z(#*BVJC2nmPWkaL_v5SY*G_idrR#s5^2v1dhLJ<lCMv;AD-'
    'yaTDZ4~K=&F=(*x^1bc7m1o9X)=PLH6XQ=ydw*#*%5(W4^u^*`Z?7<G!n_NM*f8U*b8KLmcOrQ+f?M9?ZCl|d=0=)jFCi6Yy(HPf'
    'f(vT#rF3~Vpv1j{k+a@9JaIC-gjBqaxHNE|eWM3`k#XHMNf;Uqii2}-=Qy=qec@pX1ZPH8G`ex_iHuk^Si>M{>0Lc|QE&Pc$@3<#'
    'i&c)3hN40@VWKA%yd5O6Q4-`5LdDk>NS6=-9m+N0e5R~#TK&oUZ?w`SwvDDk{B8WVO)AACrMdBV!PBQp=Oa=YYJUVsCi+cwOF}NB'
    'V>)b65(SH)A@qdApsrlnhq5sl*#UIK!IR*V%z~kCdNTV1e7R~|e$1u$&Qr}85B{uhC6=IrMm!GGALR0}yLIO`*1BEr0Jk0BX;2U$'
    'EroBOR|2rU&WVorVZ2dLRm?D0y=I(Q*>-R`=FT@)q*Y9Uv#XU0H1(K$pFhos>%8?{LD#{3Po|@cy~Ej8NDxkk3bWXf@Ss(?qE_wU'
    'Cec`yjD}+)07{3MirA4C6#!zh$sVq|5%!yI9xTkOC=k2v958_Tn@rVX=E6*p^Ygaf5^Hw>E>Clsa)d@Rq<9dH?=F?B4UEo?B!drK'
    'c#xp-Fs+G`h6N2Nk%ZV4M%dh2!Zq==R3GhC%v&uwuA1yU+_==3^6%MVLdx^qp!DtmE&WOGBy~B884>74y&`YdICqzZ$nv_d#CXv7'
    'Vo?rfrLt@=m!p;=nO)usqB|(tzm=mL!)coXIibC3tq2h$RM+fruW)fPSet8`ZXMIR$(XO?`!wE@8Y4r$bWMx*p<z<LJdB1pSiI<`'
    'Deg%|0~f#0oFh^n9lw8VmKGWCfC<PV<$j}`6~uxNpXfA#TyvSjDFeI#EBdv7&!|yDlsWk%Yzei@xmUrz;mTp9PZsits~H*Lwj7wr'
    'Q-x76oCBV9_*2r*$(`0kf{HI?m5Zn0H-NCAxuHA7vd4;22XyCZ)93<jgXDllVKOgGGRwqhdKABx3f)dw*o)~}%uWpwGxRmh9wKg5'
    '@pR6^hr45P$u!-_iX8)9w0$&)g7#o`KADLPi6$19#lxxqL+X`mvo))rGOG0Qysug0&1PCT3z=J){!rkfw3sa&DZ*#J)GH(k4c-9o'
    'D&Pz|?bP!qXywwIo${g*HySlUQR$n<aqOJS5IcZus(QkGu);UxyTSl|HX2x203dl*!FqXqYWFz!aS%w&6wl(;R-#M26=6V$sVkF^'
    '@d_KF%%Cb#{g$AYkBk|JYPdWuzIQ(>DoaSKlthrnl3wb>iI{bT;D*<!P=XQiz-V}Oql(bGBPpQ;Zu6dk(<cV4EF46t%~J_w1(bj0'
    'cFs{jGX%os`Nx2=^`&qt0Nj_<c0_UC@XXKkzuXfH)<l<vuJ^sm@ZpR4pi7IFnjMR1w0{k&aH14JxsNe(F;7!^bP`@k{@4bzY=~LN'
    'AZmms4kARdrK>-_bCPg_$4h0nfm;KR#NcXKQ|v@79v0<s2SREUMv)9w<q;W>xj+zvj!#XF1cD`e%DZS+trX3Igh@HMi==j}&_*=_'
    '^WgJ0t_Xw0j<J$eZ%|MWj-9mq^S&P@bwD4%n1eB0BxEqyCilbgd#<N62$`l+1|uyPi+5-&dsAxT2lnN4&RJPIo=AFU${M4$mnTnr'
    '+L*7FZZm>l7H>umG~NQbxw^n9QH&r++X0X(gp(Gp9)MWZDbkAPLP{xD7mmWiXsgrgTFCiZN0gipAAsrEK@qA|jE2EkV%Y&FCpQ|)'
    ';jVBrl(fH5VKP}U(s#h`U>T>!F;f-Kp(Jasa?G=VrYg+Xesrp^vZI)=ZXK^4ZE9$^+xIf<3E-q{7Nh7{cXX-G?0i&?hQ|P-Tb#Ec'
    'ywJHP4S-lcFdEidKNR8)xnFm^TFxzQ08|lb>DAkzlH@b5>T!=jup%7osKQw{6u(iV3@G)hpQ=;&sC-*fh%?h@Hbwfq<MfsBog~ZW'
    'uq3jm_C~BJ#9RuEX{?qq=IyKdLn&g~h<)OZ_#`=8Y?O%bM*I;Ez`Dq9Il#7HY1dySAf^KsA`Xa<dDwZISSnMpW!D+0&|NVk<9~>Y'
    '7qrV+>73m@ML`Cio)uh>WD`%W)Sj-4pN;Lx8y7k~tV<~vP3Y1s|E41b&x*#u>=7qQD#naRerw+#e$l5I^J7I=R=WX)GmtrLLsSJw'
    'wPd5}VJM*CH3gYAtGa0*+0X>xFe#C;6dB46lx(bX%J>#78$>B==a2xwW`b3Wr=J0ek=8~auL!8?aT5wqRj%hU^wa<(JX;N|2s@`9'
    'llciA-e?^Zp$G$FQ&J<0LoNdr*)FM3y54^i8>1Q=@BG*W-v+f%+$&dzl?g*JK}*JqrAG%iNQ@>M@Tlbub_Ms1h+Aj{Df=JXUWMLO'
    'K`NXh_O2%h_@dkdrzso!h%N-J*&Z(pTyzn5A744k!K00E$~)KcC>jZ6#3ppaD)C>^Nm_z;l?Y=)Aa>PoJ9ZlzN&_Z1*+ptk*!f5D'
    '=#rngF)Jy7A;8S)BDHKpa91TzE{+vLqrzG>HvB2j-d+Y_Hdvfjj&L}(vxp~y;4@@pE0~yOz#thiVenIjxuQ_Xv^A>HFGG4m209+c'
    'FQQsh=Xv^If{e*9@7u!$J&p9n#iGQe@u8Z>e!`|E@XdKUb;po$$fu2V-oEE>6=9#1X6{(D_%ID3|KA1yCq?7Xr-2VH)HgpsOw5JO'
    'b~lhk0X>0qI7l^$1w+s3P$o&pZjYwhgybAa@$(&aN>nc4s?2(Llri$b3yeV70nnx`j5I)vln)gij5shk+=eJ6U`Wq1iU(S-=NsYt'
    '(;@bP4hR)uGu4qa1^rpXcNthM5kFYy%z?Y6Xr7ixChlbcZQBN#`IN_ADK~{g5}&^ZfunBQ5IotW(cE)<+<94)*;OO<Y@511H)13R'
    'Tt8^WaV?qvVH0)~YriKI0&60{++jRDTCxJLccoI1yd-gNkvif8G?p9Ui3|$DNWqfeB?(N9cDJ=0+(0Nk<$WIr*pk6+swTU`8lqLT'
    'Bye^gFa02C9n+fgvN418Oftfa?B)Em*Ai<QNk?)5rtos#sR-aMU@!UiD>O@&I>M^VUEPaIV&=52Xn!M5kYZU<;yt;h1k_nUfjCd`'
    '$E9x=OZ1f2t9cunaEIrq#O-9FN(IaAQ0KVctO)?;$c6$`0RhezpFK2triVdPd^B#%!<suFq|2kADm1Ym5pmCi`}bf_EBTj5hqk1s'
    'O?-HobUWl+n5$rlvWHDn`(q_`v+E`wjkbT}U{KVGB+JrrPz<6`%)LX$x&R-gn1(d9h3my59RFD^VW?1kv{I~T=!p!7{cVullg7%='
    'Nj*_wqd>s5PEnvsv40mGJIZNz1%vTBSWy*ds9bf8g@-dCsk$rjz+A$7ySfG_Nx^KOYcf47;Y}s6%G#{jn^JRPex7}+(gXslPbc-9'
    ')hgp?WH3%)&(!D|OyD$Vq?t<iSxLb6Q942AJ=zBN4uJ?|t~yQFpDF<s6f?b>8dm8v!WA#ur045P>Ac^D#)bKoWxK|(Ox8({KkfY4'
    'u4`=?Dbi(sl+_|EJzi_>ur%IykN8qXPWmMLGo;@mhq|B$t(%U%jqlAmX}&BGJWNgM`+shA^mf0BxVIaGwfEmnt@q=~OEWGY!q?{9'
    '*OB}~9>{4izp*#s=zdyJrZv@?QG4Hkz+htA|H0xF9o#HuL(0Uj4Z+;R`@&p8RiiV1kX4h83?6jfT7ndR=dYylZ{0`$A3R<OL)!*l'
    '8V>n|$tS{=T3lP&6duP4z$Y0Qpqzg(dCgLjop7a~Ak_Jb$t!U$J-)VnF?r1bLti#mTECdQ@__7GFtLWu9<SN3zb09Sn80U`*NlYH'
    '8!`6T<27UX_eOO6;_;fBgnl#Qc~S!z-=Za#7$-3zukqKRS-^Y^V&TwlMRiV8(#90&#)+|vYyxt^zu3X@Yu|f+ezt?nvKuINa}UrH'
    'AMIcXlb9@7u&NkV3WXCX8wiaYVH=P0be0ee-v1KH;OsYIz&1TEjDGUP+y5drlmAZB{%6=n&sdf_9#k>Jp8rA9*doA~Ow%Yb@;6R='
    'Hu@>dKZ?VdZB7T`2o-ODLEm6`={(=BC#DuPc4+WRH^Qa-sDvrqsha4#!!@542l=|`c<|<327vgMK~)^I10*m;5aluil9MZ3>2*O^'
    '0yK=FVfV0x65&}~8`lNfnYc(@z-fG3-;Zj9_Q?3*ou09-bGyzA)n04*Ha;%OggBamlgZVo9`x6tQb8wyj=CQ&Ou;Gzpeylt1LsbS'
    'U9UN5c6xuR!BKvqZ+XJ&{bN6eWtw`A6+|+f6^Pcul@+Il)%QhZZon@dPp<KCU*y0IR{OYEF2_e^S-9Ofzp1pNo_ro7{gmonuh{^S'
    'ohBiIE2b5E5}+*+zxWYQ3So5z0QZ;Q+P(q;>aUMvz0JJkHNCz_cGmc<@)tlyfFo4v<RoT*k!eBI9xt}0m;QX$(QJ-a4p55U`l6Gb'
    '^-WycZv;+!Z~AHjFMQzp;wZlE!dJ*FJ&3a#X#gSW-ZsvFI#7<DAUfC3=h4AKY9dor?${K?dj8ZXTU$HP_2nW#t0u*^sFM3V@A_Ob'
    '`n5s5L1nk}*cDj~QM6SU(<m-s?^(qvFw`B(I4fHi6inHoNGqit;#Q*^J1yC~m<MHl+xf}3F$^pPBkU~$mhG3mAA0w&FNKnR!ZkRP'
    'nQ#AR(<D@&;e#Q$0R;E!iJRu1FUL_fah4ZZ^jpr9C|I7sz}TNf%g&+UTAqHM{B_vJtLwwJ{*3$Aw31PZG;GAnncwcDgjLi&^*VjT'
    'Ej|;}rN;q@1Ln&ULUB_N@q~+8`Q?}Yh=R%u&XSJA@Z&9=OyPC(TG9JgVL!g}-=0o~C3Ma(&><-0kN@w(k%-NBux;PQ@E`uv&u{!^'
    '+{atz$7B4vsQ=jNq3J2-&Iw@;MAp{_#HoYSf7UR;=;(<Qhjv&-)9(8NqQ&{fMSgxjTezo3?`8aT*oW1)5uA8yg#T?6H;CvQUN7h#'
    '`0xvU#+}Fg-~SIgb$9O'
)
