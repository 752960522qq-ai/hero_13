import * as THREE from 'three';
export async function attachBodyModules(model){
 const response=await fetch('./assets/body-modules.json?v=2');if(!response.ok)throw new Error('身体模块配置加载失败');
 const config=await response.json(),body=model.getObjectByName(config.bodyMesh);
 if(!body?.isSkinnedMesh||body.geometry.attributes.position.count!==config.positionCount)throw new Error('身体模块与角色不匹配');
 const base=body.userData.wardrobeBaseIndex||body.geometry.index;
 const owners=new Map(),modules=new Map();
 for(const item of config.modules){
  for(const face of item.triangles)owners.set([0,1,2].map(c=>base.getX(face*3+c)).join(','),item.id);
  const mesh=body.clone(false);mesh.name='BodyModule_'+item.id;mesh.userData={bodyModule:item.id,originalMaterial:body.material};mesh.geometry=body.geometry.clone();mesh.geometry.setIndex([]);mesh.frustumCulled=false;body.parent.add(mesh);
  modules.set(item.id,{...item,mesh,enabled:true,attachments:[]});
 }
 model.traverse(o=>{if(o.isMesh&&!o.userData.bodyModule&&o!==body&&/Face_Mat|Eyelash|Tearline|Eyes_|fitted_bob|Neck_continuous/.test(o.name))modules.get('head').attachments.push(o);});
 // Native accessory surfaces must follow their anatomical slot as well.
 for(const [name,id] of [['pl2020_pl2000_Props_Mat','penis'],['pl2020_pl2020_Cardigan_Mat','torso']]){const mesh=model.getObjectByName(name);if(mesh)modules.get(id).attachments.push(mesh);}
 let previousIndex=null,footwear=null;
 const replacements=new Map();
 const controller={modules,setCovered(ids,on){for(const id of ids){const slot=modules.get(id);if(slot){slot.covered=!!on;for(const mesh of slot.attachments)mesh.visible=slot.enabled&&!slot.covered;}}},connectFootwear(slot){footwear=slot;for(const id of ['foot_l','foot_r'])slot.setModuleVisible(id,modules.get(id).enabled);},registerReplacement(id,meshes){replacements.set(id,meshes);},setVisible(id,on){const slot=modules.get(id);if(!slot)throw new Error('未知身体模块');slot.enabled=!!on;slot.mesh.visible=!!on;footwear?.setModuleVisible(id,on);for(const mesh of replacements.get(id)||[])mesh.visible=!!on;for(const o of slot.attachments)o.visible=!!on&&!slot.covered&&!o.userData.outfitCovered;},update(){
  body.visible=false;const geometry=body.geometry,index=geometry.index;
  for(const slot of modules.values()){
   const mesh=slot.mesh;for(const [key,attribute] of Object.entries(geometry.attributes))mesh.geometry.setAttribute(key,attribute);
   mesh.skeleton=body.skeleton;mesh.bindMatrix.copy(body.bindMatrix);mesh.bindMatrixInverse.copy(body.bindMatrixInverse);mesh.bindMode=body.bindMode;
   mesh.position.copy(body.position);mesh.quaternion.copy(body.quaternion);mesh.scale.copy(body.scale);mesh.visible=slot.enabled;for(const replacement of replacements.get(slot.id)||[])replacement.visible=slot.enabled;
  }
  if(index!==previousIndex){const buckets=new Map([...modules.keys()].map(k=>[k,[]]));
   for(let i=0;i<index.count;i+=3){const tri=[index.getX(i),index.getX(i+1),index.getX(i+2)],id=owners.get(tri.join(','));if(id)buckets.get(id).push(...tri);}
   for(const [id,indices] of buckets)modules.get(id).mesh.geometry.setIndex(indices);previousIndex=index;
  }
 }};
 controller.update();
 const panel=document.createElement('details');panel.style.cssText='position:fixed;left:16px;bottom:110px;z-index:6;background:#fffefaee;border:1px solid #dce3d8;border-radius:12px;padding:10px;max-height:45vh;overflow:auto;font-size:12px;color:#425b49';
 const summary=document.createElement('summary');summary.textContent='身体模块 · 15';panel.append(summary);
 for(const item of config.modules){const label=document.createElement('label');label.style.cssText='display:flex;gap:8px;margin-top:7px';const input=document.createElement('input');input.type='checkbox';input.checked=true;input.onchange=()=>controller.setVisible(item.id,input.checked);label.append(input,document.createTextNode(item.label));panel.append(label);}
 document.body.append(panel);return controller;
}
