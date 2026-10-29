import fs from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFLoader} from '/workspace/recovered-xiaqing-site/dist/vendor/GLTFLoader.js';
import {createWeaponViewer} from '/workspace/recovered-xiaqing-site/dist/weapon-viewer.js';
const root='/workspace/recovered-xiaqing-site/dist/';
globalThis.self=globalThis;globalThis.location={href:'https://test.local/index.html'};
const original=GLTFLoader.prototype.parseAsync;
GLTFLoader.prototype.parseAsync=function(b,p){this.register(parser=>{parser.loadTexture=()=>Promise.resolve(new THREE.Texture());return {name:'dimension-no-images'};});return original.call(this,b,p);};
globalThis.fetch=async url=>{const p=String(url).replace(/^\.\//,'').split('?')[0],b=await fs.readFile(root+p);return new Response(b,{headers:{'content-type':p.endsWith('.json')?'application/json':'model/gltf-binary'}});};
const target={type56:.870,hanyang88:.950,qbz95:.750},report=[];
for(const outfit of ['vest','green_t','floral_dress','school_uniform']){
 const b=await fs.readFile(root+'assets/'+outfit+'_xiaqing.glb'),g=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
 const scene=new THREE.Scene();scene.add(g.scene);const viewer=createWeaponViewer();viewer.setCharacter(g.scene);const mixer=new THREE.AnimationMixer(g.scene),clip=g.animations.find(c=>c.name==='Aim');const action=mixer.clipAction(clip).play();action.time=.5;mixer.update(0);
 for(const [id,expect]of Object.entries(target)){
  if(!await viewer.setWeapon(id))throw Error(viewer.lastError);viewer.update('Aim');scene.updateMatrixWorld(true);
  const axis=new THREE.Vector3(0,0,1).transformDirection(viewer.weapon.matrixWorld);let min=Infinity,max=-Infinity;
  viewer.weapon.traverse(o=>{if(o.isMesh){const pos=o.geometry.attributes.position,v=new THREE.Vector3();for(let k=0;k<pos.count;k++){v.fromBufferAttribute(pos,k).applyMatrix4(o.matrixWorld);const d=v.dot(axis);min=Math.min(min,d);max=Math.max(max,d);}}});
  const actual=max-min,error=Math.abs(actual-expect);if(error>1e-6)throw Error(outfit+' '+id+' bad dimension '+actual);
  report.push({outfit,weapon:id,expected:expect,mountedLength:actual,error,unit:'m'});
 }
 viewer.dispose();
}
await fs.writeFile('/workspace/xiaqing-r23/weapons/mounted-report.json',JSON.stringify(report,null,2)+'\n');console.log('Checked 12 mounted dimensions; maximum error',Math.max(...report.map(x=>x.error)));
