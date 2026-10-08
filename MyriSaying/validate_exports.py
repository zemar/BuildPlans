"""Independently read and audit generated STL and 3MF files with trimesh."""
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

import MyriSaying as model


def validate():
    folder = model.HERE/'exports'
    report = {}
    generated,_ = model.build()
    expected = {name: (color,mesh) for name,color,mesh in generated}
    paths = sorted(folder.glob('*.stl'))
    assert len(paths)==5, 'Expected exactly five current STL parts'
    for path in paths:
        mesh = trimesh.load_mesh(path)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0, path
        assert np.all(mesh.area_faces>1e-12), path
        shells = mesh.split()
        assert all(s.is_watertight and s.volume>0 for s in shells), path
        report[path.name] = {'bounds_mm':mesh.bounds.tolist(),'volume_mm3':float(mesh.volume),
                            'closed_shells':len(shells),'watertight':True,'consistent_winding':True,
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    archive_path = folder/'MyriSaying.3mf'
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read('3D/3dmodel.model'))
    ns = {'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    assert root.get('unit')=='millimeter'
    colors = root.findall('m:resources/m:basematerials/m:base',ns)
    assert {c.get('name'):c.get('displaycolor') for c in colors}==model.COLORS
    meshes = {}
    for obj in root.findall('m:resources/m:object',ns):
        element = obj.find('m:mesh',ns)
        if element is None:
            continue
        vertices = [[float(v.get(axis)) for axis in ('x','y','z')]
                    for v in element.findall('m:vertices/m:vertex',ns)]
        faces = [[int(t.get(i)) for i in ('v1','v2','v3')]
                 for t in element.findall('m:triangles/m:triangle',ns)]
        mesh = trimesh.Trimesh(vertices=vertices,faces=faces)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        name = obj.get('name')
        meshes[name] = mesh
        assert obj.get('pid')=='1'
        assert colors[int(obj.get('pindex'))].get('name')==expected[name][0]
        assert np.allclose(mesh.volume, model.audit(expected[name][1])['volume_mm3'])
    assert set(meshes)==set(expected)
    assert len(root.findall('m:resources/m:object/m:components/m:component',ns))==5
    # Undo the tilt to check face dimensions and true plate thickness.
    panel = meshes['Plaque - Black'].vertices.copy()
    panel[:,2] -= model.THICKNESS_MM*math.sin(math.radians(model.LEAN_DEGREES))
    c,s = math.cos(math.radians(model.LEAN_DEGREES)),math.sin(math.radians(model.LEAN_DEGREES))
    unlean = panel@np.array([[1,0,0],[0,c,s],[0,-s,c]])
    assert np.allclose(np.ptp(unlean,axis=0),
                       [model.WIDTH_MM-2*model.FRAME_MM,model.THICKNESS_MM,
                        model.HEIGHT_MM-2*model.FRAME_MM])
    for name in ('Left support - Black','Right support - Black'):
        assert abs(meshes[name].bounds[0,2])<1e-7
        assert np.count_nonzero(np.isclose(meshes[name].vertices[:,2],0))==4
    bounds = np.vstack([m.bounds for m in meshes.values()])
    size = bounds.max(axis=0)-bounds.min(axis=0)
    report['3mf'] = {'parts':len(meshes),'overall_xyz_mm':size.tolist(),
                     'color_assignments':{name:expected[name][0] for name in meshes},
                     'plate_thickness_mm':model.THICKNESS_MM,'backward_lean_degrees':model.LEAN_DEGREES,
                     'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest()}
    (folder/'independent-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    model.LOGGER.info('INDEPENDENT VALIDATION PASSED: %s',report['3mf'])
    print('Passed independent STL/3MF validation:',size.round(3),'mm; panel',model.THICKNESS_MM,'mm')


if __name__ == '__main__':
    model.start_log()
    try:
        validate()
    except Exception:
        model.LOGGER.exception('Independent validation failed')
        raise
    finally:
        model.close_log()
