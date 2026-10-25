"""Cut source triangles at exact garment opening planes, preserving UV interpolation."""
import numpy as np
def clip_openings(vertices,uv,faces):
 output=[];tex=[];tris=[]
 for face in faces:
  poly=[np.r_[vertices[i],uv[i]] for i in face]
  planes=[(1,.845,False),(1,.065,True)]
  center=vertices[face].mean(0)
  if abs(center[0])>.15 and center[1]<.67:planes.append((1,.625,True))
  for axis,value,above in planes:
   result=[]
   for i,a in enumerate(poly):
    b=poly[(i+1)%len(poly)];da=(a[axis]-value)*(1 if above else -1);db=(b[axis]-value)*(1 if above else -1)
    if da>=0:result.append(a)
    if (da>=0)!=(db>=0):result.append(a+(b-a)*(da/(da-db)))
   poly=result
   if len(poly)<3:break
  if len(poly)<3:continue
  start=len(output)
  for point in poly:output.append(point[:3]);tex.append(point[3:])
  for i in range(1,len(poly)-1):tris.append([start,start+i,start+i+1])
 values=np.c_[output,tex];unique,inverse=np.unique(np.round(values,7),axis=0,return_inverse=True)
 return unique[:,:3].astype('float32'),unique[:,3:].astype('float32'),inverse[np.array(tris)]
