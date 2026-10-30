import bpy, numpy as np, hashlib, shapely
from shapely.geometry import Polygon,Point,box
def co(o):
 a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);a=a.reshape(-1,3).astype(float);M=np.array(o.matrix_world);return a@M[:3,:3].T+M[:3,3]

def fingerprint(o):
 h=hashlib.sha256();h.update(np.array(o.matrix_world,dtype='<f8').tobytes());h.update(np.array([v.co[:] for v in o.data.vertices],dtype='<f4').tobytes())
 for f in o.data.polygons:h.update(np.array(f.vertices[:],dtype='<i4').tobytes())
 for uv in o.data.uv_layers:h.update(np.array([x.uv[:] for x in uv.data],dtype='<f4').tobytes())
 return h.hexdigest()

def keep_faces(o,keep):
 m=o.data;fs=[f for f,k in zip(m.polygons,keep) if k]
 if not fs:bpy.data.objects.remove(o,do_unlink=True);return
 used=sorted({v for f in fs for v in f.vertices});mapping={v:i for i,v in enumerate(used)};nm=bpy.data.meshes.new(m.name+'_v18');nm.from_pydata([m.vertices[v].co[:] for v in used],[],[[mapping[v] for v in f.vertices] for f in fs])
 for mat in m.materials:nm.materials.append(mat)
 nm.polygons.foreach_set('material_index',np.array([f.material_index for f in fs],np.int32));nm.update()
 for uv in m.uv_layers:
  layer=nm.uv_layers.new(name=uv.name);layer.data.foreach_set('uv',np.array([uv.data[i].uv[:] for f in fs for i in f.loop_indices],np.float32).ravel())
 for col in m.color_attributes:
  layer=nm.color_attributes.new(name=col.name,type=col.data_type,domain=col.domain);values=[col.data[i].color[:] for i in used] if col.domain=='POINT' else [col.data[i].color[:] for f in fs for i in f.loop_indices];layer.data.foreach_set('color',np.array(values,np.float32).ravel())
 o.data=nm

def clip_ground(o,cut):
 m=o.data;m.calc_loop_triangles();xyz=co(o);local=cut.intersection(box(*np.r_[xyz[:,:2].min(0),xyz[:,:2].max(0)]))
 if local.is_empty:return
 vv=[];ff=[];mats=[];cols=[];uvs=[[] for x in m.uv_layers];color=m.color_attributes[0] if m.color_attributes else None;changed=0
 for tri in m.loop_triangles:
  q=xyz[list(tri.vertices)];shape=Polygon(q[:,:2]);parts=[q]
  if shape.area<1e-9:continue
  if shape.intersects(local):
   diff=shape.difference(local)
   if shape.area-diff.area>1e-8:
    changed+=1;parts=[]
    for t in shapely.get_parts(shapely.constrained_delaunay_triangles(diff)):
     xy=np.array(t.exterior.coords)[:3];weights=np.linalg.solve(np.vstack([q[:,:2].T,np.ones(3)]),np.vstack([xy.T,np.ones(3)]));parts.append(np.c_[xy,weights.T@q[:,2]])
  for a in parts:
   if np.cross(a[1,:2]-a[0,:2],a[2,:2]-a[0,:2])<0:a=a[::-1]
   weights=np.linalg.solve(np.vstack([q[:,:2].T,np.ones(3)]),np.vstack([a[:,:2].T,np.ones(3)]));k=len(vv);vv.extend(a.tolist());ff.append([k,k+1,k+2]);mats.append(m.polygons[tri.polygon_index].material_index)
   if color:
    ix=list(tri.vertices) if color.domain=='POINT' else list(tri.loops);cols.extend((weights.T@np.array([color.data[i].color[:] for i in ix])).tolist())
   for idx,uv in enumerate(m.uv_layers):uvs[idx].extend((weights.T@np.array([uv.data[i].uv[:] for i in tri.loops])).tolist())
 if changed:
  if not ff:bpy.data.objects.remove(o,do_unlink=True);return
  nm=bpy.data.meshes.new(m.name+'_graded_v18');nm.from_pydata(vv,[],ff)
  for mat in m.materials:nm.materials.append(mat)
  nm.polygons.foreach_set('material_index',np.array(mats,np.int32));nm.update()
  if cols:nm.color_attributes.new(name=color.name,type='BYTE_COLOR',domain='POINT').data.foreach_set('color',np.array(cols,np.float32).ravel())
  for uv,values in zip(m.uv_layers,uvs):nm.uv_layers.new(name=uv.name).data.foreach_set('uv',np.array(values,np.float32).ravel())
  o.data=nm;o['modified_in_version']='v19'

