import assert from 'node:assert/strict';
import {ClothPhysics} from '../dist/cloth-physics.mjs';
const c=new ClothPhysics();const pins=[...c.p.slice(0,3),...c.p.slice(c.cols*3,c.cols*3+3)];
for(let i=0;i<240;i++)c.update(1/60);
assert.deepEqual([...c.p.slice(0,3),...c.p.slice(c.cols*3,c.cols*3+3)],pins,'Pinned corners remain fixed');
assert(c.p.some((v,i)=>i%3===2&&Math.abs(v-c.rest[i])>.03),'Wind deflects the cloth');
const allFinite=()=>assert(c.p.every(Number.isFinite),'All particles remain finite');allFinite();
const sphere=c.spheres[0];for(let i=0;i<c.count;i++)assert(Math.hypot(c.p[i*3]-sphere.x,c.p[i*3+1]-sphere.y,c.p[i*3+2]-sphere.z)>=sphere.r+.0119,'Sphere contact stays outside surface');
c.startGrab(250,[1.6,1.4,.7]);for(let i=0;i<30;i++)c.update(1/60);assert.deepEqual([...c.p.slice(750,753)],[...new Float32Array([1.6,1.4,.7])]);c.endGrab();
c.release();c.wind=0;for(let i=0;i<300;i++)c.update(1/60);allFinite();for(let i=0;i<c.count;i++)assert(c.p[i*3+1]>=.0179,'Floor prevents penetration');assert(c.p[1]<1.5,'Released anchors fall');
c.reset();assert.deepEqual(c.p,c.rest);c.paused=true;const previous=c.p.slice();c.update(.05);assert.deepEqual(c.p,previous,'Pause freezes cloth');
const collisions=new ClothPhysics();collisions.spheres=[];collisions.capsules=[{a:[1.35,.8,.22],b:[1.35,1.5,.22],r:.12}];collisions.update(1/60);for(let i=0;i<collisions.count;i++){const k=i*3,y=Math.max(.8,Math.min(1.5,collisions.p[k+1]));assert(Math.hypot(collisions.p[k]-1.35,collisions.p[k+1]-y,collisions.p[k+2]-.22)>=.1319,'Capsule collision resolves penetration');}
console.log('PASS: wind, pins, sphere/capsule collisions, drag, release, floor, reset, pause.');
