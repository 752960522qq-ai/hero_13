"""Exercise outfit switches at fixed poses across all footwear variants."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'qa/ankle-alignment';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':700,'height':600});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def instrument(route):
        response=route.fetch();source=response.text().replace('requestAnimationFrame(frame);','window.__step=frame;').replace('window.xiaqingTest={model,actor,actions,mixer,select}','window.xiaqingTest={model,actor,actions,mixer,select,camera,orbit,renderer}')
        route.fulfill(response=response,body=source)
    page.route('**/app.js?*',instrument);page.goto('http://127.0.0.1:8765')
    page.wait_for_function('window.xiaqingOutfit?.enabled && window.xiaqingFootwear?.enabled',timeout=90000)
    page.evaluate("document.getElementById('pause').click();window.xiaqingCloth.cloth.parent.visible=false;for(const e of document.body.children)if(e.id!=='stage')e.style.display='none'")
    print('Models loaded',flush=True);results=[]
    for variant in ['black','stud','beige','navy','sandal','red','none']:
        page.evaluate('''async key=>{const select=document.querySelector('[aria-label="更换鞋子"]');select.value=key;await select.onchange();}''',variant)
        for pose in ['Idle','Walk','Run']:
            for fraction in [0,.35,.7]:
                result=page.evaluate('''({pose,fraction,variant})=>{
                    const t=window.xiaqingTest,f=window.xiaqingFootwear,o=window.xiaqingOutfit,m=window.xiaqingBodyModules;
                    if(variant==='none'?f.enabled:(!f.enabled||f.activeVariant!==variant))throw Error('Shoe selection failed');
                    f.beforeAnimation();t.mixer.stopAllAction();const action=t.actions[pose];action.reset().play();t.mixer.setTime(action.getClip().duration*fraction);f.afterAnimation();m.update();t.model.updateMatrixWorld(true);
                    const skin=t.model.getObjectByName('pl2020_Skin_Mat');
                    const meshes=f.enabled?f.variantGroups.get(f.activeVariant).group.children.filter(x=>x.isSkinnedMesh):[skin];
                    function snapshot(){t.model.updateMatrixWorld(true);let result=[],v=t.camera.position.clone();for(const mesh of meshes)for(let i=0;i<mesh.geometry.attributes.position.count;i+=31){v.fromBufferAttribute(mesh.geometry.attributes.position,i);mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);result.push(...v.toArray());}return result;}
                    o.setEquipped(false);const before=snapshot();o.setEquipped(true);const expected=skin.geometry.index.count;
                    for(let k=0;k<5;k++){o.setEquipped(false);o.setEquipped(true);}const after=snapshot();
                    const maxDelta=Math.max(...after.map((x,i)=>Math.abs(x-before[i])));
                    if(maxDelta>1e-8||!after.every(Number.isFinite)||skin.geometry.index.count!==expected)throw Error('Outfit switch changed foot geometry');
                    for(const mesh of o.group.children.filter(x=>x.name.startsWith('Suit_calf'))){let v=t.camera.position.clone();for(let i=0;i<mesh.geometry.attributes.position.count;i++){v.fromBufferAttribute(mesh.geometry.attributes.position,i);mesh.applyBoneTransform(i,v);if(!v.toArray().every(Number.isFinite))throw Error('Invalid calf deformation');}}
                    return {variant,pose,fraction,maxFootDisplacement:maxDelta,maskRestored:true};
                }''',dict(pose=pose,fraction=fraction,variant=variant))
                results.append(result)
                if variant=='black' and fraction==.35:
                    data=page.evaluate('''()=>{let t=window.xiaqingTest,out=[];t.model.updateMatrixWorld(true);t.model.traverse(o=>{if(!o.isMesh||!(/calf_|OfficeHeel|OfficeFootSkin/.test(o.name)))return;for(let a=o;a;a=a.parent)if(!a.visible)return;let g=o.geometry;if(!g.index?.count)return;let ids=[...new Set(g.index.array)],map=new Map(ids.map((id,i)=>[id,i])),v=t.camera.position.clone(),positions=[],bindHeight=[];for(let i of ids){bindHeight.push(g.attributes.position.getY(i));v.fromBufferAttribute(g.attributes.position,i);if(o.isSkinnedMesh)o.applyBoneTransform(i,v);v.applyMatrix4(o.matrixWorld);positions.push(...v.toArray());}out.push({name:o.name,positions,bindHeight,indices:Array.from(g.index.array,i=>map.get(i)),color:o.name.startsWith('Suit_')?[.2,.35,.6]:o.name.startsWith('OfficeHeel')?[.03,.03,.03]:[.65,.43,.32]});});return out;}''')
                    (OUT/f'{pose}_posed.json').write_text(json.dumps(data))
                    camera=page.evaluate('''()=>{let t=window.xiaqingTest,p=t.camera.position.clone();t.model.getObjectByName('l_leg_ankle').getWorldPosition(p);t.orbit.minDistance=.01;t.orbit.enableDamping=false;t.orbit.target.copy(p).add({x:0,y:.04,z:0});t.camera.position.copy(p).add({x:.2,y:.16,z:.36});t.orbit.update();t.renderer.render(t.model.parent.parent,t.camera);return {position:t.camera.position.toArray(),target:t.orbit.target.toArray(),fov:t.camera.fov};}''')
                    (OUT/f'{pose}_camera.json').write_text(json.dumps(camera));page.screenshot(path=str(OUT/f'{pose}_after.png'))
        print('Passed',variant,flush=True)
    assert not errors,errors
    (OUT/'runtime-checks.json').write_text(json.dumps({'cases':results,'caseCount':len(results),'togglesPerCase':10,'browserErrors':errors},indent=2))
    browser.close();print('All',len(results),'cases passed',flush=True)
