"""Sample upward mesh surfaces with a planar BVH and double-precision heights.

Long 3D ray casts against thin, vertical apron sides can produce spurious
heights. Use the BVH only to find XY triangles, then solve their height planes.
"""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

class HeightField:
    def __init__(self,objects):
        pieces=[]
        for obj in objects:
            obj.data.calc_loop_triangles()
            co=np.empty(len(obj.data.vertices)*3,np.float32);obj.data.vertices.foreach_get('co',co);co=co.reshape(-1,3).astype(np.float64)
            matrix=np.array(obj.matrix_world,np.float64);co=co@matrix[:3,:3].T+matrix[:3,3]
            faces=np.array([t.vertices[:] for t in obj.data.loop_triangles],np.int32)
            tri=co[faces];a=tri[:,1,:2]-tri[:,0,:2];b=tri[:,2,:2]-tri[:,0,:2];det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
            pieces.append(tri[det>1e-8])
        self.tri=np.concatenate(pieces)
        xy=self.tri[:,:,:2].reshape(-1,2);unique,indices=np.unique(xy,axis=0,return_inverse=True)
        self.tree=BVHTree.FromPolygons(np.c_[unique,np.zeros(len(unique))].tolist(),indices.reshape(-1,3).tolist(),all_triangles=True)
    def height(self,xy):
        p=np.array(xy[:2],np.float64);values=[]
        for _,_,i,_ in self.tree.find_nearest_range(Vector((float(p[0]),float(p[1]),0)),.002):
            tri=self.tri[i];a=tri[0,:2];u=tri[1,:2]-a;v=tri[2,:2]-a;delta=p-a;det=u[0]*v[1]-u[1]*v[0]
            s=(delta[0]*v[1]-delta[1]*v[0])/det;t=(u[0]*delta[1]-u[1]*delta[0])/det
            if min(1-s-t,s,t)>=-1e-7:values.append((1-s-t)*tri[0,2]+s*tri[1,2]+t*tri[2,2])
        return None if not values else float(max(values))
