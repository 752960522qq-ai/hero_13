from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'qa/junction-closeups';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']);page=b.new_page(viewport={'width':600,'height':600});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def instrument(route):
  response=route.fetch();route.fulfill(response=response,body=response.text().replace('window.xiaqingTest={model,actor,actions,mixer,select}', 'window.xiaqingTest={model,actor,actions,mixer,select,camera,orbit,renderer}'))
 page.route('**/app.js?*',instrument);page.goto('http://127.0.0.1:8765');page.wait_for_function('window.xiaqingOutfit?.enabled && window.xiaqingFootwear?.enabled',timeout=90000);page.locator('#pause').click()
 page.evaluate('''()=>{window.xiaqingCloth.cloth.parent.visible=false;window.xiaqingCloth.sim.paused=true;for(const e of document.body.children)if(e.id!=='stage')e.style.display='none';window.xiaqingTest.orbit.enableDamping=false;}''')
 views=[('neck_front','neck_1',[0,.02,.32]),('neck_back','neck_1',[0,.045,-.32]),('wrist_l','l_arm_wrist',[.19,.025,.25]),('wrist_r','r_arm_wrist',[-.19,.025,.25]),('ankle_l','l_leg_ankle',[.20,.07,.26]),('ankle_r','r_leg_ankle',[-.20,.07,.26])]
 for pose,t in [('Idle',0),('Run',.18)]:
  page.evaluate('''([pose,time])=>{const t=window.xiaqingTest;window.xiaqingFootwear.beforeAnimation();t.mixer.stopAllAction();t.actions[pose].reset().play();t.mixer.setTime(time);window.xiaqingFootwear.afterAnimation();window.xiaqingBodyModules.update();t.model.updateMatrixWorld(true);}''',[pose,t])
  snapshot=page.evaluate("""()=>{const t=window.xiaqingTest,out=[];t.model.updateMatrixWorld(true);t.model.traverse(o=>{if(!o.isMesh)return;let a=o;while(a){if(!a.visible)return;a=a.parent;}const g=o.geometry;if(!g.index?.count)return;const positions=[],v=t.camera.position.clone();for(let i=0;i<g.attributes.position.count;i++){v.fromBufferAttribute(g.attributes.position,i);if(o.isSkinnedMesh)o.applyBoneTransform(i,v);v.applyMatrix4(o.matrixWorld);positions.push(...v.toArray());}out.push({name:o.name,positions,indices:Array.from(g.index.array),color:o.name.startsWith('Suit_')?[.65,.7,.8]:[.65,.43,.32]});});return out;}""")
  (OUT/f'{pose}_geometry.json').write_text(json.dumps(snapshot,separators=(',',':')))
  for label,bone,delta in views:
   page.evaluate('''([bone,delta])=>{const t=window.xiaqingTest,p=t.orbit.target.clone();t.model.getObjectByName(bone).getWorldPosition(p);t.orbit.minDistance=.01;t.orbit.target.copy(p);t.camera.position.copy(p);t.camera.position.x+=delta[0];t.camera.position.y+=delta[1];t.camera.position.z+=delta[2];t.orbit.update();}''',[bone,delta]);page.wait_for_timeout(150);page.screenshot(path=str(OUT/f'{pose}_{label}.png'))
   (OUT/f'{pose}_{label}_camera.json').write_text(json.dumps(page.evaluate('()=>({position:window.xiaqingTest.camera.position.toArray(),target:window.xiaqingTest.orbit.target.toArray(),fov:window.xiaqingTest.camera.fov})')))
 (OUT/'capture.json').write_text(json.dumps({'poses':['Idle 0s','Run .18s'],'views':len(views),'errors':errors},indent=2));print('Captured 12 closeups',errors);b.close()
