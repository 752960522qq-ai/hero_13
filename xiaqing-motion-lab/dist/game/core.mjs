import { CHARACTERS, ATTRIBUTES, ITEMS, RECIPES, RULES } from './data.mjs';

const clamp=(v,min=0,max=Infinity)=>Math.max(min,Math.min(max,Number.isFinite(+v)?+v:min));
const finite=(v,fallback=0)=>Number.isFinite(+v)?+v:fallback;
const copy=v=>JSON.parse(JSON.stringify(v));
const attrIds=ATTRIBUTES.map(a=>a.id);
const itemById=new Map(ITEMS.map(i=>[i.id,i]));
const characterById=new Map(CHARACTERS.map(c=>[c.id,c]));
const recipeById=new Map(RECIPES.map(i=>[i.id,i]));
const types=['light','medium','heavy'];
const damageTypes=['bullet','explosion','melee'];

/** Pure event-driven game rules. Distances use metres; times use seconds. */
export class Game {
  constructor({random=Math.random}={}) { this.random=random; this._uid=0; this.reset(); }
  reset(){
    const characters={};
    for(const d of CHARACTERS){
      characters[d.id]={id:d.id,levels:{...d.initialLevels},exp:Object.fromEntries(attrIds.map(k=>[k,0])),
        distance:{run:0,swim:0,jump:0,climb:0,drive:0},hp:100+20*d.initialLevels.health,
        stamina:100+20*d.initialLevels.stamina,skillLevel:0,
        skill:{active:false,energy:d.id==='CHR_001'?100:0,cooldown:0,remaining:0,thinking:false},
        inventory:[],armor:null,craft:null,use:null,bandageCooldown:0,taserCooldown:0,bleeding:false,
        ammo:30,ammoPools:{rifle:0,pistol:0,smg:0,sniper:0,shotgun:0},movement:'idle'};
    }
    this.state={version:1,activeId:'CHR_003',characters,story:false,realTime:0,worldTime:0,attacks:[],
      counterOpportunity:null,target:{id:'UNT_001',type:'light',hp:200,maxHp:200,stun:0,armor:0},
      vehicle:{id:'VEH_001',hp:100,maxHp:300,moving:false,distance:0},bombs:[],log:[]};
    return this._result(true,'新游戏已就绪');
  }
  get character(){return this.state.characters[this.state.activeId];}
  get definition(){return characterById.get(this.state.activeId);}
  get timeScale(){return this.character.id==='CHR_001'&&this.character.skill.active ? .5 : 1;}
  _result(ok,message,extra={}){return {ok,message,...extra};}
  _log(text){this.state.log.unshift({time:this.state.realTime,text});this.state.log.length=Math.min(60,this.state.log.length);}
  _done(text,extra={}){this._log(text);return this._result(true,text,extra);}
  _fail(text){return this._result(false,text);}
  _stats(c){
    const l=c.levels,n=c.skillLevel,d=characterById.get(c.id),luo=c.id==='CHR_001',xu=c.id==='CHR_002';
    return {maxHp:100+20*l.health,maxStamina:100+20*l.stamina,moveMultiplier:1+.04*l.stamina,
      stabilityMultiplier:1+.06*l.shooting,reloadMultiplier:1+.05*l.shooting,
      handlingMultiplier:1+.03*l.driving,vehicleSpeedMultiplier:1+.02*l.driving,
      meleeDamageMultiplier:1+.12*l.strength,meleeSpeedMultiplier:1+.03*l.strength,
      socialMultiplier:1+.05*l.charm,craftSpeedMultiplier:1+.06*l.intelligence,
      craftWasteMultiplier:1-.06*l.intelligence,positiveChanceMultiplier:1+.06*l.luck,
      negativeChanceMultiplier:1-.05*l.luck,attributeCap:d.attributeCap,skillCap:d.skillCap,
      skillDuration:luo?6+2*n:xu?8+n:0,skillMaxEnergy:luo?100:xu?0:100*(1+.15*n),
      skillRechargePerSecond:luo?100/120:xu?0:100/90*(1+.10*n),
      dodgeChance:clamp((.14+.10*n)*(1+.06*l.luck),0,1),
      dodgeWindow:.4+.1*n,counterWindow:.1+.05*n,
      damageReduction:xu&&c.skill.active?clamp(.30+.10*n,0,1):0,
      shootingDamageMultiplier:xu&&c.skill.active?1.10+.02*n:1,
      skillMeleeMultiplier:xu&&c.skill.active?1.20+.05*n:1,
      timeScale:luo&&c.skill.active?.5:1};
  }
  stats(){return this._stats(this.character);}
  nextExp(attribute,c=this.character){
    if(!attrIds.includes(attribute)||attribute==='luck'||c.levels[attribute]>=characterById.get(c.id).attributeCap)return null;
    const table=RULES.attributeExp||[1000,1500,2500,5000,10000,null];
    return c.levels[attribute]===5?(RULES.luoLevelSixExp??null):(table[c.levels[attribute]]??null);
  }
  _xp(c,attribute,amount){
    if(attribute==='luck'||amount<=0)return;
    const d=characterById.get(c.id);
    if(c.levels[attribute]>=d.attributeCap)return;
    c.exp[attribute]+=amount*(c.id==='CHR_001'?(RULES.luoGrowthMultiplier??1):1);
    let needed;
    while((needed=this.nextExp(attribute,c))!==null&&c.exp[attribute]>=needed){
      c.exp[attribute]-=needed;c.levels[attribute]++;
      this._log(`${d.name}的${ATTRIBUTES.find(a=>a.id===attribute)?.name||attribute}升至 ${c.levels[attribute]} 级`);
    }
    if(c.levels[attribute]>=d.attributeCap)c.exp[attribute]=0;
  }
  randomChance(base,kind='positive'){return clamp(base*(kind==='negative'?this.stats().negativeChanceMultiplier:this.stats().positiveChanceMultiplier),0,1);}
  setCharacter(id){
    if(!characterById.has(id))return this._fail('人物编号不存在');
    if(id===this.state.activeId)return this._result(true,'当前人物');
    this.character.skill.thinking=false;this.character.skill.active=false;this.character.skill.remaining=0;
    this.state.counterOpportunity=null;this.state.activeId=id;
    return this._done(`切换至${this.definition.name}`);
  }
  setSkillLevel(level){
    if(!Number.isInteger(level)||level<0||level>this.definition.skillCap)return this._fail('技能等级超出范围');
    this.character.skillLevel=level;this.character.skill.active=false;this.character.skill.remaining=0;
    this.character.skill.energy=Math.min(this.character.skill.energy,this.stats().skillMaxEnergy);
    this.state.counterOpportunity=null;return this._done(`技能预览等级设为 ${level}`);
  }
  _allowed(action,c=this.character){
    if(c.hp<=0&&!['heal','rest'].includes(action))return '人物生命值为零，需先恢复';
    if(this.state.story&&!['heal','rest'].includes(action))return '剧情场景中无法执行此动作';
    if(c.skill.thinking&&action!=='walk')return '思考中仅允许步行，请先暂停思考';
    if(c.use&&action!=='walk')return '物品使用中仅允许步行，或先中断使用';
    if(c.craft&&action!=='walk')return '制造中，请等待完成或取消制造';
    return null;
  }
  activateSkill(){
    const c=this.character,s=this.stats();
    if(c.id==='CHR_001'&&c.skill.active){c.skill.active=false;c.skill.remaining=0;return this._done('完美身法已关闭');}
    const blocked=this._allowed('skill');if(blocked)return this._fail(blocked);
    if(c.id==='CHR_003')return this._result(true,'制造书已打开',{openBook:true});
    if(c.id==='CHR_001'){
      if(c.skill.energy<=0)return this._fail('能量不足');
      c.skill.active=true;c.skill.remaining=s.skillDuration*c.skill.energy/100;
      return this._done('完美身法开启：时间流速 0.5 倍');
    }
    if(c.skill.cooldown>0)return this._fail('杀神本能尚在冷却');
    c.skill.active=true;c.skill.remaining=s.skillDuration;c.skill.cooldown=100;
    return this._done('杀神本能开启：减伤、伤害增益、射击不消耗子弹');
  }
  toggleThinking(){
    const c=this.character;if(c.id!=='CHR_003')return this._fail('思考充能为夏晴专属');
    if(c.skill.thinking){c.skill.thinking=false;return this._done('思考已暂停');}
    const blocked=this._allowed('think');if(blocked)return this._fail(blocked);
    if(c.skill.energy>=this.stats().skillMaxEnergy)return this._fail('思考点数已满');
    c.skill.thinking=true;return this._done('开始思考：仅可步行');
  }
  enterStory(enabled=true){
    this.state.story=Boolean(enabled);
    if(enabled){for(const c of Object.values(this.state.characters)){c.skill.thinking=false;c.skill.active=false;c.skill.remaining=0;}this.state.counterOpportunity=null;}
    return this._done(enabled?'进入剧情，思考已自动中断':'离开剧情');
  }
  _heal(c,amount){const actual=Math.min(clamp(amount),Math.max(0,this._stats(c).maxHp-c.hp));c.hp+=actual;this._xp(c,'health',actual*3);return actual;}
  perform(action,payload={}){
    if(action==='damage')return this.receiveAttack(payload);
    const c=this.character,s=this.stats(),blocked=this._allowed(action);if(blocked)return this._fail(blocked);
    if(['walk','run','swim','jump','climb','drive'].includes(action)){
      const distance=clamp(payload.distance,0,100000);if(distance<=0)return this._fail('移动距离必须大于零');
      if(action==='drive'&&payload.moving!==true)return this._fail('车辆必须保持运动才可获得驾驶经验');
      c.movement=action;
      if(action==='walk')return this._result(true,'步行',{distance});
      if(action==='drive'){this.state.vehicle.distance+=distance;this.state.vehicle.moving=true;}
      const old=c.distance[action],step=action==='drive'?100:['run','swim'].includes(action)?10:1;
      const xpPer=action==='drive'?10:['run','swim'].includes(action)?5:2;
      c.distance[action]+=distance;const xp=(Math.floor((c.distance[action]+1e-9)/step)-Math.floor((old+1e-9)/step))*xpPer;
      this._xp(c,action==='drive'?'driving':'stamina',xp);
      if(distance>=1)this._log(`${action} ${distance.toFixed(1)}m${xp?`，EXP +${xp}`:''}`);
      return this._result(true,'移动已计入成长',{distance,exp:xp});
    }
    if(action==='heal'){const actual=this._heal(c,finite(payload.amount,30));return this._done(`恢复 ${actual.toFixed(0)} HP`,{healed:actual,exp:actual*3});}
    if(action==='rest'){c.stamina=s.maxStamina;c.movement='idle';this.state.vehicle.moving=false;return this._done('休息，体力恢复；载具已停稳');}
    if(action==='shoot'){
      const special=payload.ammoType&&c.ammoPools[payload.ammoType]>0;
      if(!(c.id==='CHR_002'&&c.skill.active)){
        if(special)c.ammoPools[payload.ammoType]--;else if(c.ammo>0)c.ammo--;else return this._fail('子弹不足');
      }
      this._xp(c,'shooting',5);let damage=0;
      if(payload.hit!==false)damage=this._damageTarget(clamp(finite(payload.damage,20))*s.shootingDamageMultiplier,{type:'bullet',armorPiercing:Boolean(special)});
      return this._done(`射击，EXP +5${damage?`，目标伤害 ${damage.toFixed(1)}`:''}`,{damage,exp:5});
    }
    if(action==='melee'){
      const hit=payload.hit!==false,xp=hit?20:5;this._xp(c,'strength',xp);
      const damage=hit?this._damageTarget(clamp(finite(payload.damage,10))*s.meleeDamageMultiplier*s.skillMeleeMultiplier,{type:'melee'}):0;
      return this._done(`近战${hit?'命中':'未命中'}，EXP +${xp}`,{damage,exp:xp});
    }
    if(action==='social'||action==='craft'){
      const success=payload.success!==false,xp=success?50:10;this._xp(c,action==='social'?'charm':'intelligence',xp);
      return this._done(`${action==='social'?'社交':'普通制造'}${success?'成功':'失败'}，EXP +${xp}`,{exp:xp});
    }
    return this._fail('尚未定义的行动事件');
  }
  _damageTarget(raw,{type='bullet',armorPiercing=false,stun=0,nonlethal=false}={}){
    const target=this.state.target;let damage=raw;
    if(target.armor>0){const ratio=({bullet:.7,explosion:.4,melee:.2})[type]||0;const absorption=raw*ratio*(armorPiercing?.6:1),absorbed=Math.min(target.armor,absorption);target.armor-=absorbed;damage-=absorbed;}
    const actual=Math.min(Math.max(0,target.hp-(nonlethal&&target.hp>0?1:0)),damage);target.hp=Math.max(0,target.hp-actual);target.stun=Math.max(target.stun,stun);return actual;
  }
  receiveAttack({damage=20,type='bullet',armorPiercing=false,characterId=this.state.activeId}={}){
    const c=this.state.characters[characterId];if(!c)return this._fail('目标人物不存在');
    damage=clamp(damage);const reduced=damage*(1-this._stats(c).damageReduction);
    let absorbed=0;
    if(c.armor?.durability>0){
      const ratio=({bullet:.7,explosion:.4,melee:.2})[type]||0;
      absorbed=Math.min(c.armor.durability,reduced*ratio*(armorPiercing?.6:1));
      c.armor.durability=Math.max(0,c.armor.durability-absorbed);
    }
    const healthDamage=Math.min(c.hp,Math.max(0,reduced-absorbed));c.hp=Math.max(0,c.hp-healthDamage);
    if(c.hp===0){c.skill.active=false;c.skill.thinking=false;}
    return this._done(`受到 ${healthDamage.toFixed(1)} 生命伤害${absorbed?`，护甲吸收 ${absorbed.toFixed(1)}`:''}`,{damage:healthDamage,absorbed,reducedDamage:damage-reduced});
  }
  queueAttack({damage=20,type='bullet',delay=2,unitClass='light'}={}){
    if(this.state.story)return this._fail('剧情中无法生成攻击');
    const attack={id:`ATK_${++this._uid}`,characterId:this.state.activeId,remaining:clamp(delay,.01,3600),damage:clamp(damage),
      type:damageTypes.includes(type)?type:'bullet',unitClass:types.includes(unitClass)?unitClass:'light',attempted:false};
    this.state.attacks.push(attack);return this._done('来袭攻击已排入时间线',{attack});
  }
  dodgeAvailable(){
    if(this.character.id!=='CHR_001'||!this.character.skill.active)return null;
    return this.state.attacks.filter(a=>a.characterId===this.state.activeId&&!a.attempted&&a.remaining>0&&a.remaining<=this.stats().dodgeWindow+1e-9).sort((a,b)=>a.remaining-b.remaining)[0]||null;
  }
  dodge(){
    const a=this.dodgeAvailable();if(!a)return this._fail('当前没有可闪避攻击');
    a.attempted=true;const success=this.random()<this.stats().dodgeChance;
    if(!success)return this._done('闪避未成功，攻击仍将到来',{dodged:false});
    this.state.attacks=this.state.attacks.filter(v=>v!==a);
    const perfect=a.remaining<=this.stats().counterWindow+1e-9;
    if(perfect)this.state.counterOpportunity={characterId:this.state.activeId,unitClass:a.unitClass};
    return this._done(perfect?'完美闪避：可触发反击':'闪避成功',{dodged:true,perfect});
  }
  get counterAvailable(){return this.state.counterOpportunity?.characterId===this.state.activeId&&this.character.hp>0;}
  counter(){
    if(!this.counterAvailable)return this._fail('没有反击机会');
    const o=this.state.counterOpportunity;this.state.counterOpportunity=null;
    const stun={light:5,medium:3,heavy:1}[o.unitClass]||1;
    const damage=this._damageTarget(30*this.stats().meleeDamageMultiplier,{type:'melee',stun});
    return this._done(`闪避反击，伤害 ${damage.toFixed(1)}，眩晕 ${stun} 秒`,{damage,stun});
  }
  giveItem(itemId,quantity=1,c=this.character){
    const item=itemById.get(itemId);if(!item||itemId==='ITM_005')return this._fail('物品编号不存在，弹药需指定子编号');
    quantity=Math.floor(clamp(quantity,0,10000));if(!quantity)return this._fail('物品数量必须大于零');
    const original=quantity,stack=item.stack===null?Infinity:Math.max(1,item.stack||1);
    if(!['ITM_003','ITM_006'].includes(itemId)){
      for(const entry of c.inventory){if(entry.itemId===itemId&&entry.quantity<stack){const add=Math.min(quantity,stack-entry.quantity);entry.quantity+=add;quantity-=add;if(!quantity)break;}}
    }
    while(quantity>0){const add=Math.min(quantity,stack);const entry={uid:`INV_${++this._uid}`,itemId,quantity:add};
      if(itemId==='ITM_003')entry.charges=100;if(itemId==='ITM_006')entry.durability=100;
      c.inventory.push(entry);quantity-=add;
    }
    return this._result(true,`获得 ${item.name} ×${original}`,{quantity:original});
  }
  _consume(c,entry,quantity=1){entry.quantity-=quantity;if(entry.quantity<=0)c.inventory=c.inventory.filter(v=>v!==entry);}
  startCraft(itemId){
    const c=this.character;if(c.id!=='CHR_003')return this._fail('制造书为夏晴专属');
    const blocked=this._allowed('craftBook');if(blocked)return this._fail(blocked);
    const item=recipeById.get(itemId);if(!item)return this._fail('请选择具体可制造物品或弹药类型');
    if(c.skillLevel<item.level)return this._fail(`需要 ${item.level} 级巧手灵心`);
    if(c.skill.energy+1e-9<item.cost)return this._fail('思考点数不足');
    c.skill.energy=Math.max(0,c.skill.energy-item.cost);c.craft={itemId,remaining:item.duration,duration:item.duration,cost:item.cost};
    return this._done(`开始制造${item.name}，消耗 ${item.cost} 点`);
  }
  cancelCraft(){const c=this.character;if(!c.craft)return this._fail('没有进行中的制造');const refund=c.craft.cost;c.craft=null;c.skill.energy=Math.min(this.stats().skillMaxEnergy,c.skill.energy+refund);return this._done('制造已取消，点数已退回');}
  useItem(itemId,payload={}){
    const c=this.character,entry=c.inventory.find(v=>v.itemId===itemId&&(!payload.uid||v.uid===payload.uid));
    if(!entry)return this._fail('物品栏中没有此物品');
    const blocked=this._allowed('useItem');if(blocked)return this._fail(blocked);
    const item=itemById.get(itemId),distance=clamp(finite(payload.distance,0));
    if(itemId==='ITM_001'){
      if(distance>25)return this._fail('超过最大投掷距离 25m');
      this._consume(c,entry);const direct=Boolean(payload.directHit),vehicle=Boolean(payload.vehicle);
      let directDamage=0;
      if(direct){directDamage=80*(vehicle?.5:1);if(vehicle)this.state.vehicle.hp=Math.max(0,this.state.vehicle.hp-directDamage);else this._damageTarget(directDamage,{type:'melee'});}
      this.state.bombs.push({remaining:3,blastDistance:clamp(finite(payload.blastDistance,0)),vehicle,characterId:c.id});
      return this._done('土制炸弹已投掷，3 秒后引爆',{damage:directDamage});
    }
    if(itemId==='ITM_002'){
      if(c.bandageCooldown>0)return this._fail('绷带使用冷却中');
      if(c.hp>=this.stats().maxHp&&!c.bleeding)return this._fail('当前生命已满，且没有流血状态');
      c.use={itemId,uid:entry.uid,remaining:3,duration:3};return this._done('开始使用绷带，可步行；3 秒后生效');
    }
    if(itemId==='ITM_003'){
      if(distance>8)return this._fail('超过泰瑟枪有效射程 8m');
      if(c.taserCooldown>0)return this._fail('泰瑟枪射击间隔为 2 秒');
      if(entry.charges<20)return this._fail('泰瑟枪电量不足');
      const unit=types.includes(payload.unitClass)?payload.unitClass:this.state.target.type;
      const stun={light:5,medium:2,heavy:0}[unit]||0;
      entry.charges-=20;c.taserCooldown=2;
      const damage=this._damageTarget(5,{type:'bullet',stun,nonlethal:true});if(entry.charges<=0)this._consume(c,entry);
      return this._done(`泰瑟枪命中${stun?`，眩晕 ${stun} 秒`:'，重型单位免疫眩晕'}${entry.charges<=0?'，电量耗尽已报废':''}`,{damage,stun});
    }
    if(itemId==='ITM_004'){
      if(distance>2)return this._fail('维修距离不得超过 2m');
      if(this.state.vehicle.moving)return this._fail('载具必须静止才能维修');
      if(this.state.vehicle.hp>=this.state.vehicle.maxHp)return this._fail('载具耐久已满');
      c.use={itemId,uid:entry.uid,remaining:8,duration:8};return this._done('开始维修，8 秒后完成并消耗工具');
    }
    if(itemId==='ITM_006'){
      const previous=c.armor;c.armor={itemId,durability:entry.durability??100,maxDurability:100};this._consume(c,entry);
      if(previous){this.giveItem('ITM_006',1,c);c.inventory[c.inventory.length-1].durability=previous.durability;}
      return this._done('凯夫拉防弹衣已装备');
    }
    if(item.parentId==='ITM_005'){
      c.ammoPools[item.ammoType]+=entry.quantity;const quantity=entry.quantity;this._consume(c,entry,quantity);
      return this._done(`装入 ${item.name} ×${quantity}`,{quantity});
    }
    return this._fail('该物品暂无使用方式');
  }
  interruptUse(){if(!this.character.use)return this._fail('没有进行中的物品使用');this.character.use=null;return this._done('使用已中断，物品已保留');}
  repairArmor(amount){if(!this.character.armor)return this._fail('未装备护甲');this.character.armor.durability=clamp(this.character.armor.durability+clamp(amount),0,100);return this._done('护甲已修复');}
  tick(realDt){
    realDt=clamp(realDt,0,3600);if(!realDt)return;
    // Split at 50ms so a long tick resolves expiry before subsequent attacks.
    let remaining=realDt;while(remaining>1e-9){const dt=Math.min(remaining,.05);this._tickStep(dt);remaining-=dt;}
  }
  _tickStep(dt){
    const worldDt=dt*this.timeScale;this.state.realTime+=dt;this.state.worldTime+=worldDt;
    for(const c of Object.values(this.state.characters)){
      const s=this._stats(c);c.skill.cooldown=Math.max(0,c.skill.cooldown-dt);
      c.bandageCooldown=Math.max(0,c.bandageCooldown-worldDt);c.taserCooldown=Math.max(0,c.taserCooldown-worldDt);
      if(c.skill.active){
        c.skill.remaining=Math.max(0,c.skill.remaining-dt);
        if(c.id==='CHR_001'){c.skill.energy=Math.max(0,c.skill.energy-dt*100/s.skillDuration);if(c.skill.energy<=1e-9)c.skill.remaining=0;}
        if(c.skill.remaining<=1e-9){c.skill.active=false;c.skill.remaining=0;}
      }else if(c.id==='CHR_001')c.skill.energy=Math.min(100,c.skill.energy+dt*s.skillRechargePerSecond);
      if(c.id==='CHR_003'&&c.skill.thinking){
        if(this.state.story||c.hp<=0)c.skill.thinking=false;
        else{c.skill.energy=Math.min(s.skillMaxEnergy,c.skill.energy+dt*s.skillRechargePerSecond);if(c.skill.energy>=s.skillMaxEnergy-1e-9)c.skill.thinking=false;}
      }
      if(c.craft){c.craft.remaining=Math.max(0,c.craft.remaining-worldDt);if(c.craft.remaining<=1e-9){const item=recipeById.get(c.craft.itemId);this.giveItem(item.id,item.quantity||1,c);c.craft=null;this._xp(c,'intelligence',50);this._log(`${characterById.get(c.id).name}完成制造：${item.name}，智力 EXP +50`);}}
      if(c.use){
        if(c.use.itemId==='ITM_004'&&this.state.vehicle.moving){c.use=null;this._log('载具开始移动，维修已中断，工具保留');}
        else{c.use.remaining=Math.max(0,c.use.remaining-worldDt);if(c.use.remaining<=1e-9){const job=c.use,entry=c.inventory.find(v=>v.uid===job.uid);c.use=null;
          if(entry){if(job.itemId==='ITM_002'){const actual=this._heal(c,30);c.bleeding=false;c.bandageCooldown=5;this._log(`绷带完成：恢复 ${actual.toFixed(0)} HP，解除流血`);}else{this.state.vehicle.hp=Math.min(this.state.vehicle.maxHp,this.state.vehicle.hp+150);this._log('维修完成：载具耐久恢复 150');}this._consume(c,entry);}
        }}
      }
    }
    this.state.target.stun=Math.max(0,this.state.target.stun-worldDt);
    for(const a of [...this.state.attacks]){a.remaining-=worldDt;if(a.remaining<=1e-9){this.state.attacks=this.state.attacks.filter(v=>v!==a);this.receiveAttack({...a,characterId:a.characterId});}}
    for(const bomb of [...this.state.bombs]){bomb.remaining-=worldDt;if(bomb.remaining<=1e-9){const damage=100*Math.max(0,1-bomb.blastDistance/5)*(bomb.vehicle?.5:1);if(bomb.vehicle)this.state.vehicle.hp=Math.max(0,this.state.vehicle.hp-damage);else this._damageTarget(damage,{type:'explosion'});this.state.bombs=this.state.bombs.filter(v=>v!==bomb);this._log(`炸弹引爆，伤害 ${damage.toFixed(1)}`);}}
  }
  snapshot(){return copy(this.state);}
  restore(data){
    // Whitelist all saved fields. Invalid saves never partially modify the game.
    if(!data||typeof data!=='object'||data.version!==1||!characterById.has(data.activeId)||!data.characters)return this._fail('存档版本或人物数据无效');
    const temporary=new Game({random:this.random}),state=temporary.state;let maxUid=0;
    const uid=raw=>{const match=String(raw||'').match(/^INV_(\d+)$/);maxUid=Math.max(maxUid,match?clamp(+match[1],0,1e9):0);return `INV_${++maxUid}`;};
    try{
      for(const def of CHARACTERS){
        const raw=data.characters[def.id],c=state.characters[def.id];if(!raw||!raw.levels||!raw.exp)return this._fail('存档缺少人物记录');
        for(const id of attrIds){c.levels[id]=id==='luck'?def.initialLevels.luck:Math.floor(clamp(raw.levels[id],0,def.attributeCap));c.exp[id]=id==='luck'?0:clamp(raw.exp[id],0,1e9);}
        c.skillLevel=Math.floor(clamp(raw.skillLevel,0,def.skillCap));const s=temporary._stats(c);
        c.hp=clamp(raw.hp,0,s.maxHp);c.stamina=clamp(raw.stamina,0,s.maxStamina);
        c.skill={active:false,thinking:false,energy:clamp(raw.skill?.energy,0,s.skillMaxEnergy),cooldown:clamp(raw.skill?.cooldown,0,100),remaining:0};
        for(const key of Object.keys(c.distance))c.distance[key]=clamp(raw.distance?.[key],0,1e12);
        c.bandageCooldown=clamp(raw.bandageCooldown,0,5);c.taserCooldown=clamp(raw.taserCooldown,0,2);c.bleeding=raw.bleeding===true;
        c.ammo=Math.floor(clamp(raw.ammo,0,1e6));for(const type of Object.keys(c.ammoPools))c.ammoPools[type]=Math.floor(clamp(raw.ammoPools?.[type],0,1e6));
        if(!Array.isArray(raw.inventory)||raw.inventory.length>10000)return this._fail('物品栏数据无效');
        for(const saved of raw.inventory){const item=itemById.get(saved.itemId);if(!item||item.id==='ITM_005')continue;const quantity=Math.floor(clamp(saved.quantity,0,item.stack===null?1e6:item.stack||1));if(!quantity)continue;
          const e={uid:uid(saved.uid),itemId:item.id,quantity};if(item.id==='ITM_003'){e.charges=Math.floor(clamp(saved.charges,0,100)/20)*20;if(!e.charges)continue;}if(item.id==='ITM_006')e.durability=clamp(saved.durability,0,100);c.inventory.push(e);
        }
        if(raw.armor?.itemId==='ITM_006')c.armor={itemId:'ITM_006',durability:clamp(raw.armor.durability,0,100),maxDurability:100};
        if(raw.craft&&def.id==='CHR_003'){
          const item=recipeById.get(raw.craft.itemId);if(item&&item.level<=c.skillLevel)c.craft={itemId:item.id,duration:item.duration,remaining:clamp(raw.craft.remaining,0,item.duration),cost:item.cost};
        }
        // Item use and combat are interrupted across reload. No elapsed offline rewards.
      }
      state.activeId=data.activeId;state.story=data.story===true;state.realTime=clamp(data.realTime,0,1e12);state.worldTime=clamp(data.worldTime,0,1e12);
      state.target={id:'UNT_001',type:types.includes(data.target?.type)?data.target.type:'light',hp:clamp(data.target?.hp,0,200),maxHp:200,stun:clamp(data.target?.stun,0,5),armor:clamp(data.target?.armor,0,100)};
      state.vehicle={id:'VEH_001',hp:clamp(data.vehicle?.hp,0,300),maxHp:300,moving:false,distance:clamp(data.vehicle?.distance,0,1e12)};
      state.log=Array.isArray(data.log)?data.log.slice(0,60).filter(l=>typeof l?.text==='string').map(l=>({time:clamp(l.time,0,1e12),text:l.text.slice(0,300)})):[];
      this.state=state;this._uid=maxUid+100;return this._result(true,'存档已载入；思考、战斗和使用动作已暂停');
    }catch{return this._fail('存档格式无效');}
  }
}
