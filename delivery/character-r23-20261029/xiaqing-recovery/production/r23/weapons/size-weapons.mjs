import fs from 'node:fs/promises';
import path from 'node:path';
import * as THREE from 'three';
import {GLTFLoader} from '/workspace/recovered-xiaqing-site/dist/vendor/GLTFLoader.js';
const root='/workspace/recovered-xiaqing-site/dist';
const file=path.join(root,'assets/weapons.json');
const targets={type56:.870,hanyang88:.950,qbz95:.750};
globalThis.self=globalThis;
const loader=new GLTFLoader();
loader.register(parser=>{parser.loadTexture=()=>Promise.resolve(new THREE.Texture());return {name:'size-without-image-decoding'};});
const manifest=JSON.parse(await fs.readFile(file,'utf8'));
const report={units:'metres',measurement:'Exact decoded scene vertices projected onto weapon +Z (barrel axis), including all magazine parts',weapons:{}};
for(const [id,target]of Object.entries(targets)){
 const definition=manifest[id],asset=path.join(root,definition.url.replace(/^\.\//,'').split('?')[0]);
 const b=await fs.readFile(asset),result=await loader.parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
 result.scene.updateMatrixWorld(true);
 let min=Infinity,max=-Infinity,count=0;
 result.scene.traverse(o=>{if(o.isMesh){const a=o.geometry.attributes.position,v=new THREE.Vector3();for(let i=0;i<a.count;i++){v.fromBufferAttribute(a,i).applyMatrix4(o.matrixWorld);min=Math.min(min,v.z);max=Math.max(max,v.z);count++;}}});
 const native=max-min,scale=target/native;
 definition.displayScale=scale;definition.displayLength=target;definition.visualLength=native;
 definition.url=definition.url.split('?')[0]+'?v=r23';
 definition.dimensionPolicy='Uniform displayScale; local grip/support/stock/muzzle coordinates remain asset-space and receive the same scale at mount.';
 report.weapons[id]={asset:path.basename(asset),vertexCount:count,nativeBarrelBounds:[min,max],nativeLength:native,uniformScale:scale,targetLength:target,measuredDisplayLength:native*scale,errorMetres:native*scale-target,previousScale:.92};
}
await fs.writeFile(file,JSON.stringify(manifest,null,2)+'\n');
await fs.writeFile('/workspace/xiaqing-r23/weapons/size-report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
