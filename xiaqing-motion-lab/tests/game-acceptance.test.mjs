import test from 'node:test';
import assert from 'node:assert/strict';
import {Game} from '../dist/game/core.mjs';
import {CHARACTERS, ITEMS, RECIPES} from '../dist/game/data.mjs';

const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-7,`${a} != ${b}`);
const gameFor=id=>{const g=new Game({random:()=>0});g.setCharacter(id);return g;};

test('three protagonists preserve all supplied initial attribute levels',()=>{
  const supplied=[[1,1,1,1,1,1,2,6],[3,3,4,3,4,0,1,1],[1,0,0,2,0,4,4,3]];
  for(let n=0;n<3;n++)assert.deepEqual(Object.values(CHARACTERS[n].initialLevels),supplied[n]);
  assert.equal(CHARACTERS[0].model,null);assert.equal(CHARACTERS[1].model,null);
});
test('initial effective attributes use additive percentages on level-zero base',()=>{
  const g=gameFor('CHR_002'),s=g.stats();
  assert.equal(s.maxHp,160);assert.equal(s.maxStamina,160);
  near(s.moveMultiplier,1.12);near(s.stabilityMultiplier,1.24);near(s.reloadMultiplier,1.20);
  near(s.handlingMultiplier,1.09);near(s.vehicleSpeedMultiplier,1.06);
  near(s.meleeDamageMultiplier,1.48);near(s.meleeSpeedMultiplier,1.12);
});
test('fractional movement accumulates exact EXP only at distance units',()=>{
  const g=gameFor('CHR_003');
  g.perform('run',{distance:4});g.perform('run',{distance:5.9});assert.equal(g.character.exp.stamina,0);
  g.perform('run',{distance:.1});assert.equal(g.character.exp.stamina,5);
  g.perform('swim',{distance:20});g.perform('jump',{distance:.75});g.perform('jump',{distance:.25});
  g.perform('climb',{distance:2});assert.equal(g.character.exp.stamina,21);
  assert.equal(g.perform('drive',{distance:100,moving:false}).ok,false);
  g.perform('drive',{distance:99,moving:true});assert.equal(g.character.exp.driving,0);
  g.perform('drive',{distance:1,moving:true});assert.equal(g.character.exp.driving,10);
});
test('one bullet trains five EXP and levels carry only excess EXP',()=>{
  const g=gameFor('CHR_003');g.character.ammo=400;
  for(let i=0;i<201;i++)g.perform('shoot',{hit:false});
  assert.equal(g.character.levels.shooting,1);assert.equal(g.character.exp.shooting,5);
  assert.equal(g.nextExp('shooting'),1500);assert.equal(g.character.ammo,199);
});
test('healing awards only actual restored HP and never full-health EXP',()=>{
  const g=gameFor('CHR_003');g.perform('heal',{amount:100});assert.equal(g.character.exp.health,0);
  g.receiveAttack({damage:7});g.perform('heal',{amount:100});assert.equal(g.character.exp.health,21);
});
test('luck multiplies initial probabilities and is bounded',()=>{
  const g=gameFor('CHR_001');near(g.randomChance(.14),.1904);near(g.randomChance(.5,'negative'),.35);
  g.setSkillLevel(6);assert.equal(g.stats().dodgeChance,1);assert.equal(g.nextExp('luck'),null);
});
test('Luo sixth attribute threshold remains explicitly unconfigured',()=>{
  const g=gameFor('CHR_001');g.character.levels.charm=5;
  g.perform('social',{success:true});assert.equal(g.character.levels.charm,5);
  assert.equal(g.character.exp.charm,50);assert.equal(g.nextExp('charm'),null);
});
test('armor absorbs per damage type and cannot absorb more than durability',()=>{
  for(const [type,absorb] of [['bullet',70],['explosion',40],['melee',20]]){
    const g=gameFor('CHR_002');g.giveItem('ITM_006');g.useItem('ITM_006');
    const result=g.receiveAttack({damage:100,type});near(result.absorbed,absorb);near(g.character.hp,160-100+absorb);
  }
  const g=gameFor('CHR_002');g.giveItem('ITM_006');g.useItem('ITM_006');g.character.armor.durability=10;
  g.receiveAttack({damage:100,type:'bullet'});near(g.character.hp,70);near(g.character.armor.durability,0);
});
test('armor piercing reduces armor protection by forty percent',()=>{
  const g=gameFor('CHR_002');g.giveItem('ITM_006');g.useItem('ITM_006');
  const result=g.receiveAttack({damage:100,type:'bullet',armorPiercing:true});near(result.absorbed,42);near(result.damage,58);
});
test('Xu active skill preserves ammo and applies exact defense/offense',()=>{
  const g=gameFor('CHR_002');g.character.ammo=0;g.activateSkill();
  const shot=g.perform('shoot',{damage:20});near(shot.damage,22);assert.equal(g.character.ammo,0);
  const received=g.receiveAttack({damage:100});near(received.damage,70);
  g.tick(8);assert.equal(g.character.skill.active,false);assert.equal(g.perform('shoot').ok,false);
});
test('Luo world attack clock slows while energy duration uses real seconds',()=>{
  const g=gameFor('CHR_001');g.activateSkill();g.queueAttack({damage:10,delay:1});
  g.tick(1);near(g.state.attacks[0].remaining,.5);assert.equal(g.dodgeAvailable(),null);
  g.tick(.2);assert.ok(g.dodgeAvailable());g.tick(.6);assert.ok(g.dodge().perfect);
  const result=g.counter();near(result.damage,33.6);assert.equal(result.stun,5);
});
test('thinking charges in ninety seconds, restricts actions and auto-interrupts on story',()=>{
  const g=gameFor('CHR_003');assert.equal(g.toggleThinking().ok,true);g.tick(45);near(g.character.skill.energy,50);
  assert.equal(g.perform('run',{distance:10}).ok,false);assert.equal(g.perform('shoot').ok,false);
  assert.equal(g.perform('walk',{distance:1}).ok,true);g.enterStory(true);assert.equal(g.character.skill.thinking,false);
  g.tick(45);near(g.character.skill.energy,50);
});
test('book craft takes fixed time and points and awards successful-craft intelligence EXP',()=>{
  const g=gameFor('CHR_003');g.character.skill.energy=100;
  assert.equal(g.startCraft('ITM_001').ok,true);near(g.character.skill.energy,80);
  g.tick(5.99);assert.equal(g.character.inventory.length,0);g.tick(.01);
  assert.equal(g.character.inventory[0].itemId,'ITM_001');assert.equal(g.character.exp.intelligence,50);
  assert.equal(g.startCraft('ITM_003').ok,false);
});
test('every armor-piercing batch crafts only its selected ammunition quantity',()=>{
  for(const [suffix,quantity] of [['A',30],['B',20],['C',50],['D',10],['E',15]]){
    const g=gameFor('CHR_003');g.setSkillLevel(2);g.character.skill.energy=100;
    assert.equal(g.startCraft(`ITM_005_${suffix}`).ok,true);g.tick(5);
    assert.equal(g.character.inventory.reduce((n,i)=>n+i.quantity,0),quantity);
    assert.ok(g.character.inventory.every(i=>i.itemId===`ITM_005_${suffix}`));
  }
  assert.ok(RECIPES.some(i=>i.id==='ITM_004'&&i.level===1));
});
test('taser instances have independent five-shot batteries and self-remove',()=>{
  const g=gameFor('CHR_003');g.giveItem('ITM_003',2);const [first,second]=g.character.inventory;
  for(let i=0;i<5;i++){assert.equal(g.useItem('ITM_003',{uid:first.uid,distance:8,unitClass:'heavy'}).ok,true);g.tick(2);}
  assert.equal(g.character.inventory.length,1);assert.equal(g.character.inventory[0].uid,second.uid);assert.equal(second.charges,100);
});
test('nonlethal taser leaves at least one HP, armored target uses damage-type absorption',()=>{
  const taser=gameFor('CHR_003');taser.state.target.hp=2;taser.giveItem('ITM_003');taser.useItem('ITM_003');
  assert.equal(taser.state.target.hp,1);
  const melee=gameFor('CHR_003');melee.state.target.armor=100;
  const hit=melee.perform('melee',{damage:100});near(hit.damage,80);
  const bomb=gameFor('CHR_003');bomb.state.target.armor=100;bomb.giveItem('ITM_001');bomb.useItem('ITM_001');bomb.tick(3);
  near(bomb.state.target.hp,140);
});
test('repair interruption preserves tool, completion consumes and clamps HP',()=>{
  const g=gameFor('CHR_003');g.giveItem('ITM_004');assert.equal(g.useItem('ITM_004',{distance:2}).ok,true);
  g.tick(4);g.interruptUse();assert.equal(g.character.inventory[0].quantity,1);assert.equal(g.state.vehicle.hp,100);
  g.useItem('ITM_004',{distance:2});g.tick(8);assert.equal(g.character.inventory.length,0);assert.equal(g.state.vehicle.hp,250);
});
test('bomb center, edge falloff and vehicle multiplier follow specification',()=>{
  for(const [blastDistance,vehicle,expected] of [[0,false,100],[2.5,false,50],[5,false,0],[0,true,50]]){
    const g=gameFor('CHR_003');g.giveItem('ITM_001');g.useItem('ITM_001',{distance:25,blastDistance,vehicle});
    const before=vehicle?g.state.vehicle.hp:g.state.target.hp;g.tick(3);near(before-(vehicle?g.state.vehicle.hp:g.state.target.hp),expected);
  }
});
test('restore keeps inventory instance data, fixed luck and character separation',()=>{
  const g=gameFor('CHR_003');g.giveItem('ITM_003');g.useItem('ITM_003');g.tick(2);
  const saved=g.snapshot();const h=new Game();assert.equal(h.restore(saved).ok,true);
  assert.equal(h.character.inventory[0].charges,80);assert.equal(h.character.levels.luck,3);
  h.setCharacter('CHR_001');assert.equal(h.character.inventory.length,0);assert.equal(h.character.levels.luck,6);
});
