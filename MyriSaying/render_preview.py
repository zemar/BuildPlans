"""Render actual mesh geometry on the CPU; requires NumPy and Pillow only."""
import numpy as np
from PIL import Image

import MyriSaying as model


def render(parts, position, filename):
    width, height = 1400, 900
    target = np.array([0., 15., 48.])
    toward_camera = np.array(position)-target
    toward_camera /= np.linalg.norm(toward_camera)
    right = np.cross([0.,0.,1.], toward_camera)
    right /= np.linalg.norm(right)
    up = np.cross(toward_camera, right)
    basis = np.array([right, -up, toward_camera]).T
    projected = [(np.asarray(mesh[0])-target)@basis for _,_,mesh in parts]
    all_points = np.vstack(projected)
    low, high = all_points[:,:2].min(axis=0), all_points[:,:2].max(axis=0)
    scale = min((width-160)/(high[0]-low[0]), (height-160)/(high[1]-low[1]))
    center = (low+high)/2
    pixels = np.full((height,width,3), [232,228,221], dtype=np.uint8)
    depth = np.full((height,width), -np.inf)
    light = np.array([-.4,-.7,1.])
    light /= np.linalg.norm(light)
    for (_,color,(vertices,faces)), screen in zip(parts, projected):
        rgb = np.array([int(model.COLORS[color][i:i+2],16) for i in (1,3,5)])
        rgb = np.maximum(rgb, 22)
        screen[:,:2] = (screen[:,:2]-center)*scale+[width/2,height/2]
        vertices = np.asarray(vertices)
        for face in faces:
            world = vertices[list(face)]
            normal = np.cross(world[1]-world[0], world[2]-world[0])
            normal /= np.linalg.norm(normal)
            if np.dot(normal,toward_camera) <= 0:
                continue
            p,q,r = screen[list(face)]
            lo = np.maximum(np.floor(np.minimum(np.minimum(p[:2],q[:2]),r[:2])).astype(int),0)
            hi = np.minimum(np.ceil(np.maximum(np.maximum(p[:2],q[:2]),r[:2])).astype(int),[width-1,height-1])
            if np.any(hi<lo):
                continue
            xx,yy = np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
            denominator = (q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1])
            if abs(denominator)<1e-12:
                continue
            a = ((q[1]-r[1])*(xx-r[0])+(r[0]-q[0])*(yy-r[1]))/denominator
            b = ((r[1]-p[1])*(xx-r[0])+(p[0]-r[0])*(yy-r[1]))/denominator
            c = 1-a-b
            zz = a*p[2]+b*q[2]+c*r[2]
            box = np.s_[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            visible = (a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(zz>depth[box])
            depth[box][visible] = zz[visible]
            shade = .72+.28*max(0.,np.dot(normal,light))
            pixels[box][visible] = np.clip(rgb*shade,0,255).astype(np.uint8)
    Image.fromarray(pixels).save(model.HERE/filename)
    model.LOGGER.info('Rendered actual mesh geometry: %s', filename)


if __name__ == '__main__':
    model.start_log()
    try:
        parts,_ = model.build()
        render(parts, (220,-380,200), 'preview-3d.png')
        render(parts, (-230,380,190), 'preview-rear.png')
    except Exception:
        model.LOGGER.exception('Preview rendering failed')
        raise
    finally:
        model.close_log()
