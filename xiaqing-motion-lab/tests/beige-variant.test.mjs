import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {GLTFLoader} from '../dist/vendor/GLTFLoader.js';
import {FootwearSlot} from '../dist/footwear.js';
const root=new URL('../',import.meta.url);
async function load(path){const data=fs.readFileSync(new URL(path,root));const n=data.readUInt32LE(12),j=JSON.parse(data.subarray(20,20+n));j.materials=(j.materials||[]).map(()=>({}));j.images=[];j.textures=[];let text=Buffer.from(JSON.stringify(j));text=Buffer.concat([text,Buffer.alloc((4-text.length%4)%4,32)]);const bin=data.subarray(20+n),out=Buffer.alloc(20+text.length+bin.length);data.copy(out,0,0,12);out.writeUInt32LE(out.length,8);out.writeUInt32LE(text.length,12);out.writeUInt32LE(0x4e4f534a,16);text.copy(out,20);bin.copy(out,20+text.length);return new GLTFLoader().parseAsync(out.buffer.slice(out.byteOffset,out.byteOffset+out.length),'');}
const model=await load('dist/assets/xiaqing_native_animated.glb');
const black=await load('dist/assets/wardrobe/office_feet_rigged.glb'),blackCfg=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/office_feet.json',root)));
const beige=await load('dist/assets/wardrobe/beige_feet_rigged.glb'),beigeCfg=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/beige_feet.json',root)));
const navy=await load('dist/assets/wardrobe/navy_mary_jane_feet_rigged.glb'),navyCfg=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/navy_mary_jane_feet.json',root)));
const sandal=await load('dist/assets/wardrobe/sandal_feet_rigged.glb'),sandalCfg=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/sandal_feet.json',root)));
const red=await load('dist/assets/wardrobe/red_sneakers_feet_rigged.glb'),redCfg=JSON.parse(fs.readFileSync(new URL('dist/assets/wardrobe/red_sneakers_feet.json',root)));
assert(Math.abs(redCfg.ankleDegrees)<1e-8);assert(Math.abs(redCfg.ballDegrees)<1e-8);assert(Math.abs(redCfg.rootLift)<1e-8);assert(red.scene.children.some(m=>m.name==='RedSneakers_L'));assert(red.scene.children.some(m=>m.name==='RedSneakersSkin_L'));
const slot=new FootwearSlot(model.scene);slot.install(black,blackCfg,'black');slot.install(beige,beigeCfg,'beige');slot.install(navy,navyCfg,'navy');slot.install(sandal,sandalCfg,'sandal');slot.install(red,redCfg,'red');
assert.equal(slot.meshes.length,20);slot.selectVariant('black');slot.setEquipped(true);
const body=(()=>{let found;model.scene.traverse(o=>{if(o.isSkinnedMesh&&!slot.meshes.includes(o)&&o.geometry.attributes.position.count===beigeCfg.mask.positionCount)found=o;});return found;})();assert(body);
const mixer=new THREE.AnimationMixer(model.scene),point=new THREE.Vector3();let samples=0,seamMax=0;
for(const key of ['black','beige','navy','sandal','red']){
 slot.selectVariant(key);slot.setEquipped(true);
 const active=slot.variantGroups.get(key).group;assert(active.visible);
 for(const [otherKey,other] of slot.variantGroups)if(otherKey!==key)assert(!other.group.visible);
 const cfg=slot.config;
 for(const clip of model.animations){const action=mixer.clipAction(clip);action.reset().play();for(let k=0;k<12;k++){slot.beforeAnimation();mixer.setTime(clip.duration*k/12);slot.afterAnimation();model.scene.updateMatrixWorld(true);body.skeleton.update();for(const mesh of active.children){mesh.skeleton.update();const w=mesh.geometry.attributes.skinWeight;for(let i=0;i<w.count;i++)assert(Math.abs(w.getX(i)+w.getY(i)+w.getZ(i)+w.getW(i)-1)<1e-6);}
 for(const seam of cfg.seams){const foot=active.children.find(m=>m.name===(key==='beige'?'BeigeFootSkin_':key==='navy'?'NavyMaryJaneSkin_':key==='sandal'?'SandalSkin_':key==='red'?'RedSneakersSkin_':'OfficeFootSkin_')+seam.side);for(let i=0;i<seam.nativeIndices.length;i++){const a=body.getVertexPosition(seam.nativeIndices[i],point.clone()).applyMatrix4(body.matrixWorld);const b=foot.getVertexPosition(seam.accessoryIndices[i],new THREE.Vector3()).applyMatrix4(foot.matrixWorld);seamMax=Math.max(seamMax,a.distanceTo(b));}}
 samples++;}}
 mixer.stopAllAction();
}
slot.setEquipped(false);assert(!slot.variantGroups.get('black').group.visible&&!slot.variantGroups.get('beige').group.visible&&!slot.variantGroups.get('navy').group.visible&&!slot.variantGroups.get('sandal').group.visible&&!slot.variantGroups.get('red').group.visible);assert.equal(slot.masks[0].geometry.index,slot.masks[0].original);
assert(seamMax<1e-6,`ankle seam gap: ${seamMax}`);console.log(JSON.stringify({samples,seamMax,allFiveShoeVariantsCanSwitch:true,bothHiddenWhenUnequipped:true,skinWeightsNormalized:true}));
