import * as THREE from 'three';
import {GLTFLoader} from './vendor/GLTFLoader.js';
import {OrbitControls} from './vendor/OrbitControls.js';
const $=id=>document.getElementById(id),stage=$('stage');
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.8));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;stage.append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#f0f0ed');scene.fog=new THREE.Fog('#f0f0ed',15,40);
scene.add(new THREE.HemisphereLight(0xe9f2ff,0x777469,2.4));
const key=new THREE.DirectionalLight(0xfff2de,3.4);key.position.set(3,6,4);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-4,right:4,top:4,bottom:-4});key.shadow.normalBias=.018;scene.add(key);
const rim=new THREE.DirectionalLight(0xd6e8ff,2.3);rim.position.set(-3,3,-2);scene.add(rim);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(100,100),new THREE.MeshStandardMaterial({color:0xe3e6df,roughness:.94}));floor.rotation.x=-Math.PI/2;floor.position.y=-.003;floor.receiveShadow=true;scene.add(floor);
const grid=new THREE.GridHelper(12,24,0xcbd2ca,0xdce1d9);grid.material.transparent=true;grid.material.opacity=.3;grid.position.y=-.001;scene.add(grid);
const camera=new THREE.PerspectiveCamera(34,1,.01,100);const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.enablePan=false;orbit.maxPolarAngle=Math.PI*.495;orbit.minDistance=.5;orbit.maxDistance=12;
let configs={double_stars:{label:'双星',url:'./assets/double_stars.glb?v=1',ground:{}},superman:{label:'超人',url:'./assets/superman_animated.glb?v=1',ground:{}}};
const labels={Idle:'待机',Walk:'行走',Run:'跑步'};let model=null,mixer=null,helper=null,clips={},action=null,selected='Idle',current='double_stars',requested=current,paused=false,speed=1,serial=0,aborter=null,loading=false,failed=false,contextLost=false;
let center=new THREE.Vector3(0,1,0),height=2;
const manifest=fetch('./assets/characters.json?v=1',{credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('人物配置未找到');return r.json();}).then(data=>{for(const id of Object.keys(configs))if(data[id])configs[id]={...configs[id],...data[id]};}).catch(()=>{});
function setView(name='default'){const dir={front:[0,.07,1],side:[1,.07,0],back:[0,.07,-1],default:[.34,.13,1]}[name]||[.34,.13,1];orbit.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(...dir).normalize().multiplyScalar(height*2.1));orbit.update();}
setView();
function interfaceState(){
 for(const b of document.querySelectorAll('[data-character]')){const active=b.dataset.character===current&&!!model;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));b.setAttribute('aria-busy',String(loading&&b.dataset.character===requested));}
 for(const b of document.querySelectorAll('[data-action]')){b.disabled=!clips[b.dataset.action]||loading;b.classList.toggle('selected',b.dataset.action===selected);}
 $('play').disabled=!action;$('timeline').disabled=!action;$('skeleton').disabled=!model;$('play').textContent=paused?'▶':'Ⅱ';$('play').setAttribute('aria-label',paused?'播放动画':'暂停动画');
 $('viewLabel').textContent=configs[current].label+' / '+labels[selected];$('motionLabel').textContent=labels[selected];$('characterTitle').textContent=configs[current].label;
 $('status').textContent=contextLost?'图形显示中断':loading?'人物载入中':failed?'载入失败，可重试':paused?'动画已暂停':labels[selected]+' · 循环播放';
 $('loading').hidden=!loading&&!failed&&!contextLost;$('retry').hidden=!failed&&!contextLost;document.body.dataset.failed=String(failed||contextLost);
}
function chooseAction(name){if(!clips[name])return;const previous=action;selected=name;action=clips[name];if(action!==previous){action.reset().fadeIn(.18).play();previous?.fadeOut(.18);}if(model)model.position.y=configs[current].ground?.[name]??0;interfaceState();}
function dispose(root){const geos=new Set(),mats=new Set(),textures=new Set(),skeletons=new Set();root?.traverse(o=>{if(o.geometry)geos.add(o.geometry);if(o.skeleton)skeletons.add(o.skeleton);for(const mat of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){mats.add(mat);for(const t of Object.values(mat))if(t?.isTexture)textures.add(t);}});for(const t of textures){const image=t.source?.data;t.dispose();image?.close?.();}for(const mat of mats)mat.dispose();for(const g of geos)g.dispose();for(const s of skeletons)s.dispose();}
function removeHelper(h){if(!h)return;scene.remove(h);h.geometry.dispose();h.material.dispose();}
async function loadCharacter(id){
 if(!configs[id])return;requested=id;const token=++serial;aborter?.abort();const ctrl=new AbortController();aborter=ctrl;loading=true;failed=false;$('loadingTitle').textContent='正在载入'+configs[id].label;$('loadingText').textContent='下载模型与动作…';interfaceState();let candidate=null;
 try{
  await manifest;if(token!==serial)return;const config=configs[id],response=await fetch(config.url,{signal:ctrl.signal,credentials:'same-origin'});if(!response.ok)throw Error('模型下载失败（'+response.status+'）');if((response.headers.get('content-type')||'').includes('text/html'))throw Error('服务器返回的内容不是人物模型');
  const chunks=[];let loaded=0;const total=Number(response.headers.get('content-length'))||0;const reader=response.body?.getReader();
  if(reader){while(true){const {value,done}=await reader.read();if(done)break;chunks.push(value);loaded+=value.length;if(token===serial)$('loadingText').textContent=total?'模型与动作 · '+Math.min(100,Math.round(loaded/total*100))+'%':'已载入 '+(loaded/1048576).toFixed(1)+' MB';}}else{const bytes=new Uint8Array(await response.arrayBuffer());chunks.push(bytes);loaded=bytes.length;}
  const bytes=new Uint8Array(loaded);let off=0;for(const c of chunks){bytes.set(c,off);off+=c.length;}if(loaded<20||new DataView(bytes.buffer).getUint32(0,true)!==0x46546c67||new DataView(bytes.buffer).getUint32(8,true)!==loaded)throw Error('模型数据不完整，请重试');
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer,new URL('.',new URL(config.url,location.href)).href);candidate=gltf.scene;if(token!==serial){dispose(candidate);return;}
  const newMixer=new THREE.AnimationMixer(candidate),nextClips={};for(const clip of gltf.animations)if(labels[clip.name])nextClips[clip.name]=newMixer.clipAction(clip);for(const name of Object.keys(labels))if(!nextClips[name])throw Error('缺少'+labels[name]+'动作');
  let skins=0;candidate.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false;}if(o.isSkinnedMesh)skins++;});if(!skins)throw Error('模型缺少骨骼蒙皮');
  const nextAction=nextClips[selected]||nextClips.Idle;nextAction.play();newMixer.update(0);candidate.position.y=config.ground?.[selected]??0;candidate.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(candidate);if(!Number.isFinite(box.min.y)||box.isEmpty())throw Error('人物模型范围异常');const nextCenter=box.getCenter(new THREE.Vector3()),nextHeight=box.max.y-box.min.y;
  if(nextHeight<.5||nextHeight>5)throw Error('人物模型尺寸异常');const nextHelper=new THREE.SkeletonHelper(candidate);nextHelper.visible=helper?.visible||false;nextHelper.material.depthTest=false;nextHelper.material.transparent=true;nextHelper.material.opacity=.65;
  if(model){mixer.stopAllAction();scene.remove(model);dispose(model);removeHelper(helper);}model=candidate;candidate=null;mixer=newMixer;clips=nextClips;action=nextAction;helper=nextHelper;scene.add(model,helper);current=id;center.copy(nextCenter);height=nextHeight;setView();
  $('download').href=config.url;$('download').download=config.label+'_动作适配.glb';$('skeleton').setAttribute('aria-pressed',String(helper.visible));loading=false;failed=false;aborter=null;interfaceState();
 }catch(error){if(candidate)dispose(candidate);if(token!==serial||error.name==='AbortError')return;loading=false;failed=true;aborter=null;$('loadingTitle').textContent='人物暂时无法载入';$('loadingText').textContent=error.message;interfaceState();}
}
for(const b of document.querySelectorAll('[data-character]'))b.onclick=()=>loadCharacter(b.dataset.character);
for(const b of document.querySelectorAll('[data-action]'))b.onclick=()=>{paused=false;chooseAction(b.dataset.action);};
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>setView(b.dataset.view);
$('reset').onclick=()=>setView();$('retry').onclick=()=>contextLost?location.reload():loadCharacter(requested);
$('skeleton').onclick=()=>{if(helper){helper.visible=!helper.visible;$('skeleton').setAttribute('aria-pressed',String(helper.visible));}};
$('play').onclick=()=>{paused=!paused;interfaceState();};$('speed').oninput=e=>{speed=Number(e.target.value);$('speedLabel').textContent=speed.toFixed(2)+'×';};
$('timeline').oninput=e=>{if(!action)return;paused=true;action.time=Number(e.target.value)*action.getClip().duration;mixer.update(0);interfaceState();};
renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();contextLost=true;$('loadingTitle').textContent='图形显示已暂停';$('loadingText').textContent='请刷新页面恢复人物预览。';interfaceState();});renderer.domElement.addEventListener('webglcontextrestored',()=>location.reload());
const clock=new THREE.Clock();function frame(){requestAnimationFrame(frame);const dt=Math.min(clock.getDelta(),.05);if(contextLost)return;if(mixer&&!paused)mixer.update(dt*speed);if(action){const d=action.getClip().duration;$('timeline').value=d?action.time/d:0;$('timeLabel').textContent=action.time.toFixed(2)+' / '+d.toFixed(2)+' s';}orbit.update();renderer.render(scene,camera);}function resize(){const w=stage.clientWidth,h=stage.clientHeight;camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();renderer.setSize(w,h,false);}new ResizeObserver(resize).observe(stage);resize();frame();loadCharacter('double_stars');
window.heroTest={get model(){return model;},get mixer(){return mixer;},get clips(){return clips;},get loading(){return loading;},get failed(){return failed;},get current(){return current;},select:chooseAction,loadCharacter,scene,camera,renderer};
