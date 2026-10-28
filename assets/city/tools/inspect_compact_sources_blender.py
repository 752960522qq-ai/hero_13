"""Measure original source meshes and facade references without editing them."""
import argparse,json,gzip,sys,math
from pathlib import Path
import bpy,numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);baseline=json.loads((a.source/'city_plan.json').read_text());cfg=json.loads(gzip.decompress((a.source/'oldtown_expansion_plan.json.gz').read_bytes()));specs={r['instance_name']:r for r in cfg['models']};out=[]
for rec in baseline['real_buildings']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    file=rec.get('file',rec['source_filename']);bpy.ops.import_scene.gltf(filepath=str((a.source/'buildings'/file).resolve()));bpy.context.view_layer.update()
    o=next(o for o in bpy.context.scene.objects if o.type=='MESH');co=np.array([o.matrix_world@v.co for v in o.data.vertices],float);lo=co.min(0);hi=co.max(0);s=rec['uniform_scale'];axis=np.array(rec.get('local_axis_scale',[1,1,1]));turn=math.pi/2 if 'Corner_Shop_10' in rec['instance_name'] else 0
    r=specs.get(rec['instance_name'],{});o.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in o.data.loop_triangles]);v=co[tri];normal=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);area=normal[:,2]/2;cz=v[:,:,2].mean(1);mask=(area>0)&(cz<lo[2]+.15*(hi[2]-lo[2]))
    bins=np.round((cz[mask]-lo[2])/max((hi[2]-lo[2])*.001,1e-6)).astype(int);freq=np.bincount(bins,weights=area[mask]);winner=freq.argmax();floor=float(np.average(cz[mask][bins==winner],weights=area[mask][bins==winner]))
    floor=r.get('source_floor_reference',floor);front=r.get('source_front_reference',float(np.quantile(co[(co[:,2]>lo[2]+.18*(hi[2]-lo[2]))&(co[:,2]<lo[2]+.7*(hi[2]-lo[2])),1],.01)))
    pre=co[:,:2]*(s*axis[:2]);R=np.array([[math.cos(turn),-math.sin(turn)],[math.sin(turn),math.cos(turn)]]);pre=pre@R.T;mask=(co[:,2]>lo[2]+.17*(hi[2]-lo[2]))&(co[:,2]<lo[2]+.75*(hi[2]-lo[2]))
    if turn:
        front2=float(np.quantile(pre[mask,1],.01));yl,yh=pre[:,1].min(),pre[:,1].max();core=pre[mask&(pre[:,1]>yl+(yh-yl)*.35)&(pre[:,1]<yl+(yh-yl)*.8)];left,right=np.quantile(core[:,0],[.005,.995])
    else:front2=front*s*axis[1];left=r.get('source_core_left',lo[0])*s;right=r.get('source_core_right',hi[0])*s
    out.append({'instance_name':rec['instance_name'],'file':file,'uniform_scale':s,'local_axis_scale':axis.tolist(),'target_height_m':rec['target_height_m'],'source_bounds':[lo.tolist(),hi.tolist()],'source_floor_reference':floor,'turn':turn,'left':float(left),'right':float(right),'front':front2,'rotated_xy_bounds':[pre.min(0).tolist(),pre.max(0).tolist()]})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2));print('SOURCE_MEASURES_SAVED',len(out),flush=True)
