import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';

const defaults={
 type56:{name:'56 式',url:'./assets/type56.glb',supportGrip:[0,.08413,.31823],supportGripZRange:[.21823,.31823]},
 hanyang88:{name:'汉阳造',url:'./assets/hanyang88.glb',supportGrip:[0,.01879,.35068],supportGripZRange:[.25068,.35068]}
};
const supportActions=new Set(['Aim','RifleIdle','RifleRun']);
const visibleActions=new Set(['Aim','RifleIdle','RifleRun','Reload']);
const v=()=>new THREE.Vector3(),q=()=>new THREE.Quaternion(),m=()=>new THREE.Matrix4();

function disposeObject(root){
 const geometries=new Set(),materials=new Set(),textures=new Set(),images=new Set();
 root.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const material of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){materials.add(material);for(const value of Object.values(material))if(value?.isTexture){textures.add(value);const data=value.source?.data??value.image;for(const image of Array.isArray(data)?data:[data])if(image&&typeof image.close==='function')images.add(image);}}});
 for(const texture of textures)texture.dispose();for(const image of images){try{image.close();}catch{}}
 for(const material of materials)material.dispose();for(const geometry of geometries)geometry.dispose();
}
function point(matrix){return v().setFromMatrixPosition(matrix);}
function semanticPalm(rest,side){
 const wrist=rest.get(side+'_arm_wrist'),middle=rest.get(side+'_hand_middle_0'),index=rest.get(side+'_hand_index_0'),little=rest.get(side+'_hand_little_1');
 if(!wrist||!middle||!index||!little)return null;
 const w=point(wrist),z=point(middle).sub(w).normalize(),up=point(index).sub(point(little));up.addScaledVector(z,-up.dot(z)).normalize();
 if(z.lengthSq()<.9||up.lengthSq()<.9)return null;
 const x=v().crossVectors(up,z).normalize(),basis=m().makeBasis(x,up,z);
 // The asset origin is the firing grip, seated in the palm rather than at the wrist pivot.
 const center=w.clone().lerp(point(middle),.52),thumb=rest.get(side+'_hand_thumb_0');if(thumb)center.addScaledVector(point(thumb).sub(w),.12);
 basis.setPosition(center);
 return {socket:wrist.clone().invert().multiply(basis),offset:center.applyMatrix4(wrist.clone().invert())};
}

/** Geometry and source clips stay unchanged; the support arm is solved after animation. */
export function createWeaponViewer({onStatus=()=>{},manifestURL='./assets/weapons.json?v=r20'}={}){
 let character=null,binding=null,weapon=null,selected='none',serial=0,controller=null,loading=false,error=null,manifestPromise=null,lastAction='Idle',lastIKError=0,lastReachError=0,lastNominalReachError=0,supportPoint=null;
 const bindings=new WeakMap();let definitions={...defaults},overrides=[];
 function status(){
  const hidden=lastAction==='PistolIdle';
  let text=hidden?'手枪待机 · 当前未提供手枪模型':selected==='none'?'未装备武器':loading?'正在载入'+(definitions[selected]?.name||'武器')+'…':error?'武器载入失败，可重新选择重试':!binding?.rightPalm?'角色握持点不可用':!visibleActions.has(lastAction)?(definitions[selected]?.name||'武器')+' · 持枪动作中显示':definitions[selected]?.name||'武器';
  onStatus({selected,loading,error,text,visible:!!weapon?.visible,ikError:lastIKError,reachError:lastReachError});
 }
 function restoreOverrides(){for(const [bone,position,rotation,scale] of overrides){bone.position.copy(position);bone.quaternion.copy(rotation);bone.scale.copy(scale);}if(overrides.length&&character)character.updateMatrixWorld(true);overrides=[];}
 function remember(bone){if(bone&&!overrides.some(row=>row[0]===bone))overrides.push([bone,bone.position.clone(),bone.quaternion.clone(),bone.scale.clone()]);}
 function captureCharacter(model){
  if(bindings.has(model))return bindings.get(model);
  model.updateMatrixWorld(true);const inverse=model.matrixWorld.clone().invert(),bones=new Map(),rest=new Map();
  model.traverse(o=>{if(o.isBone){bones.set(o.name,o);rest.set(o.name,inverse.clone().multiply(o.matrixWorld));}});
  const state={model,bones,rest,rightPalm:semanticPalm(rest,'r'),leftPalm:semanticPalm(rest,'l')};bindings.set(model,state);return state;
 }
 function mount(){
  if(!weapon)return;weapon.removeFromParent();
  const wrist=binding?.bones.get('r_arm_wrist');if(!wrist||!binding.rightPalm){weapon.visible=false;return;}
  const definition=definitions[selected]||{},offset=new THREE.Vector3().fromArray(definition.socketOffset||[0,0,0]),rotation=new THREE.Euler().fromArray([...(definition.socketRotation||[0,0,0]),'XYZ']);
  const local=binding.rightPalm.socket.clone().multiply(m().compose(offset,q().setFromEuler(rotation),new THREE.Vector3(1,1,1)));
  wrist.add(weapon);local.decompose(weapon.position,weapon.quaternion,weapon.scale);weapon.updateMatrixWorld(true);weapon.visible=visibleActions.has(lastAction)&&lastAction!=='PistolIdle';
 }
 function setCharacter(model,prepared){
  restoreOverrides();if(weapon)weapon.removeFromParent();character=model||null;binding=model?(prepared||captureCharacter(model)):null;mount();status();
 }
 async function manifest(){
  if(!manifestPromise)manifestPromise=fetch(manifestURL,{credentials:'same-origin'}).then(response=>{if(!response.ok)throw new Error('武器握持数据未能载入');return response.json();}).then(data=>{for(const [id,definition] of Object.entries(data.weapons||data))if(defaults[id])definitions[id]={...defaults[id],...definition,name:definition.name||definition.label||defaults[id].name};}).catch(e=>{console.warn('使用默认武器握持数据',e);});
  return manifestPromise;
 }
 async function setWeapon(id){
  if(id!=='none'&&!defaults[id])id='none';
  const token=++serial;controller?.abort();controller=null;selected=id;error=null;loading=false;restoreOverrides();
  if(weapon){weapon.removeFromParent();disposeObject(weapon);weapon=null;}
  if(id==='none'){status();return true;}
  loading=true;status();const abort=new AbortController();controller=abort;
  try{
   await manifest();if(token!==serial)return false;
   const definition=definitions[id],response=await fetch(definition.url,{signal:abort.signal,credentials:'same-origin'});if(!response.ok)throw new Error('武器文件下载失败（HTTP '+response.status+'）');
   if((response.headers.get('content-type')||'').includes('text/html'))throw new Error('服务器返回的内容不是武器模型');
   const bytes=await response.arrayBuffer();if(bytes.byteLength<20||new DataView(bytes).getUint32(0,true)!==0x46546c67)throw new Error('武器模型文件不完整');
   const result=await new GLTFLoader().parseAsync(bytes,new URL('.',new URL(definition.url,location.href)).href);
   if(token!==serial){disposeObject(result.scene);return false;}
   weapon=result.scene;weapon.name='装备_'+id;weapon.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}});loading=false;controller=null;mount();status();return true;
  }catch(e){if(token!==serial||e?.name==='AbortError')return false;loading=false;controller=null;error=e?.message||String(e);console.error('武器载入失败',id,e);status();return false;}
 }
 function modelMatrix(bone){return character.matrixWorld.clone().invert().multiply(bone.matrixWorld);}
 function setWorldRotation(bone,world){remember(bone);const parent=bone.parent?bone.parent.getWorldQuaternion(q()):q();bone.quaternion.copy(parent.invert().multiply(world));bone.updateWorldMatrix(false,true);}
 function setModelMatrix(bone,desired){
  remember(bone);const world=character.matrixWorld.clone().multiply(desired),local=bone.parent?bone.parent.matrixWorld.clone().invert().multiply(world):world;local.decompose(bone.position,bone.quaternion,bone.scale);bone.updateWorldMatrix(false,true);
 }
 function updateTwistHelpers(){
  const names=['l_arm_humerus','l_arm_radius','l_arm_wrist'],[H,E,W]=names.map(n=>binding.bones.get(n));if(!H||!E||!W)return;
  character.updateMatrixWorld(true);const current=names.map(n=>modelMatrix(binding.bones.get(n))),rest=names.map(n=>binding.rest.get(n));
  const skin=current.map((matrix,i)=>q().setFromRotationMatrix(matrix).multiply(q().setFromRotationMatrix(rest[i]).invert()).normalize()),[qh,qr,qw]=skin;
  const helper=binding.bones.get('l_arm_humerus_twist_3_H'),helperRest=binding.rest.get('l_arm_humerus_twist_3_H');
  if(helper&&helperRest){const desired=m().makeTranslation(...point(current[1]).toArray()).multiply(m().makeRotationFromQuaternion(qh.clone().slerp(qr,.5))).multiply(m().makeTranslation(...point(rest[1]).negate().toArray())).multiply(helperRest);setModelMatrix(helper,desired);}
  const rel=qr.clone().invert().multiply(qw);if(rel.w<0)rel.set(-rel.x,-rel.y,-rel.z,-rel.w);
  const axis=point(rest[2]).sub(point(rest[1])).normalize(),projection=axis.clone().multiplyScalar(new THREE.Vector3(rel.x,rel.y,rel.z).dot(axis));
  let twist=new THREE.Quaternion(projection.x,projection.y,projection.z,rel.w);if(twist.lengthSq()<1e-12)twist.identity();else twist.normalize();
  for(let j=0;j<4;j++){
   const name='l_arm_radius_twist_'+j+'_H',bone=binding.bones.get(name),B=binding.rest.get(name);if(!bone||!B)continue;
   const rotation=qr.clone().multiply(q().slerp(twist,j/3));const desired=m().makeTranslation(...point(current[2]).toArray()).multiply(m().makeRotationFromQuaternion(rotation)).multiply(m().makeTranslation(...point(rest[2]).negate().toArray())).multiply(B);setModelMatrix(bone,desired);
  }
 }
 function solveSupport(){
  const H=binding.bones.get('l_arm_humerus'),E=binding.bones.get('l_arm_radius'),W=binding.bones.get('l_arm_wrist');if(!H||!E||!W||!binding.leftPalm)return;
  character.updateMatrixWorld(true);weapon.updateMatrixWorld(true);
  const definition=definitions[selected]||{},nominal=new THREE.Vector3().fromArray(definition.supportGrip||[0,0,.32]),wristRotation=W.getWorldQuaternion(q()),wristOffset=binding.leftPalm.offset.clone().applyQuaternion(wristRotation);
  const h=H.getWorldPosition(v()),e=E.getWorldPosition(v()),w=W.getWorldPosition(v()),upper=e.distanceTo(h),lower=w.distanceTo(e);
  if(upper<1e-5||lower<1e-5)return;
  // Select a reachable point on the supplied fore-end interval. Preserve a slight
  // elbow bend rather than stretching joints or leaving the support hand floating.
  const maxReach=Math.sqrt(upper*upper+lower*lower-2*upper*lower*Math.cos(THREE.MathUtils.degToRad(155))),minimumReach=Math.abs(upper-lower)+1e-5;
  supportPoint=nominal.clone();let target=supportPoint.clone().applyMatrix4(weapon.matrixWorld),goal=target.clone().sub(wristOffset),distance=goal.distanceTo(h);lastNominalReachError=Math.max(0,distance-maxReach);
  const range=definition.supportGripZRange;
  if(distance>maxReach&&Array.isArray(range)&&range.length===2){
   const direction=v().setFromMatrixColumn(weapon.matrixWorld,2),scale=direction.length();direction.normalize();
   const displacement=goal.clone().sub(h),projection=displacement.dot(direction),disc=projection*projection-(displacement.lengthSq()-maxReach*maxReach),lo=(Math.min(...range)-nominal.z)*scale,hi=(Math.max(...range)-nominal.z)*scale;
   let shift;
   if(disc>=0){const root=Math.sqrt(disc),entry=Math.max(lo,-projection-root),exit=Math.min(hi,-projection+root);if(entry<=exit)shift=THREE.MathUtils.clamp(0,entry,exit);}
   if(shift===undefined)shift=THREE.MathUtils.clamp(-projection,lo,hi);
   supportPoint.z+=shift/scale;target=supportPoint.clone().applyMatrix4(weapon.matrixWorld);goal=target.clone().sub(wristOffset);distance=goal.distanceTo(h);
  }
  const direction=goal.clone().sub(h);if(distance<1e-5)return;
  const reach=THREE.MathUtils.clamp(distance,minimumReach,maxReach),axis=direction.normalize(),along=(upper*upper-lower*lower+reach*reach)/(2*reach),height=Math.sqrt(Math.max(0,upper*upper-along*along));
  const pole=e.clone().sub(h).addScaledVector(axis,-e.clone().sub(h).dot(axis));
  if(pole.lengthSq()<1e-10){pole.set(0,1,0).addScaledVector(axis,-axis.y);if(pole.lengthSq()<1e-10)pole.set(1,0,0).addScaledVector(axis,-axis.x);}
  const newElbow=h.clone().addScaledVector(axis,along).addScaledVector(pole.normalize(),height),newWrist=h.clone().addScaledVector(axis,reach);
  const delta=q().setFromUnitVectors(e.clone().sub(h).normalize(),newElbow.clone().sub(h).normalize());setWorldRotation(H,delta.multiply(H.getWorldQuaternion(q())));
  const changedElbow=E.getWorldPosition(v()),changedWrist=W.getWorldPosition(v()),deltaLower=q().setFromUnitVectors(changedWrist.sub(changedElbow).normalize(),newWrist.clone().sub(changedElbow).normalize());setWorldRotation(E,deltaLower.multiply(E.getWorldQuaternion(q())));setWorldRotation(W,wristRotation);
  updateTwistHelpers();character.updateMatrixWorld(true);lastIKError=W.getWorldPosition(v()).add(binding.leftPalm.offset.clone().applyQuaternion(W.getWorldQuaternion(q()))).distanceTo(target);lastReachError=Math.abs(distance-reach);
 }
 function beforeAnimation(){restoreOverrides();}
 function update(actionName){
  const changed=lastAction!==actionName;lastAction=actionName;lastIKError=0;lastReachError=0;lastNominalReachError=0;supportPoint=null;
  if(weapon){weapon.visible=visibleActions.has(actionName)&&actionName!=='PistolIdle'&&!!binding?.rightPalm;if(weapon.visible&&supportActions.has(actionName))solveSupport();}
  if(changed)status();
 }
 function dispose(){++serial;controller?.abort();restoreOverrides();if(weapon){weapon.removeFromParent();disposeObject(weapon);}weapon=null;character=null;binding=null;}
 function getDebugState(){
  character?.updateMatrixWorld(true);weapon?.updateMatrixWorld(true);
  const rightGrip=weapon?v().applyMatrix4(weapon.matrixWorld):null,supportTarget=weapon?(supportPoint?.clone()||new THREE.Vector3().fromArray(definitions[selected]?.supportGrip||[0,0,.32])).applyMatrix4(weapon.matrixWorld):null,leftWrist=binding?.bones.get('l_arm_wrist'),leftGrip=leftWrist&&binding?.leftPalm?binding.leftPalm.offset.clone().applyMatrix4(leftWrist.matrixWorld):null;
  return {selected,action:lastAction,loading,error,visible:!!weapon?.visible,weaponMatrixWorld:weapon?weapon.matrixWorld.toArray():null,rightGripWorld:rightGrip?.toArray()||null,supportTargetWorld:supportTarget?.toArray()||null,leftGripWorld:leftGrip?.toArray()||null,supportIKActive:!!weapon?.visible&&supportActions.has(lastAction),supportError:lastIKError,reachError:lastReachError,nominalReachError:lastNominalReachError,supportGripUsed:supportPoint?.toArray()||null,clamped:lastReachError>1e-5,coordinates:'Three.js world meters; supportError is measured after IK'};
 }
 return {captureCharacter,setCharacter,setWeapon,beforeAnimation,update,dispose,getDebugState,get selected(){return selected;},get loading(){return loading;},get lastError(){return error;},get lastIKError(){return lastIKError;},get lastReachError(){return lastReachError;},get weapon(){return weapon;},get binding(){return binding;}};
}
