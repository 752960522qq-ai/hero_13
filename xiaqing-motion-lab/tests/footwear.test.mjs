import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {GLTFLoader} from '../dist/vendor/GLTFLoader.js';
import {FootwearSlot} from '../dist/footwear.js';
const root=new URL('../',import.meta.url);
// Geometry/animation test: omit GPU-only textures, retain every vertex and animation byte.
async function load(path){
 const data=fs.readFileSync(new URL(path,root));const n=data.readUInt32LE(12),j=JSON.parse(data.subarray(20,20+n));
 j.materials=(j.materials||[]).map(()=>({}));j.images=[];j.textures=[];
 let text=Buffer.from(JSON.stringify(j));text=Buffer.concat([text,Buffer.alloc((4-text.length%4)%4,32)]);
 const bin=data.subarray(20+n),out=Buffer.alloc(20+text.length+bin.length);data.copy(out,0,0,12);out.writeUInt32LE(out.length,8);out.writeUInt32LE(text.length,12);out.writeUInt32LE(0x4e4f534a,16);text.copy(out,20);bin.copy(out,20+text.length);
 return new GLTFLoader().parseAsync(out.buffer.slice(out.byteOffset,out.byteOffset+out.length),'');
}
const model=await load('dist/assets/xiaqing_native_animated.glb'),shoes=await load('dist/assets/wardrobe/office_feet_rigged.glb');
const config=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/office_feet.json',root)));
assert.equal(createHash('sha256').update(fs.readFileSync(new URL('dist/assets/xiaqing_native_animated.glb',root))).digest('hex'),config.bodySHA256);
const slot=new FootwearSlot(model.scene);slot.install(shoes,config);slot.setEquipped(true);
const left=slot.meshes.find(m=>m.name.endsWith('_L')),right=slot.meshes.find(m=>m.name.endsWith('_R'));
assert(left&&right);const a=left.geometry.attributes.position,b=right.geometry.attributes.position;
assert.equal(slot.meshes.length,4);assert.equal(a.count,b.count);
const nativeBody=(()=>{let found;model.scene.traverse(o=>{if(o.isSkinnedMesh&&!slot.meshes.includes(o)&&o.geometry.attributes.position.count===config.mask.positionCount)found=o;});return found;})();
let seamMax=0;
for(const mesh of slot.meshes){const w=mesh.geometry.attributes.skinWeight;for(let i=0;i<w.count;i++)assert(Math.abs(w.getX(i)+w.getY(i)+w.getZ(i)+w.getW(i)-1)<1e-6);}
const mixer=new THREE.AnimationMixer(model.scene),v=new THREE.Vector3();let minY=Infinity,maxExtent=0,samples=0;const clips={};
for(const clip of model.animations){
 slot.beforeAnimation();mixer.stopAllAction();const action=mixer.clipAction(clip);action.play();let low=Infinity;
 for(let k=0;k<12;k++){
  slot.beforeAnimation();mixer.setTime(clip.duration*k/12);slot.afterAnimation();model.scene.updateMatrixWorld(true);
  const box=new THREE.Box3();for(const mesh of slot.meshes){mesh.skeleton.update();for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,v);v.applyMatrix4(mesh.matrixWorld);assert(Number.isFinite(v.x+v.y+v.z));box.expandByPoint(v);}}
  nativeBody.skeleton.update();for(const seam of config.seams){const foot=slot.meshes.find(m=>m.name==='OfficeFootSkin_'+seam.side);for(let s=0;s<seam.nativeIndices.length;s++){const p=nativeBody.getVertexPosition(seam.nativeIndices[s],new THREE.Vector3()).applyMatrix4(nativeBody.matrixWorld);const q=foot.getVertexPosition(seam.accessoryIndices[s],new THREE.Vector3()).applyMatrix4(foot.matrixWorld);seamMax=Math.max(seamMax,p.distanceTo(q));}}
  low=Math.min(low,box.min.y);maxExtent=Math.max(maxExtent,box.getSize(v).length());samples++;
 }
 clips[clip.name]={minimumShoeY:low};minY=Math.min(minY,low);
}
const quats=slot.pose.map(p=>p.bone.quaternion.clone());
for(let i=0;i<300;i++){slot.beforeAnimation();slot.afterAnimation();}
slot.pose.forEach((p,i)=>assert(p.bone.quaternion.toArray().every((x,k)=>Math.abs(x-quats[i].toArray()[k])<1e-12),'Paused pose must not accumulate'));
const raw=slot.pose.map(p=>p.raw.clone());slot.setEquipped(false);slot.pose.forEach((p,i)=>assert(p.bone.quaternion.toArray().every((x,k)=>Math.abs(x-raw[i].toArray()[k])<1e-12)));assert.equal(model.scene.position.y,slot.rootY);for(const m of slot.masks){assert.equal(m.geometry.index,m.original);assert.equal(m.geometry.attributes.position,m.originalPosition);assert.equal(m.geometry.attributes.normal,m.originalNormal);}
slot.setEquipped(true);for(const m of slot.masks)assert.equal(m.geometry.index,m.masked);assert(maxExtent<1.4,'Shoes must stay on feet, not explode');
assert(seamMax<1e-6,`Ankle seam separated: ${seamMax}`);
const report={seamMaxMeters:seamMax,samples,clips,minY,maxExtent,sharedSourcePair:true,normalizedWeights:true,pauseNoDrift:true,unequipRestoresPoseAndGeometry:true,originalCharacterAssetUnmodified:true};
fs.writeFileSync(new URL('tests/office-feet-validation.json',root),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
