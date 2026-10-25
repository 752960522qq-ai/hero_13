"""Local browser checks for wardrobe replacement, visibility and posed previews."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'qa/shirt-trouser';OUT.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':900,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8765');page.wait_for_function('window.xiaqingOutfit?.enabled && window.xiaqingFootwear?.enabled',timeout=90000)
 page.locator('#pause').click();page.evaluate('window.xiaqingCloth.cloth.parent.visible=false;window.xiaqingCloth.sim.paused=true;document.querySelector("#clothPanel").style.display="none"');page.locator('#front').click()
 for name,time in [('Idle',0),('Walk',.3),('Run',.18)]:
  page.evaluate('''([name,time])=>{const t=window.xiaqingTest;window.xiaqingFootwear.beforeAnimation();t.mixer.stopAllAction();t.actions[name].reset().play();t.mixer.setTime(time);window.xiaqingFootwear.afterAnimation();window.xiaqingBodyModules.update();t.model.updateMatrixWorld(true);}''',[name,time]);page.wait_for_timeout(400);page.screenshot(path=str(OUT/f'{name}_front.png'))
  if name=='Idle':
   page.locator('#sideview').click();page.wait_for_timeout(400);page.screenshot(path=str(OUT/'Idle_side.png'));page.locator('#front').click()
 page.evaluate("window.xiaqingBodyModules.setVisible('foot_l',false)")
 results=[]
 for key in ['beige','navy','sandal','red','stud','black']:
  page.select_option('[aria-label="更换鞋子"]',key);page.wait_for_function('(key)=>window.xiaqingFootwear.activeVariant===key && !document.querySelector(\'[aria-label="更换鞋子"]\').disabled',arg=key,timeout=60000)
  result=page.evaluate('''()=>{const s=window.xiaqingFootwear;const g=s.variantGroups.get(s.activeVariant).group;return {variant:s.activeVariant,leftHidden:g.children.filter(m=>m.userData.bodyModule==='foot_l').every(m=>!m.visible),rightVisible:g.children.filter(m=>m.userData.bodyModule==='foot_r').every(m=>m.visible),count:g.children.length}}''');assert result['leftHidden'] and result['rightVisible'] and result['count']>=2,result;results.append(result)
 page.evaluate("window.xiaqingBodyModules.setVisible('foot_r',false)")
 assert page.evaluate("window.xiaqingFootwear.meshes.every(m=>!m.visible)")
 page.select_option('[aria-label="更换鞋子"]','none');assert page.evaluate("!window.xiaqingFootwear.enabled")
 page.evaluate("window.xiaqingBodyModules.setVisible('foot_l',true);window.xiaqingBodyModules.setVisible('foot_r',true)")
 assert page.evaluate("!window.xiaqingTest.model.getObjectByName('pl2020_pl2000_Props_Mat').visible && !window.xiaqingTest.model.getObjectByName('pl2020_pl2020_Cardigan_Mat').visible")
 # No shoes: verify suit mask is reversible independently of the foot mask.
 counts=page.evaluate('''()=>{const o=window.xiaqingOutfit,b=window.xiaqingTest.model.getObjectByName('pl2020_Skin_Mat');const equipped=b.geometry.index.count;o.setEquipped(false);const restored=b.geometry.index.count;const expected=b.userData.wardrobeBaseIndex.count;o.setEquipped(true);return {equipped,restored,expected,reEquipped:b.geometry.index.count};}''')
 assert counts['restored']==counts['expected'] and counts['equipped']==counts['reEquipped'] and counts['equipped']<counts['restored'],counts
 for id in ['torso','upper_arm_l','upper_arm_r','forearm_l','forearm_r','thigh_l','thigh_r','calf_l','calf_r']:
  assert page.evaluate('''id=>{const m=window.xiaqingBodyModules;m.setVisible(id,false);m.update();const mesh=window.xiaqingOutfit.group.children.find(o=>o.userData.bodyModule===id);const hidden=!mesh.visible;m.setVisible(id,true);return hidden;}''',id)
 page.evaluate("window.xiaqingOutfit.setEquipped(false);window.xiaqingBodyModules.setVisible('penis',false)")
 assert page.evaluate("!window.xiaqingTest.model.getObjectByName('pl2020_pl2000_Props_Mat').visible")
 page.evaluate("window.xiaqingBodyModules.setVisible('penis',true)")
 assert page.evaluate("window.xiaqingTest.model.getObjectByName('pl2020_pl2000_Props_Mat').visible")
 assert not errors,errors
 report={'shoeVisibility':results,'restoration':counts,'outfitModules':9,'browserErrors':errors,'posedPreviews':['Idle 0s','Walk 0.3s','Run 0.18s']};(OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report));browser.close()
