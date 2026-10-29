import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {createClothTest} from './cloth-test.js';
import {createGameBridge} from './game/scene-bridge.mjs';
import {createWeaponViewer} from './weapon-viewer.js?v=r23';

const $=id=>document.getElementById(id),stage=$('stage'),bridge=createGameBridge();
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;stage.prepend(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#e9e7e1');scene.fog=new THREE.Fog('#e9e7e1',10,28);
const camera=new THREE.PerspectiveCamera(34,1,.01,100),orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.enablePan=false;orbit.maxPolarAngle=Math.PI*.49;orbit.minDistance=.45;orbit.maxDistance=8;
scene.add(new THREE.HemisphereLight(0xfffaf0,0x6c7b6c,2.5));
const key=new THREE.DirectionalLight(0xfff5e8,3.3);key.position.set(3,6,4);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-5,right:5,top:5,bottom:-5});key.shadow.bias=-.0003;scene.add(key);
const rim=new THREE.DirectionalLight(0xe0ebff,2);rim.position.set(-3,3,-3);scene.add(rim);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(100,100),new THREE.MeshStandardMaterial({color:0xe2e2db,roughness:.92}));floor.rotation.x=-Math.PI/2;floor.position.y=-.005;floor.receiveShadow=true;scene.add(floor);
const actor=new THREE.Group();scene.add(actor);const actions={},labels={Idle:'待机',Walk:'行走',Run:'跑步',Aim:'瞄准',PistolIdle:'手枪待机',RifleIdle:'持枪待机',RifleRun:'持枪跑步',Reload:'换弹',Jump:'跳跃',Fire:'步枪射击',ImportedMotion:'新动作'};
const outfits={
 "vest": {
  "title": "背心与牛仔短裤",
  "name": "背心套装",
  "ground": {
   "Jump": -0.041987, "Fire": -0.000257,
   "Idle": 0.021179,
   "Walk": 0.036664,
   "Run": 0.049744,
   "Aim": 0.009763,
   "PistolIdle": 0.020681,
   "RifleIdle": 0.034218,
   "RifleRun": 0.034809,
   "Reload": 0.034105
  },
  "url": "./assets/vest_xiaqing.glb?v=r21",
  "download": "夏晴_背心套装_R21.glb"
 },
 "green": {
  "title": "绿 T 与牛仔长裤",
  "name": "绿 T 套装",
  "ground": {
   "Jump": -0.0338, "Fire": 0.023319,
   "Idle": -0.006602,
   "Walk": 0.052521,
   "Run": 0.030449,
   "Aim": 1e-06,
   "PistolIdle": 0.006682,
   "RifleIdle": -0.001665,
   "RifleRun": 0.045266,
   "Reload": -0.001755
  },
  "url": "./assets/green_t_xiaqing.glb?v=r21",
  "download": "夏晴_绿 T 套装_R21.glb"
 },
 "floral": {
  "title": "碎花连衣裙",
  "name": "碎花裙套装",
  "ground": {
   "Jump": -0.078013,
   "Fire": 0.0,
   "Idle": 0.012601,
   "Walk": 0.046717,
   "Run": 0.071921,
   "Aim": 0.0,
   "ImportedMotion": 0.0,
   "PistolIdle": 0.0,
   "RifleIdle": 0.0,
   "RifleRun": 0.068213,
   "Reload": 0.0
  },
  "url": "./assets/floral_dress_xiaqing.glb?v=r22",
  "download": "夏晴_碎花裙套装_R22.glb"
 },
 "school": {
  "title": "校服套装",
  "name": "校服套装",
  "ground": {
   "Jump": -0.077527,
   "Fire": 0.0,
   "Idle": 0.008116,
   "Walk": 0.027625,
   "Run": 0.050577,
   "Aim": 0.0,
   "PistolIdle": 0.0,
   "RifleIdle": 0.0,
   "RifleRun": 0.045161,
   "Reload": 0.0
  },
  "url": "./assets/school_uniform_xiaqing.glb?v=r23",
  "download": "夏晴_校服套装_R23.glb"
 }
};
let currentOutfit='vest',requestedOutfit='vest',loadSerial=0,loading=false,loadFailed=false,loadController=null,lastLoadError=null,contextLost=false,lastContextError=null;
let mode='character',model=null,mixer=null,skeleton=null,currentAction=null,selected='Idle',paused=false,playRate=1,moving=false,autoReturn=false;
const weapons=createWeaponViewer({onStatus:state=>{$('weaponSelect').value=state.selected;$('weaponSelect').disabled=!model;$('weaponSelect').setAttribute('aria-busy',String(state.loading));$('weaponStatus').textContent=state.text;$('weaponStatus').title=state.error||'';}});
const cloth=createClothTest({scene,camera,renderer,orbit,getModel:()=>model,mount:$('clothControls')});
function characterView(kind='default'){const offset=kind==='front'?new THREE.Vector3(0,1.05,3.7):kind==='side'?new THREE.Vector3(3.7,1.05,0):new THREE.Vector3(1.4,1.25,3.7);camera.position.copy(actor.position).add(offset);orbit.target.copy(actor.position).add(new THREE.Vector3(0,.86,0));orbit.minDistance=.45;orbit.update();}
function updateState(){const active=currentAction?.getClip().name||selected;$('state').textContent=contextLost?'图形显示已暂停，请稍候恢复或刷新页面':mode==='cloth'?'拖动布面 · 移动人物碰撞':loading?'载入'+outfits[requestedOutfit].name+'中':loadFailed?outfits[requestedOutfit].name+'载入失败':model?(paused?'动作已暂停':(labels[active]||active)+'预览'):'载入角色中';}
function syncLoadingVisibility(){
 if(contextLost){$('loadingTitle').textContent='图形显示已暂停';$('loadingText').textContent='正在尝试恢复显示，也可刷新页面重试。';$('retry').textContent='刷新页面';$('retry').hidden=false;}
 $('loading').hidden=!contextLost&&(mode==='cloth'||(!loading&&!loadFailed));
}
renderer.domElement.addEventListener('webglcontextlost',event=>{
 event.preventDefault();contextLost=true;lastContextError={code:'webgl-context-lost',outfit:loading?requestedOutfit:currentOutfit,message:'图形上下文已中断，显示已暂停。'};console.error('图形显示中断',lastContextError);syncLoadingVisibility();updateState();
});
renderer.domElement.addEventListener('webglcontextrestored',()=>{
 contextLost=false;$('retry').textContent='重新载入';$('retry').hidden=!loadFailed;
 if(loading){$('loadingTitle').textContent='正在载入'+outfits[requestedOutfit].name;$('loadingText').textContent=outfits[requestedOutfit].name+'与动作';$('retry').hidden=true;}
 else if(loadFailed){$('loadingTitle').textContent=outfits[requestedOutfit].name+'未能载入';$('loadingText').textContent=lastLoadError?.message||'请重新载入角色。';}
 syncLoadingVisibility();updateState();
});
function setMode(next){
 mode=next;document.body.dataset.mode=next;cloth.setActive(next==='cloth');$('characterPanel').hidden=next!=='character';$('clothPanel').hidden=next!=='cloth';
 for(const b of document.querySelectorAll('button[data-mode]'))b.setAttribute('aria-selected',String(b.dataset.mode===next));
 syncLoadingVisibility();if(next==='cloth'){camera.position.set(3.0,1.85,4.8);orbit.target.set(.66,1.0,.12);orbit.minDistance=.4;orbit.update();}else characterView();updateState();
}
function motionAllowed(name){const gameAction=name==='RifleRun'?'Run':['PistolIdle','RifleIdle','Reload','Fire'].includes(name)?'Aim':name;return !['Walk','Run','Aim'].includes(gameAction)||bridge.allows(gameAction);}
function updateActionButtons(){
 for(const b of document.querySelectorAll('[data-action]')){const name=b.dataset.action,available=!!actions[name];b.hidden=!['Idle','Walk','Run','Aim'].includes(name)&&!available;b.disabled=!available||!motionAllowed(name);b.classList.toggle('selected',currentAction===actions[name]);}
}
function select(name,manual=true){
 if(!actions[name]||!motionAllowed(name))return false;const ground=outfits[currentOutfit].ground;if(model)model.position.y=ground[name]??ground.Idle??0;if(manual){selected=name;autoReturn=false;if(['Aim','RifleIdle','RifleRun','Reload','Fire'].includes(name)&&weapons.selected==='none')weapons.setWeapon('type56');}
 if(currentAction!==actions[name]||(['Reload','Jump','Fire'].includes(name)&&manual)){const prev=currentAction;currentAction=actions[name];currentAction.reset().fadeIn(name==='Fire'?.04:.15).play();if(prev&&prev!==currentAction)prev.fadeOut(name==='Fire'?.04:.15);}
 updateActionButtons();$('motionLabel').textContent=labels[name]||name;updateState();return true;
}
bridge.onAction(name=>select(name));
function disposeModel(root){
 const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set(),images=new Set();
 const rememberImage=image=>{if(Array.isArray(image)){for(const item of image)rememberImage(item);}else if(image&&typeof image.close==='function')images.add(image);};
 root.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.skeleton)skeletons.add(o.skeleton);for(const material of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){materials.add(material);for(const value of Object.values(material))if(value?.isTexture){textures.add(value);rememberImage(value.source?.data??value.image);}}});
 for(const skeleton of skeletons)skeleton.dispose();for(const texture of textures)texture.dispose();for(const image of images){try{image.close();}catch(error){console.warn('角色图像资源释放未完成',error);}}for(const material of materials)material.dispose();for(const geometry of geometries)geometry.dispose();
}
function outfitState(){
 for(const b of document.querySelectorAll('[data-outfit]')){const active=b.dataset.outfit===currentOutfit&&!!model,pending=loading&&b.dataset.outfit===requestedOutfit;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));b.setAttribute('aria-busy',String(pending));b.querySelector('.current').textContent=pending?'载入中':active?'当前':'选择';}
}
async function loadCharacter(config,onProgress,signal){
 const loader=new GLTFLoader(),urls=config.parts?.length?config.parts:[config.url];let loaded=0,total=0;
 const buffers=await Promise.all(urls.map(async url=>{
  const response=await fetch(url,{signal,credentials:'same-origin'});
  if(!response.ok){const message=response.status===404?'模型文件未找到，请刷新页面重试。':[401,403].includes(response.status)?'无法读取模型文件，请刷新登录后重试。':'模型下载失败，请稍后重试。';throw new Error(message+'（HTTP '+response.status+'）');}
  if((response.headers.get('content-type')||'').includes('text/html'))throw new Error('服务器返回了网页而非模型文件，请刷新页面重试。');
  total+=Number(response.headers.get('content-length'))||0;
  if(!response.body){const bytes=await response.arrayBuffer();loaded+=bytes.byteLength;onProgress({loaded,total});return bytes;}
  const reader=response.body.getReader(),chunks=[];let size=0;
  while(true){const next=await reader.read();if(next.done)break;chunks.push(next.value);size+=next.value.byteLength;loaded+=next.value.byteLength;onProgress({loaded,total});}
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes.buffer;
 }));
 const length=buffers.reduce((sum,bytes)=>sum+bytes.byteLength,0);let bytes;
 if(buffers.length===1)bytes=buffers[0];else{const joined=new Uint8Array(length);let offset=0;for(const part of buffers){joined.set(new Uint8Array(part),offset);offset+=part.byteLength;}bytes=joined.buffer;}
 if(signal.aborted)throw new DOMException('模型载入已取消','AbortError');
 if(bytes.byteLength<20)throw new Error('模型文件下载不完整，请重新载入。');
 const header=new DataView(bytes);if(header.getUint32(0,true)!==0x46546c67||header.getUint32(4,true)!==2)throw new Error('下载内容不是可用的GLB模型，请刷新页面重试。');
 if(header.getUint32(8,true)!==bytes.byteLength)throw new Error('模型文件长度不完整，请重新载入。');
 onProgress({loaded:length,total:length});
 let gltf;
 try{gltf=await loader.parseAsync(bytes,new URL('.',new URL(config.url,location.href)).href);}catch(error){throw new Error('模型解析失败：'+(error?.message||String(error)));}
 if(config.parts?.length)gltf.downloadUrl=URL.createObjectURL(new Blob([bytes],{type:'model/gltf-binary'}));
 return gltf;
}
function releaseCandidate(candidate){
 if(!candidate)return;candidate.mixer?.stopAllAction();if(candidate.mixer&&candidate.model)candidate.mixer.uncacheRoot(candidate.model);if(candidate.skeleton){candidate.skeleton.geometry.dispose();candidate.skeleton.material.dispose();}if(candidate.model)disposeModel(candidate.model);if(candidate.downloadUrl)URL.revokeObjectURL(candidate.downloadUrl);
}
function prepareCharacter(gltf,config,preferredName,phase,skeletonVisible){
 const candidate={model:gltf.scene,mixer:null,skeleton:null,actions:{},downloadUrl:gltf.downloadUrl};
 try{
  if(!candidate.model?.isObject3D)throw new Error('模型缺少角色场景。');
  let meshCount=0,skinCount=0;candidate.model.traverse(o=>{if(o.isMesh){meshCount++;o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}if(o.isSkinnedMesh&&o.skeleton?.bones.length)skinCount++;});
  if(!meshCount||!skinCount)throw new Error('模型缺少可用的蒙皮角色。');
  candidate.model.name='夏晴';candidate.weaponBinding=weapons.captureCharacter(candidate.model);candidate.mixer=new THREE.AnimationMixer(candidate.model);
  for(const clip of gltf.animations||[]){if(!clip.name||!Number.isFinite(clip.duration)||clip.duration<=0||!clip.tracks?.length)throw new Error('模型包含无效动作。');if(candidate.actions[clip.name])throw new Error('模型包含重名动作：'+clip.name);candidate.actions[clip.name]=candidate.mixer.clipAction(clip);if(['Reload','Jump','Fire'].includes(clip.name)){candidate.actions[clip.name].setLoop(THREE.LoopOnce,1);candidate.actions[clip.name].clampWhenFinished=true;}}
  if(!candidate.actions.Idle)throw new Error('模型缺少待机动作。');
  candidate.mixer.addEventListener('finished',event=>{if(mixer!==candidate.mixer||event.action!==currentAction||!['Reload','Jump','Fire'].includes(event.action.getClip().name))return;const next=weapons.selected!=='none'&&actions.RifleIdle&&motionAllowed('RifleIdle')?'RifleIdle':'Idle';select(next);});
  candidate.name=candidate.actions[preferredName]&&motionAllowed(preferredName)?preferredName:'Idle';candidate.action=candidate.actions[candidate.name];candidate.action.reset().setEffectiveWeight(1).play();candidate.action.time=candidate.name===preferredName?((phase%1+1)%1)*candidate.action.getClip().duration:0;
  candidate.model.position.y=config.ground[candidate.name]??config.ground.Idle??0;candidate.mixer.update(0);
  candidate.skeleton=new THREE.SkeletonHelper(candidate.model);candidate.skeleton.material.depthTest=false;candidate.skeleton.material.transparent=true;candidate.skeleton.material.opacity=.7;candidate.skeleton.visible=skeletonVisible;
  return candidate;
 }catch(error){releaseCandidate(candidate);throw error;}
}
async function loadOutfit(id){
 if(!outfits[id]||(loading&&requestedOutfit===id))return;
 const serial=++loadSerial;loadController?.abort();loadController=null;requestedOutfit=id;loadFailed=false;lastLoadError=null;
 if(model&&id===currentOutfit){loading=false;syncLoadingVisibility();outfitState();updateState();return;}
 const config=outfits[id],controller=new AbortController();loadController=controller;loading=true;$('retry').hidden=true;$('loadProgress').value=0;$('loadingTitle').textContent='正在载入'+config.name;$('loadingText').textContent=config.name+'与动作';syncLoadingVisibility();outfitState();updateState();
 let gltf,candidate,previous;
 try{
  gltf=await loadCharacter(config,e=>{if(serial===loadSerial&&e.total){const p=Math.min(100,Math.round(e.loaded/e.total*100));$('loadProgress').value=p;$('loadingText').textContent=config.name+'与动作 · '+p+'%';}},controller.signal);
  if(serial!==loadSerial){releaseCandidate({model:gltf.scene,downloadUrl:gltf.downloadUrl});return;}
  const oldModel=model,oldMixer=mixer,oldSkeleton=skeleton,oldAction=currentAction,activeName=oldAction?.getClip().name||selected,phase=oldAction?oldAction.time/oldAction.getClip().duration:0;
  const parsed=gltf;gltf=null;candidate=prepareCharacter(parsed,config,activeName,phase,!!oldSkeleton?.visible);
  previous={model:oldModel,mixer:oldMixer,skeleton:oldSkeleton,action:oldAction,outfit:currentOutfit,selected,autoReturn,actions:{...actions},title:$('outfitTitle').textContent,download:$('downloadModel').getAttribute('download'),href:$('downloadModel').href};
  // All decoding, validation and pose preparation complete before replacing the visible character.
  actor.add(candidate.model);scene.add(candidate.skeleton);
  for(const name of Object.keys(actions))delete actions[name];Object.assign(actions,candidate.actions);currentOutfit=id;model=candidate.model;mixer=candidate.mixer;skeleton=candidate.skeleton;currentAction=candidate.action;weapons.setCharacter(model,candidate.weaponBinding);
  if(!moving||!actions[selected]||!motionAllowed(selected))selected=candidate.name;
  if(oldModel)actor.remove(oldModel);if(oldSkeleton)scene.remove(oldSkeleton);
  $('pause').disabled=false;$('skeleton').disabled=false;$('skeleton').setAttribute('aria-pressed',String(skeleton.visible));updateActionButtons();$('motionLabel').textContent=labels[candidate.name]||candidate.name;
  $('outfitTitle').textContent=config.title;$('downloadModel').href=candidate.downloadUrl||config.url;$('downloadModel').download=config.download;
  loading=false;loadController=null;syncLoadingVisibility();outfitState();updateState();candidate=null;
  try{if(previous.href.startsWith('blob:'))URL.revokeObjectURL(previous.href);if(oldMixer){oldMixer.stopAllAction();oldMixer.uncacheRoot(oldModel);}if(oldSkeleton){oldSkeleton.geometry.dispose();oldSkeleton.material.dispose();}if(oldModel)disposeModel(oldModel);}catch(error){console.warn('旧角色资源释放未完成',error);}
 }catch(error){
  if(candidate){
   actor.remove(candidate.model);scene.remove(candidate.skeleton);
   if(previous&&model===candidate.model){
    model=previous.model;mixer=previous.mixer;skeleton=previous.skeleton;currentAction=previous.action;currentOutfit=previous.outfit;selected=previous.selected;autoReturn=previous.autoReturn;weapons.setCharacter(model);
    for(const name of Object.keys(actions))delete actions[name];Object.assign(actions,previous.actions);if(model)actor.add(model);if(skeleton)scene.add(skeleton);
    $('outfitTitle').textContent=previous.title;$('downloadModel').href=previous.href;$('downloadModel').setAttribute('download',previous.download||'');$('pause').disabled=!model;$('skeleton').disabled=!skeleton;$('skeleton').setAttribute('aria-pressed',String(!!skeleton?.visible));updateActionButtons();$('motionLabel').textContent=labels[currentAction?.getClip().name||selected]||selected;
   }
   releaseCandidate(candidate);
  }else if(gltf)releaseCandidate({model:gltf.scene,downloadUrl:gltf.downloadUrl});
  if(serial!==loadSerial||error?.name==='AbortError')return;
  loading=false;loadController=null;loadFailed=true;lastLoadError={outfit:id,message:error?.message||String(error)};console.error('角色载入失败',id,config.url,error);
  $('loadingTitle').textContent=config.name+'未能载入';$('loadingText').textContent=lastLoadError.message+(model?' 原套装仍可使用，可重试或选择原套装。':' 请刷新后重试。');$('retry').hidden=false;syncLoadingVisibility();outfitState();updateState();
 }
}
$('retry').onclick=()=>{if(contextLost){location.reload();return;}loadOutfit(requestedOutfit);};for(const b of document.querySelectorAll('[data-outfit]')){b.hidden=!outfits[b.dataset.outfit];b.onclick=()=>loadOutfit(b.dataset.outfit);}loadOutfit('vest');
for(const b of document.querySelectorAll('button[data-mode]'))b.onclick=()=>setMode(b.dataset.mode);for(const b of document.querySelectorAll('[data-action]'))b.onclick=()=>{paused=false;$('pause').textContent='暂停动作';select(b.dataset.action);};
$('weaponSelect').onchange=e=>{const id=e.target.value;weapons.setWeapon(id);if(id!=='none'&&actions.RifleIdle&&!['Aim','RifleIdle','RifleRun','Reload','Fire'].includes(currentAction?.getClip().name))select('RifleIdle');};
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
  if(!moving&&!['Walk','Run','RifleRun'].includes(selected))autoReturn=true;const rifleGait=weapons.selected!=='none'&&['Aim','RifleIdle','RifleRun','Reload','Fire'].includes(selected)&&actions.RifleRun&&motionAllowed('RifleRun'),gait=rifleGait?'RifleRun':selected==='Run'&&bridge.allows('Run')?'Run':'Walk';select(gait,false);camera.getWorldDirection(forward);forward.y=0;forward.normalize();right.crossVectors(forward,new THREE.Vector3(0,1,0)).normalize();dir.copy(forward).multiplyScalar(-motion.y).addScaledVector(right,motion.x).normalize();
  const yaw=Math.atan2(dir.x,dir.z),diff=Math.atan2(Math.sin(yaw-actor.rotation.y),Math.cos(yaw-actor.rotation.y));actor.rotation.y+=diff*Math.min(1,worldDt*10);const delta=dir.multiplyScalar(worldDt*(['Run','RifleRun'].includes(gait)?2.2:1.05)*motion.length()*playRate*(bridge.enabled?bridge.state.moveMultiplier:1)),proposed=actor.position.clone().add(delta);
  if(proposed.length()<6){actor.position.copy(proposed);bridge.moved(['Run','RifleRun'].includes(gait)?'run':'walk',delta.length());if(mode==='character'){camera.position.add(delta);orbit.target.add(delta);}}
 }else if(moving&&autoReturn){select(selected,false);autoReturn=false;}
 moving=active;weapons.beforeAnimation();if(mixer&&!paused)mixer.update(worldDt*playRate);weapons.update(currentAction?.getClip().name||selected,paused?0:worldDt*playRate,{time:currentAction?.time||0,duration:currentAction?.getClip().duration||1});cloth.update(worldDt);bridge.update(dt);orbit.update();renderer.render(scene,camera);
}
function resize(){const w=stage.clientWidth,h=stage.clientHeight;camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();renderer.setSize(w,h,false);}new ResizeObserver(resize).observe(stage);resize();setMode('character');frame();
window.xiaqingTest={get model(){return model;},get mixer(){return mixer;},actor,actions,select,setMode,loadOutfit,get outfit(){return currentOutfit;},get lastLoadError(){return contextLost?lastContextError:lastLoadError;},get lastContextError(){return lastContextError;},get contextLost(){return contextLost;},get loading(){return loading;},weapons,cloth,camera,orbit,renderer};
