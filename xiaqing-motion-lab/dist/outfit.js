import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { setBodyTriangleMask } from './footwear.js?v=9.4';

export async function attachOutfit(model,modules){
 const panel=document.createElement('div');panel.className='outfit-controls';panel.style.cssText='position:fixed;left:16px;bottom:72px;z-index:6;background:#fffefaee;padding:8px 10px;border-radius:10px;font-size:12px;color:#425b49';
 panel.innerHTML='<label>套装 <select aria-label="更换套装" disabled><option value="suit">衬衫＋牛仔裤</option><option value="none">原身体</option></select></label> <span role="status">载入中…</span>';
 document.body.append(panel);const select=panel.querySelector('select'),status=panel.querySelector('[role="status"]');
 const group=new THREE.Group();group.name='Wardrobe_ShirtTrouser';group.visible=false;model.add(group);
 let installed=false,body,config;const attached=new Map();
 const neckPatch=model.getObjectByName('pl2001_pl2001_Face_Mat');const neckVisible=neckPatch?.visible;const neckOriginal=neckPatch?.geometry;let neckFitted;const oldNeck=[];model.traverse(o=>{if(o.isMesh&&o.name.startsWith('Neck_continuous_transition'))oldNeck.push({mesh:o,visible:o.visible});});
 const controller={group,enabled:false,setEquipped(on){if(!installed)return;this.enabled=!!on;group.visible=this.enabled;if(neckPatch){neckPatch.visible=neckVisible&&modules.modules.get('head').enabled;neckPatch.geometry=this.enabled&&neckFitted?neckFitted:neckOriginal;}for(const n of oldNeck){n.mesh.userData.outfitCovered=this.enabled;n.mesh.visible=!this.enabled&&n.visible&&modules.modules.get('head').enabled;}modules.setCovered([...attached.keys(),'penis'],this.enabled);setBodyTriangleMask(body,'shirt-trouser',config.hideTriangles,this.enabled);modules.update();}};
 try{
  const response=await fetch('./assets/wardrobe/shirt_trouser.json?v=ankle-fit-20261025');if(!response.ok)throw new Error('套装配置加载失败');config=await response.json();
  if(neckPatch && config.neckBridge){const d=config.neckBridge;neckFitted=new THREE.BufferGeometry();neckFitted.setAttribute('position',new THREE.Float32BufferAttribute(d.positions.flat(),3));neckFitted.setAttribute('uv',new THREE.Float32BufferAttribute(d.uv.flat(),2));neckFitted.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(d.joints.flat(),4));neckFitted.setAttribute('skinWeight',new THREE.Float32BufferAttribute(d.weights.flat(),4));neckFitted.setIndex(d.indices.flat());neckFitted.computeVertexNormals();neckFitted.computeBoundingSphere();}
  body=model.getObjectByName('pl2020_Skin_Mat');if(!body?.isSkinnedMesh||body.geometry.attributes.position.count!==config.positionCount)throw new Error('套装与角色不匹配');
  const gltf=await new GLTFLoader().loadAsync(config.asset+'?v=ankle-fit-20261025');const sources=[];let sharedSkeleton=null;gltf.scene.traverse(o=>{if(o.isSkinnedMesh)sources.push(o);});
  if(sources.length!==9)throw new Error('套装部位不完整');
  for(const mesh of sources){
   const id=mesh.name.replace(/^Suit_/,'');if(!modules.modules.has(id))throw new Error('未知套装部位：'+id);
   const bones=mesh.skeleton.bones.map(b=>model.getObjectByName(b.name));if(bones.some(b=>!b?.isBone))throw new Error('套装骨骼映射失败');
   const inverses=mesh.skeleton.boneInverses.map(m=>m.clone());mesh.removeFromParent();mesh.position.set(0,0,0);mesh.quaternion.identity();mesh.scale.set(1,1,1);group.add(mesh);sharedSkeleton ||= new THREE.Skeleton(bones,inverses);mesh.bind(sharedSkeleton,new THREE.Matrix4());
   mesh.userData.bodyModule=id;mesh.userData.originalMaterial=mesh.material;mesh.frustumCulled=false;mesh.castShadow=true;mesh.receiveShadow=true;
   attached.set(id,[mesh]);
  }
  for(const [id,meshes] of attached)modules.registerReplacement(id,meshes);
  installed=true;controller.setEquipped(true);select.disabled=false;status.textContent='';select.onchange=()=>controller.setEquipped(select.value==='suit');
 }catch(error){if(neckPatch)neckPatch.geometry=neckOriginal;group.removeFromParent();for(const [id] of attached)modules.registerReplacement(id,[]);if(body&&config)setBodyTriangleMask(body,'shirt-trouser',[],false);status.textContent='套装载入失败，已保留原身体';console.error(error);}
 return controller;
}
