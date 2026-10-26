import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {createClothTest} from './cloth-test.js';
import {createGameBridge} from './game/scene-bridge.mjs';

const $=id=>document.getElementById(id),stage=$('stage'),bridge=createGameBridge();
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;stage.prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#e9e7e1');scene.fog=new THREE.Fog('#e9e7e1',10,28);
const camera=new THREE.PerspectiveCamera(34,1,.01,100),orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.enablePan=false;orbit.maxPolarAngle=Math.PI*.49;orbit.minDistance=.45;orbit.maxDistance=8;
scene.add(new THREE.HemisphereLight(0xfffaf0,0x6c7b6c,2.5));
const key=new THREE.DirectionalLight(0xfff5e8,3.3);key.position.set(3,6,4);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-5,right:5,top:5,bottom:-5});key.shadow.bias=-.0003;scene.add(key);
const rim=new THREE.DirectionalLight(0xe0ebff,2);rim.position.set(-3,3,-3);scene.add(rim);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(100,100),new THREE.MeshStandardMaterial({color:0xe2e2db,roughness:.92}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;floor.receiveShadow=true;scene.add(floor);
const actor=new THREE.Group();scene.add(actor);const actions={},labels={Idle:'待机',Walk:'行走',Run:'跑步',Aim:'瞄准'},ground={Idle:.017692,Walk:.035238,Run:.046244,Aim:.006148};
let mode='character',model=null,mixer=null,skeleton=null,currentAction=null,selected='Idle',paused=false,playRate=1,moving=false,autoReturn=false;
const cloth=createClothTest({scene,camera,renderer,orbit,getModel:()=>model,mount:$('clothControls')});
function characterView(kind='default'){const offset=kind==='front'?new THREE.Vector3(0,1.05,3.7):kind==='side'?new THREE.Vector3(3.7,1.05,0):new THREE.Vector3(1.4,1.25,3.7);camera.position.copy(actor.position).add(offset);orbit.target.copy(actor.position).add(new THREE.Vector3(0,.86,0));orbit.minDistance=.45;orbit.update();}
function updateState(){$('state').textContent=mode==='cloth'?'拖动布面 · 移动人物碰撞':model?(paused?'动作已暂停':labels[selected]+'预览'):'载入角色中';}
function setMode(next){
 mode=next;document.body.dataset.mode=next;cloth.setActive(next==='cloth');$('characterPanel').hidden=next!=='character';$('clothPanel').hidden=next!=='cloth';
 for(const b of document.querySelectorAll('button[data-mode]'))b.setAttribute('aria-selected',String(b.dataset.mode===next));
 $('loading').hidden=next==='cloth'||!!model;if(next==='cloth'){camera.position.set(3.0,1.85,4.8);orbit.target.set(.66,1.0,.12);orbit.minDistance=.4;orbit.update();}else characterView();updateState();
}
function select(name,manual=true){
 if(!actions[name]||(name!=='Idle'&&!bridge.allows(name)))return;if(model)model.position.y=ground[name]??ground.Idle;if(manual){selected=name;autoReturn=false;}
 if(currentAction!==actions[name]){const prev=currentAction;currentAction=actions[name];currentAction.reset().fadeIn(.22).play();if(prev)prev.fadeOut(.22);}
 for(const b of document.querySelectorAll('[data-action]'))b.classList.toggle('selected',b.dataset.action===name);$('motionLabel').textContent=labels[name];updateState();
}
bridge.onAction(name=>select(name));
new GLTFLoader().load('./assets/vest_xiaqing.glb?v=wardrobe-cloth-r7-360d7aedba7f',gltf=>{
 model=gltf.scene;model.name='夏晴';model.position.y=ground.Idle;model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}});actor.add(model);mixer=new THREE.AnimationMixer(model);for(const clip of gltf.animations)actions[clip.name]=mixer.clipAction(clip);
 skeleton=new THREE.SkeletonHelper(model);skeleton.material.depthTest=false;skeleton.material.transparent=true;skeleton.material.opacity=.7;skeleton.visible=false;scene.add(skeleton);
 for(const b of document.querySelectorAll('[data-action],#pause,#skeleton'))b.disabled=false;select('Idle');$('loading').hidden=true;updateState();
},e=>{if(e.total){const p=Math.round(e.loaded/e.total*100);$('loadProgress').value=p;$('loadingText').textContent='背心套装与动作 · '+p+'%';}},()=>{$('loadingTitle').textContent='角色未能载入';$('loadingText').textContent='请检查网络后重试';$('retry').hidden=false;});
$('retry').onclick=()=>location.reload();for(const b of document.querySelectorAll('button[data-mode]'))b.onclick=()=>setMode(b.dataset.mode);for(const b of document.querySelectorAll('[data-action]'))b.onclick=()=>{paused=false;$('pause').textContent='暂停动作';select(b.dataset.action);};
$('speed').oninput=e=>{playRate=Number(e.target.value);$('speedValue').value=playRate.toFixed(1)+'×';};$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'继续动作':'暂停动作';updateState();};
$('skeleton').onclick=()=>{if(!skeleton)return;skeleton.visible=!skeleton.visible;$('skeleton').setAttribute('aria-pressed',String(skeleton.visible));};$('front').onclick=()=>{if(mode==='cloth')cloth.focus();else characterView('front');};$('sideview').onclick=()=>{if(mode==='cloth'){camera.position.set(4.2,1.6,.2);orbit.target.set(.8,1,.2);orbit.update();}else characterView('side');};$('reset').onclick=()=>{actor.position.set(0,0,0);actor.rotation.y=0;setMode(mode);};
const input=new THREE.Vector2(),keys=new Set(),joy=$('joystick'),stick=$('stick');let pointer=null;
function joystick(e){const r=joy.getBoundingClientRect(),max=r.width*.33;input.set((e.clientX-r.left-r.width/2)/max,(e.clientY-r.top-r.height/2)/max);if(input.length()>1)input.normalize();stick.style.transform=`translate(${input.x*max}px,${input.y*max}px)`;}
joy.onpointerdown=e=>{e.preventDefault();pointer=e.pointerId;joy.setPointerCapture(pointer);joystick(e);};joy.onpointermove=e=>{if(e.pointerId===pointer)joystick(e);};function release(){pointer=null;input.set(0,0);stick.style.transform='';}joy.onpointerup=release;joy.onpointercancel=release;window.addEventListener('blur',()=>{keys.clear();release();});
const moveKeys=['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'];window.addEventListener('keydown',e=>{if(/INPUT|TEXTAREA|SELECT|BUTTON/.test(e.target.tagName))return;if(moveKeys.includes(e.code)){e.preventDefault();keys.add(e.code);}});window.addEventListener('keyup',e=>keys.delete(e.code));
const clock=new THREE.Clock(),motion=new THREE.Vector2(),forward=new THREE.Vector3(),right=new THREE.Vector3(),dir=new THREE.Vector3();
function frame(){
 requestAnimationFrame(frame);const dt=Math.min(clock.getDelta(),.05),worldDt=dt*(bridge.enabled?bridge.state.timeScale:1);motion.copy(input);if(keys.size){motion.set((keys.has('KeyD')||keys.has('ArrowRight')?1:0)-(keys.has('KeyA')||keys.has('ArrowLeft')?1:0),(keys.has('KeyS')||keys.has('ArrowDown')?1:0)-(keys.has('KeyW')||keys.has('ArrowUp')?1:0));if(motion.length()>1)motion.normalize();}
 const active=motion.length()>.12&&(!bridge.enabled||!bridge.state.blocked);
 if(model&&active&&!paused){
  if(!moving&&(selected==='Idle'||selected==='Aim'))autoReturn=true;const gait=selected==='Run'&&bridge.allows('Run')?'Run':'Walk';select(gait,false);camera.getWorldDirection(forward);forward.y=0;forward.normalize();right.crossVectors(forward,new THREE.Vector3(0,1,0)).normalize();dir.copy(forward).multiplyScalar(-motion.y).addScaledVector(right,motion.x).normalize();
  const yaw=Math.atan2(dir.x,dir.z),diff=Math.atan2(Math.sin(yaw-actor.rotation.y),Math.cos(yaw-actor.rotation.y));actor.rotation.y+=diff*Math.min(1,worldDt*10);const delta=dir.multiplyScalar(worldDt*(gait==='Run'?2.2:1.05)*motion.length()*playRate*(bridge.enabled?bridge.state.moveMultiplier:1)),proposed=actor.position.clone().add(delta);
  if(proposed.length()<6){actor.position.copy(proposed);bridge.moved(gait==='Run'?'run':'walk',delta.length());if(mode==='character'){camera.position.add(delta);orbit.target.add(delta);}}
 }else if(moving&&autoReturn){select(selected,false);autoReturn=false;}
 moving=active;if(mixer&&!paused)mixer.update(worldDt*playRate);cloth.update(worldDt);bridge.update(dt);orbit.update();renderer.render(scene,camera);
}
function resize(){const w=stage.clientWidth,h=stage.clientHeight;camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();renderer.setSize(w,h,false);}new ResizeObserver(resize).observe(stage);resize();setMode('character');frame();
window.xiaqingTest={get model(){return model;},get mixer(){return mixer;},actor,actions,select,setMode,cloth,camera,orbit,renderer};
