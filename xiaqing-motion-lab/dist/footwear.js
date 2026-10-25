import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';

export function setBodyTriangleMask(body,key,hidden,enabled){
  const s=body.userData.wardrobeMaskState||(body.userData.wardrobeMaskState={base:body.userData.wardrobeBaseIndex||body.geometry.index,masks:new Map()});
  body.userData.wardrobeBaseIndex=s.base;
  s.masks.set(key,{hidden:new Set(hidden),enabled});const kept=[],base=s.base;
  for(let i=0;i<base.count;i+=3){const tri=i/3;if(![...s.masks.values()].some(m=>m.enabled&&m.hidden.has(tri)))kept.push(base.getX(i),base.getX(i+1),base.getX(i+2));}
  body.geometry.setIndex(new THREE.BufferAttribute(new base.array.constructor(kept),1));
}

// A wardrobe slot owns its meshes, bind matrices, reversible skin mask and pose offset.
// It never edits the character GLB or animation clips.
export class FootwearSlot {
  constructor(model) {
    this.model=model; this.rootY=model.position.y; this.enabled=false; this.moduleVisibility={l:true,r:true};
    this.group=new THREE.Group(); this.group.name='Wardrobe_Shoes';
    this.model.add(this.group); this.pose=[]; this.masks=[]; this.meshes=[]; this.variantGroups=new Map(); this.activeVariant=null;
  }
  install(gltf,config,key='default') {
    if(this.variantGroups.has(key)) throw new Error('鞋款重复加载');
    const variantGroup=new THREE.Group();variantGroup.name=`Wardrobe_${key}`;variantGroup.visible=false;this.group.add(variantGroup);
    this.variantGroups.set(key,{group:variantGroup,config});
    if(this.activeVariant===null){this.activeVariant=key;this.config=config;}
    const targets=config.boneNames.map(name=>this.model.getObjectByName(name));
    if(targets.some(b=>!b?.isBone)) throw new Error('鞋子与当前脚骨不匹配');
    gltf.scene.updateMatrixWorld(true);
    const sources=[]; gltf.scene.traverse(o=>{if(o.isSkinnedMesh)sources.push(o);});
    if(sources.length!==(config.meshCount??2)) throw new Error('鞋子资源缺少左右脚网格');
    for(const mesh of sources) {
      const bones=mesh.skeleton.bones.map(b=>this.model.getObjectByName(b.name));
      if(bones.some(b=>!b?.isBone)) throw new Error('鞋子骨骼映射失败');
      const inverses=mesh.skeleton.boneInverses.map(m=>m.clone());
      mesh.removeFromParent(); mesh.position.set(0,0,0);mesh.quaternion.identity();mesh.scale.set(1,1,1);
      variantGroup.add(mesh); mesh.bind(new THREE.Skeleton(bones,inverses),new THREE.Matrix4());
      mesh.castShadow=true;mesh.receiveShadow=true;mesh.frustumCulled=false;
      const side=mesh.name.match(/_([LR])$/)?.[1]?.toLowerCase();
      if(!side)throw new Error('鞋子缺少左右脚标识');
      mesh.userData.bodyModule='foot_'+side;mesh.visible=this.moduleVisibility[side];
      mesh.userData.originalMaterial=mesh.material; this.meshes.push(mesh);
    }
    if(this.pose.length===0) for(const side of ['l','r']) for(const part of ['ankle','ball']) {
      const bone=this.model.getObjectByName(`${side}_leg_${part}`);
      this.pose.push({bone,raw:null,offset:new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),THREE.MathUtils.degToRad(part==='ankle'?config.ankleDegrees:config.ballDegrees))});
    }
    let body;
    this.model.traverse(o=>{if(o.isSkinnedMesh&&!o.userData.bodyModule&&!this.meshes.includes(o)&&o.geometry.attributes.position.count===config.mask.positionCount)body=o;});
    if(!body?.geometry.index) throw new Error('找不到鞋口遮挡所需的身体网格');
    if(this.masks.length===0){
      const geometry=body.geometry.clone(),original=geometry.index;
      const hidden=new Set(config.mask.hideTriangles),kept=[];
      for(let i=0;i<original.count;i+=3)if(!hidden.has(i/3))kept.push(original.getX(i),original.getX(i+1),original.getX(i+2));
      const masked=new THREE.BufferAttribute(new original.array.constructor(kept),1);
      const originalPosition=geometry.attributes.position,originalNormal=geometry.attributes.normal;
      const fittedPosition=originalPosition.clone(),fittedNormal=originalNormal.clone();
      for(const [i,x,y,z] of config.geometryFit.positions)fittedPosition.setXYZ(i,x,y,z);
      for(const [i,x,y,z] of config.geometryFit.normals)fittedNormal.setXYZ(i,x,y,z);
      body.userData.wardrobeBaseIndex=body.userData.wardrobeBaseIndex||original;body.geometry=geometry;this.masks.push({body,geometry,original,masked,originalPosition,originalNormal,fittedPosition,fittedNormal,hidden:config.mask.hideTriangles});
    } else if(this.masks[0].geometry.attributes.position.count!==config.mask.positionCount) throw new Error('不同鞋款的角色模型不一致');
    variantGroup.visible=this.enabled&&key===this.activeVariant;
  }
  setModuleVisible(id,on){
    const side=id==='foot_l'?'l':id==='foot_r'?'r':null;if(!side)return;
    this.moduleVisibility[side]=!!on;
    for(const mesh of this.meshes)if(mesh.userData.bodyModule===id)mesh.visible=!!on;
  }
  selectVariant(key){
    const variant=this.variantGroups.get(key);if(!variant)throw new Error('鞋款尚未加载');
    this.beforeAnimation();this.activeVariant=key;this.config=variant.config;
    for(const p of this.pose)p.offset.setFromAxisAngle(new THREE.Vector3(1,0,0),THREE.MathUtils.degToRad(p.bone.name.endsWith('_ankle')?this.config.ankleDegrees:this.config.ballDegrees));
    this.setEquipped(this.enabled);
  }
  beforeAnimation() {
    for(const p of this.pose)if(p.raw){p.bone.quaternion.copy(p.raw);p.raw=null;}
    this.model.position.y=this.rootY;
  }
  afterAnimation() {
    if(!this.enabled)return;
    for(const p of this.pose){p.raw=p.bone.quaternion.clone();p.bone.quaternion.multiply(p.offset);}
    this.model.position.y=this.rootY+this.config.rootLift;
    this.model.updateMatrixWorld(true);
  }
  setEquipped(value) {
    this.beforeAnimation();this.enabled=!!value;for(const [key,variant] of this.variantGroups)variant.group.visible=this.enabled&&key===this.activeVariant;
    for(const m of this.masks){setBodyTriangleMask(m.body,'shoes',m.hidden,this.enabled);m.geometry.setAttribute('position',this.enabled?m.fittedPosition:m.originalPosition);m.geometry.setAttribute('normal',this.enabled?m.fittedNormal:m.originalNormal);m.geometry.computeBoundingBox();m.geometry.computeBoundingSphere();}
    this.afterAnimation();
  }
}

export async function attachFootwear(model,{onFocus}={}) {
  const slot=new FootwearSlot(model);
  const box=document.createElement('div');box.className='footwear-controls';
  box.innerHTML='<label>鞋子 <select aria-label="更换鞋子" disabled><option value="black">黑色高跟鞋（整脚）</option><option value="stud">铆钉高跟鞋（整脚）</option><option value="beige">米色高跟鞋（整脚）</option><option value="navy">海军蓝玛丽珍（整脚）</option><option value="sandal">凉鞋（整脚）</option><option value="red">红色运动鞋（整脚）</option><option value="none">不穿鞋</option></select></label><button type="button">查看脚部</button><span role="status">鞋子载入中…</span>';
  document.body.appendChild(box);
  const select=box.querySelector('select'),status=box.querySelector('[role="status"]');
  box.querySelector('button').onclick=()=>onFocus?.();
  async function loadVariant(key){
    const configName=key==='beige'?'beige_feet':key==='navy'?'navy_mary_jane_feet':key==='sandal'?'sandal_feet':key==='red'?'red_sneakers_feet':key==='stud'?'studded_high_heel_feet':'office_feet';
    const response=await fetch(`./assets/wardrobe/${configName}.json?v=9.1`);if(!response.ok)throw new Error('鞋子配置加载失败');
    const config=await response.json();const gltf=await new GLTFLoader().loadAsync(`${config.asset}?v=9.1`);slot.install(gltf,config,key);
  }
  try {
    await loadVariant('black');slot.selectVariant('black');slot.setEquipped(true);select.disabled=false;status.textContent='';
    select.onchange=async()=>{
      const key=select.value;if(key==='none'){slot.setEquipped(false);return;}
      try {
        if(!slot.variantGroups.has(key)){select.disabled=true;status.textContent=(key==='navy'?'海军蓝玛丽珍':key==='sandal'?'凉鞋':key==='red'?'红色运动鞋':key==='stud'?'铆钉高跟鞋':key==='black'?'黑色高跟鞋':'米色鞋子')+'载入中…';await loadVariant(key);}
        slot.selectVariant(key);slot.setEquipped(true);status.textContent='';
      } catch(error) {select.value=slot.activeVariant||'black';status.textContent='鞋子加载失败，可刷新重试';console.error(error);}
      finally {select.disabled=false;}
    };
  } catch(error) {
    slot.setEquipped(false);status.textContent='鞋子加载失败，可刷新重试';console.error(error);
  }
  return slot;
}
