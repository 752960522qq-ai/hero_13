import {Game} from './core.mjs';
import {CHARACTERS, ATTRIBUTES, ITEMS, RECIPES, RULES} from './data.mjs';

const $ = id => document.getElementById(id);
const game = new Game();
window.hero13Game = game;
const SAVE_KEY = 'hero13.game.v1';
const number = (n, digits = 0) => Number.isFinite(Number(n)) ? Number(n).toFixed(digits).replace(/\.0+$/, '') : '—';
const percent = n => `${number(n * 100, 1)}%`;
const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const meter = (value, max) => `<div class="meter"><span style="width:${Math.max(0, Math.min(100, Number(value || 0) / (max || 1) * 100))}%"></span></div>`;
const itemById = Object.fromEntries(ITEMS.map(item => [item.id, item]));
const icons = {health:'♡',stamina:'↗',shooting:'⌖',driving:'▱',strength:'◇',charm:'✧',intelligence:'⌘',luck:'☆'};
const itemIcons = {ITM_001:'◉',ITM_002:'✚',ITM_003:'ϟ',ITM_004:'⚒',ITM_005:'⋮',ITM_006:'♜'};
const iconFor = id => itemIcons[id.startsWith('ITM_005') ? 'ITM_005' : id] || '◇';
let currentTab = 'attributes';
let previousCharacter = null;
let toastTimer, saveTimer;
let restoring = false;
let storageAvailable = true;
let lastFrameMessage = '';
const signatures = new Map();

function update(id, markup) {
  if (signatures.get(id) === markup) return;
  signatures.set(id, markup);
  $(id).innerHTML = markup;
}

function toast(message, error = false) {
  if (!message) return;
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').dataset.error = String(error);
  $('toast').hidden = false;
  toastTimer = setTimeout(() => {$('toast').hidden = true;}, 4200);
}

function save() {
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(game.snapshot()));
    $('saveState').innerHTML = '<i></i>已保存在本机';
  } catch {
    storageAvailable = false;
    $('saveState').textContent = '本机存储不可用';
  }
}

try {
  const saved = localStorage.getItem(SAVE_KEY);
  if (saved) {
    const result = game.restore(JSON.parse(saved));
    if (result?.ok === false) toast('本地存档无法读取，已使用新档案。', true);
    else restoring = true;
  }
} catch { toast('本地存档无法读取，已使用新档案。', true); }

function command(fn, {silent = false} = {}) {
  try {
    const result = fn();
    if (!silent && result?.message) toast(result.message, result.ok === false);
    if (result?.openBook) selectTab('crafting');
    render();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 250);
    return result;
  } catch (error) {
    console.error(error);
    toast('操作未完成，请重试。', true);
    return {ok:false};
  }
}

function selectTab(name) {
  if (!['attributes', 'crafting', 'inventory', 'sandbox'].includes(name)) return;
  currentTab = name;
  for (const button of document.querySelectorAll('[data-tab]')) {
    const active = button.dataset.tab === name;
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
    $(`panel-${button.dataset.tab}`).hidden = !active;
  }
  render();
}

document.querySelector('.tabs').addEventListener('click', event => {
  const tab = event.target.closest('[data-tab]');
  if (tab) selectTab(tab.dataset.tab);
});
document.querySelector('.tabs').addEventListener('keydown', event => {
  const names = ['attributes','crafting','inventory','sandbox'];
  let next = names.indexOf(currentTab);
  if (event.key === 'ArrowRight') next = (next + 1) % names.length;
  else if (event.key === 'ArrowLeft') next = (next + names.length - 1) % names.length;
  else if (event.key === 'Home') next = 0;
  else if (event.key === 'End') next = names.length - 1;
  else return;
  event.preventDefault(); selectTab(names[next]); $(`tab-${names[next]}`).focus();
});

function characterChanged() {
  const definition = game.definition;
  const isXia = definition.id === 'CHR_003';
  $('characterName').textContent = definition.name;
  $('characterRole').textContent = definition.role;
  $('characterTrait').textContent = definition.description;
  $('stageId').textContent = definition.id;
  $('placeholderId').textContent = definition.id;
  $('assetStatus').textContent = isXia ? '现有人物资源' : '编号待命';
  $('stageIndex').textContent = definition.id.slice(-2);
  $('placeholder').hidden = isXia;
  $('characterFrame').hidden = !isXia;
  document.querySelector('.character-stage').classList.toggle('has-model',isXia);
  $('movementNote').textContent = isXia ? '在预览区内使用 WASD / 摇杆移动。实际跑动距离计入体力成长。' : '模型接入前，可在演练场验证此人物的全部数据与技能。';
  $('attributeCap').textContent = `属性上限 ${definition.attributeCap} 级`;
  $('inventoryOwner').textContent = `${definition.name}的物品栏`;
  $('skillLevel').innerHTML = Array.from({length:definition.skillCap + 1}, (_, level) => `<option value="${level}">${level} 级</option>`).join('');
  $('skillLevel').value = String(game.character.skillLevel);
  $('thinkButton').hidden = !isXia;
  renderSandbox();
  previousCharacter = definition.id;
  lastFrameMessage = '';
}

function attributeEffect(id, stats) {
  const effects = {
    health:`生命上限 ${number(stats.maxHp)} HP`,
    stamina:`体力上限 ${number(stats.maxStamina)} · 移速 +${percent(stats.moveMultiplier - 1)}`,
    shooting:`稳定性 +${percent(stats.stabilityMultiplier - 1)} · 换弹速度 +${percent(stats.reloadMultiplier - 1)}`,
    driving:`操纵性 +${percent(stats.handlingMultiplier - 1)} · 车速 +${percent(stats.vehicleSpeedMultiplier - 1)}`,
    strength:`近战伤害 +${percent(stats.meleeDamageMultiplier - 1)} · 攻速 +${percent(stats.meleeSpeedMultiplier - 1)}`,
    charm:`社交加成 +${percent(stats.socialMultiplier - 1)}`,
    intelligence:`制造速度 +${percent(stats.craftSpeedMultiplier - 1)} · 损耗 −${percent(1 - stats.craftWasteMultiplier)}`,
    luck:`正向概率 ×${number(stats.positiveChanceMultiplier, 2)} · 负向概率 ×${number(stats.negativeChanceMultiplier, 2)}`,
  };
  return effects[id] || '';
}

function renderAttributes(stats) {
  const character = game.character;
  update('attributes', ATTRIBUTES.map(attribute => {
    const level = character.levels[attribute.id];
    const exp = character.exp[attribute.id] || 0;
    const next = game.nextExp(attribute.id);
    const atCap = level >= game.definition.attributeCap;
    const fixed = attribute.id === 'luck';
    const label = fixed ? '固定 · 不可升级' : next ? `${number(exp)} / ${next} EXP` : atCap ? '已达上限' : '下一级经验待配置';
    return `<article class="attribute" data-attribute="${attribute.id}"><div class="attribute-top"><span class="attribute-icon">${icons[attribute.id]}</span><span class="attribute-name">${escape(attribute.name)}</span><span class="attribute-level">${level}<small> LV</small></span></div><p class="attribute-effect">${attributeEffect(attribute.id, stats)}</p>${meter(fixed || atCap ? 1 : exp, fixed || atCap ? 1 : next || 1)}<div class="exp-row"><span>${label}</span><span>${fixed ? 'LUCK' : `MAX ${game.definition.attributeCap}`}</span></div></article>`;
  }).join(''));
  update('growthRules', `<p>生命和体力以 0 级 100 为基准，每级增加 20；百分比加成都以 0 级初始基准相加，不逐级复利。</p><p>0→1 / 1→2 / 2→3 / 3→4 / 4→5：1000 / 1500 / 2500 / 5000 / 10000 EXP；罗甄 5→6 级为 ${RULES.luoLevelSixExp} EXP。初始等级直接生效，运气固定。</p>${ATTRIBUTES.filter(a => a.id !== 'luck').map(a => `<p><strong>${escape(a.name)}</strong>：${escape(a.description)}</p>`).join('')}<p>运气修正乘在事件原始概率上，并限制在 0—100%。正向 ×(1 + 6% × 等级)，负向 ×(1 − 5% × 等级)。</p><p>待配置：罗甄的成长速度倍率；专属技能升级获取方式。专属技能暂按 0—5 级、罗甄 0—6 级开放配置预览。</p>`);
}

function renderVitals(stats) {
  const c = game.character;
  const armor = c.armor?.durability ?? c.armor?.value ?? 0;
  update('vitals', [['health','生命',c.hp,stats.maxHp,'HP'],['stamina','体力',c.stamina,stats.maxStamina,'SP'],['armor','护甲',armor,c.armor ? 100 : 0,'AP']].map(([id,label,value,max,unit]) => `<div class="vital ${id}"><div class="vital-label"><span>${label}</span><span>${unit}</span></div><div class="vital-number">${number(value)}<small>/ ${number(max)}</small></div>${meter(value,max)}</div>`).join(''));
}

function renderSkill(stats) {
  const c = game.character;
  const id = c.id;
  const skill = c.skill;
  const isXia = id === 'CHR_003';
  const isLuo = id === 'CHR_001';
  let description, resourceLabel, resourceText, resourceValue, resourceMax;
  if (isLuo) {
    description = `时间流速 0.5× · 最长 ${number(stats.skillDuration)} 秒。闪避概率 ${percent(stats.dodgeChance)}（含运气），预警窗口 ${number(stats.dodgeWindow,2)} 秒，完美反击窗口 ${number(stats.counterWindow,2)} 秒，均按正常时间计。完全充能 120 秒。`;
    resourceLabel = skill.active ? '完美身法已开启' : '身法能量';
    resourceText = `${number(skill.energy,1)} / ${number(stats.skillMaxEnergy)}`;
    resourceValue = skill.energy; resourceMax = stats.skillMaxEnergy;
  } else if (isXia) {
    description = `制造书就地制造，成品进入物品栏。思考充能速度 ${number(stats.skillRechargePerSecond,2)} 点/秒，上限 ${number(stats.skillMaxEnergy)} 点。思考期间仅可步行；进入剧情会自动中断。书内制造不受智力加成。`;
    resourceLabel = skill.thinking ? '正在思考 · 仅可步行' : '思考点数';
    resourceText = `${number(skill.energy,1)} / ${number(stats.skillMaxEnergy)}`;
    resourceValue = skill.energy; resourceMax = stats.skillMaxEnergy;
  } else {
    description = `持续 ${number(stats.skillDuration)} 秒 · 冷却 100 秒。开启时减伤 ${percent(.3 + .1*c.skillLevel)}，近战伤害 +${percent(.2 + .05*c.skillLevel)}，射击伤害 +${percent(.1 + .02*c.skillLevel)}，射击不消耗子弹。`;
    resourceLabel = skill.active ? '杀神本能已开启' : skill.cooldown > 0 ? '技能冷却中' : '技能就绪';
    resourceText = skill.active ? `剩余 ${number(skill.remaining,1)} 秒` : skill.cooldown > 0 ? `${number(skill.cooldown,1)} 秒` : 'READY';
    resourceValue = skill.active ? skill.remaining : Math.max(0, 100 - skill.cooldown); resourceMax = skill.active ? stats.skillDuration : 100;
  }
  // Keep static description outside the fast-changing meter to preserve readable text.
  update('skillContent', `<div class="skill-head"><span class="skill-icon">${isLuo ? '⌁' : isXia ? '✧' : '⌖'}</span><div><h3>${escape(game.definition.skillName)}</h3><span class="section-kicker">${game.definition.skillId} · 专属技能</span></div><span class="skill-level">LV ${c.skillLevel}</span></div><p class="skill-description">${description}</p><div class="skill-resource"><span>${resourceLabel}</span><strong>${resourceText}</strong></div>${meter(resourceValue,resourceMax)}`);
  document.querySelector('.skill-panel').classList.toggle('is-thinking', !!skill.thinking);
  $('activateSkill').textContent = isXia ? '打开制造书' : isLuo && skill.active ? '取消身法' : '开启技能';
  $('activateSkill').disabled = c.hp <= 0 || (!isXia && !isLuo && (skill.active || skill.cooldown > 0));
  $('thinkButton').textContent = skill.thinking ? '暂停思考' : '开始思考';
  $('thinkButton').disabled = c.hp <= 0 || game.state.story;
  const incoming = game.dodgeAvailable();
  $('dodgeButton').hidden = !incoming;
  $('counterButton').hidden = !game.counterAvailable;
  const attacks = game.state.attacks || [];
  const earliest = attacks.filter(attack => !attack.dodged && (attack.characterId == null || attack.characterId === c.id)).sort((a,b) => (a.remaining ?? a.delay ?? 0) - (b.remaining ?? b.delay ?? 0))[0];
  const remaining = earliest?.remaining ?? (earliest?.at != null ? earliest.at - game.state.worldTime : null);
  $('combatPrompt').textContent = c.hp <= 0 ? '人物已失去行动能力，可在演练场恢复生命。' : incoming ? '攻击即将到来：点击闪避，把握最后时刻可触发反击。' : game.counterAvailable ? '完美闪避！点击反击使对手眩晕。' : earliest ? `来袭攻击${remaining != null ? ` · ${number(Math.max(0,remaining),1)} 秒` : '已排入时间轴'}${game.timeScale === .5 ? ' · 当前半速' : ''}` : game.state.story ? '剧情场景中 · 思考已中断' : '';
}

function itemDescription(item) {
  if (item.description) return item.description;
  return {ITM_001:'爆炸中心 100 伤害 · 半径 5m · 延迟 3 秒',ITM_002:'恢复 30HP，解除流血 · 使用 3 秒',ITM_003:'伤害 5 · 有效射程 8m · 5 次使用',ITM_004:'恢复载具 150HP · 维修 8 秒',ITM_005:'削弱目标 40% 的护甲减伤效果',ITM_006:'护甲 100 · 吸收子弹 70% / 爆炸 40% / 近战 20%'}[item.parentId || item.id] || '';
}

function renderCrafting(stats) {
  const c = game.character;
  const isXia = c.id === 'CHR_003';
  $('craftingHelp').textContent = isXia ? `当前 ${number(c.skill.energy,1)} 点思考点数。开启思考积累点数，暂停后选择制造。配方按巧手灵心等级解锁。` : '制造书为夏晴专属。选择夏晴后可使用思考点数制造；其他人物可查看物品数据。';
  update('craftProgress', c.craft ? `<div class="craft-progress"><div class="progress-head"><span>正在制造 ${escape(itemById[c.craft.itemId]?.name || c.craft.itemId)}</span><span>${number(c.craft.remaining,1)} 秒</span></div>${meter(c.craft.duration - c.craft.remaining,c.craft.duration)}<button class="text-button" data-cancel-craft>取消制造并退回点数</button></div>` : '');
  const baseRecipes = RECIPES.filter(item => !item.parentId && !item.id.startsWith('ITM_005_'));
  const ammoRecipes = RECIPES.filter(item => item.parentId === 'ITM_005' || item.id.startsWith('ITM_005_'));
  const parent = itemById.ITM_005;
  const recipes = [...baseRecipes];
  if (ammoRecipes.length && parent && !recipes.some(item => item.id === 'ITM_005')) recipes.splice(Math.min(4,recipes.length),0,parent);
  // A recipe control is never replaced while the user is choosing an ammo variant.
  const signature = `${c.id}|${c.skillLevel}|${!!c.craft}|${!!c.use}|${!!c.skill.thinking}|${c.hp > 0}|${Math.floor(c.skill.energy)}`;
  if (signatures.get('recipes-state') !== signature) {
    const selectedAmmo = document.querySelector('[data-ammo-choice]')?.value;
    update('recipeList', recipes.map(item => {
      const unlocked = isXia && c.skillLevel >= item.level;
      const eligible = unlocked && c.skill.energy >= item.cost && !c.craft && !c.use && !c.skill.thinking && c.hp > 0;
      const buttonText = !isXia ? '夏晴专属' : !unlocked ? `${item.level} 级解锁` : c.craft ? '制造进行中' : c.skill.thinking ? '先暂停思考' : c.skill.energy < item.cost ? '思考点数不足' : '开始制造';
      const choices = item.id === 'ITM_005' ? `<select data-ammo-choice aria-label="选择穿甲弹类型">${ammoRecipes.map(variant => `<option value="${variant.id}">${escape(variant.name)} ×${variant.quantity}</option>`).join('')}</select>` : '';
      return `<article class="recipe"><div class="recipe-visual"><span class="mono">${item.id}</span><span class="recipe-symbol">${iconFor(item.id)}</span><span class="recipe-placeholder">资源待接入</span></div><div class="recipe-body"><div class="recipe-title"><h4>${escape(item.name)}</h4><span>LV ${item.level}</span></div><p>${escape(itemDescription(item))}</p><div class="recipe-meta"><span>◇ ${item.cost} 点</span><span>◷ ${item.duration} 秒</span></div>${choices}<button class="secondary" data-craft="${item.id}" ${eligible ? '' : 'disabled'}>${buttonText}</button></div></article>`;
    }).join(''));
    if (selectedAmmo && document.querySelector('[data-ammo-choice]')) document.querySelector('[data-ammo-choice]').value = selectedAmmo;
    signatures.set('recipes-state',signature);
  }
}

function renderInventory() {
  const c = game.character;
  const inventory = c.inventory || [];
  $('inventoryCount').textContent = String(inventory.reduce((n,stack) => n + stack.quantity,0));
  let contents = c.armor ? `<div class="equipped-armor"><span>${iconFor('ITM_006')} 躯干已装备 · 凯夫拉防弹衣</span><strong>护甲 ${number(c.armor.durability ?? c.armor.value)} / 100</strong></div>` : '';
  if (c.use) contents += `<div class="craft-progress"><div class="progress-head"><span>正在${c.use.itemId === 'ITM_004' ? '维修载具' : '使用物品'}</span><span>${number(c.use.remaining,1)} 秒</span></div><button class="text-button" data-interrupt-use>中断使用</button></div>`;
  contents += inventory.length ? inventory.map(stack => {
    const item = itemById[stack.itemId];
    if (!item) return '';
    const details = [`${item.id} · ×${stack.quantity}`];
    if (stack.charges != null) details.push(`电量 ${number(stack.charges)} / 100`);
    if (stack.durability != null) details.push(`耐久 ${number(stack.durability)} / 100`);
    const label = stack.itemId === 'ITM_006' ? '装备' : stack.itemId.startsWith('ITM_005') ? '装入弹药' : stack.itemId === 'ITM_001' ? '投掷' : stack.itemId === 'ITM_003' ? '电击' : stack.itemId === 'ITM_004' ? '维修' : '使用';
    return `<div class="inventory-row"><span class="inventory-icon">${iconFor(item.id)}</span><div class="inventory-main"><h4>${escape(item.name)}</h4><p>${escape(details.join(' · '))}</p></div><button class="secondary" data-use="${item.id}" data-uid="${escape(stack.uid)}" ${c.hp <= 0 || c.skill.thinking || c.use || c.craft ? 'disabled' : ''}>${label}</button></div>`;
  }).join('') : `<div class="empty-state"><span class="empty-icon">▱</span><h4>物品栏空空如也</h4><p>夏晴可通过制造书获得物品。<br>演练场也可发放指定编号的测试物品。</p></div>`;
  update('inventoryList', contents);
}

function renderRegistry() {
  const descriptions = {
    ITM_001:'中心伤害 100，直接命中 80。半径 5m，伤害随距离线性衰减至 0；延迟 3 秒引爆，最远投掷 25m。载具伤害 ×50%，每堆 5 个。',
    ITM_002:'恢复 30HP，解除流血。使用 3 秒、冷却 5 秒，可步行使用；每堆 10 个。',
    ITM_003:'伤害 5，射程 8m。轻型眩晕 5 秒，中型 2 秒，重型无效。间隔 2 秒；电量 100，每发耗电 20，不能充电，耗尽自动移除。每堆 1 把。',
    ITM_004:'恢复载具耐久 150HP，维修 8 秒，最远 2m；载具必须静止。可以中断，完成后消耗；每堆 5 个。',
    ITM_005:'削弱目标 40% 护甲减伤效果。基础伤害继承枪械；对无甲目标伤害不变。每批次选择一种：A 步枪 ×30 / B 手枪 ×20 / C 冲锋枪 ×50 / D 狙击枪 ×10 / E 霰弹枪 ×15。',
    ITM_006:'躯干护甲 100，重量 5kg，可维修。吸收子弹 70%、爆炸 40%、近战 20%；护甲耗尽后失去防护，溢出伤害直接扣生命。每堆 1 件。',
  };
  update('itemRegistry', ITEMS.filter(item => !item.parentId && !item.id.startsWith('ITM_005_')).map(item => `<article class="item-record"><strong><span class="mono">${item.id}</span> · ${escape(item.name)}</strong><p>制造等级 ${item.level} · 消耗 ${item.cost} 点 · ${item.duration} 秒<br>${descriptions[item.id] || escape(itemDescription(item))}</p></article>`).join(''));
}

function sandboxButton(action, title, subtitle, payload = {}) {
  return `<button data-perform="${action}" data-payload="${escape(JSON.stringify(payload))}">${title}<small>${subtitle}</small></button>`;
}

function renderSandbox() {
  update('sandboxControls', `<div class="sandbox-section"><h4>移动与恢复 <span>按真实事件累计 EXP</span></h4><div class="sandbox-grid">${sandboxButton('walk','步行 10m','思考时允许',{distance:10})}${sandboxButton('run','跑步 10m','体力 +5 EXP',{distance:10})}${sandboxButton('swim','游泳 10m','体力 +5 EXP',{distance:10})}${sandboxButton('jump','跳跃 1m','体力 +2 EXP',{distance:1})}${sandboxButton('climb','攀爬 1m','体力 +2 EXP',{distance:1})}${sandboxButton('heal','恢复 30HP','仅按实际恢复计 EXP',{amount:30})}${sandboxButton('rest','休息','恢复体力')}${sandboxButton('drive','驾驶 100m','驾驶 +10 EXP',{distance:100,moving:true})}${sandboxButton('drive','静止驾驶','不获取驾驶经验',{distance:100,moving:false})}</div></div><div class="sandbox-section"><h4>战斗与随机事件 <span>目标 UNT_001</span></h4><div class="inline-controls"><label>目标单位 <select id="targetClass"><option value="light">轻型</option><option value="medium">中型</option><option value="heavy">重型</option></select></label><label>来袭伤害 <select id="attackType"><option value="bullet">子弹</option><option value="explosion">爆炸</option><option value="melee">近战</option></select></label></div><div class="sandbox-grid">${sandboxButton('shoot','射击命中','基础伤害 20 · +5 EXP',{hit:true,damage:20})}${sandboxButton('shoot','射击未命中','每发 +5 EXP',{hit:false,damage:20})}${sandboxButton('melee','近战命中','基础伤害 10 · +20 EXP',{hit:true,damage:10})}${sandboxButton('melee','近战未命中','力量 +5 EXP',{hit:false,damage:10})}<button data-incoming>安排来袭攻击<small>2 秒后 · 20 基础伤害</small></button><button data-damage>立即受到 20 伤害<small>检验减伤与护甲</small></button></div><div class="inline-controls"><label>射击弹药 <select id="weaponAmmo"><option value="">普通弹药</option><option value="rifle">步枪穿甲弹</option><option value="pistol">手枪穿甲弹</option><option value="smg">冲锋枪穿甲弹</option><option value="sniper">狙击枪穿甲弹</option><option value="shotgun">霰弹枪穿甲弹</option></select></label><label>目标护甲 <select id="targetArmor"><option value="0">无护甲</option><option value="100">100 AP</option></select></label></div><div id="targetReadout" class="target-readout" aria-live="off"></div><div class="inline-controls"><button class="text-button" data-reset-target>重置演练目标</button></div></div><div class="sandbox-section"><h4>社交与普通制造</h4><div class="sandbox-grid">${sandboxButton('social','社交成功','魅力 +50 EXP',{success:true})}${sandboxButton('social','社交失败','魅力 +10 EXP',{success:false})}${sandboxButton('craft','制造成功','智力 +50 EXP',{success:true})}${sandboxButton('craft','制造失败','智力 +10 EXP',{success:false})}<button data-story class="story-button" aria-pressed="false">进入剧情<small>自动打断思考</small></button></div></div><div class="sandbox-section"><h4>物品使用条件 <span>载具 VEH_001</span></h4><div class="inline-controls"><label>目标距离 <select id="itemDistance"><option value="1">1m</option><option value="2">2m</option><option value="5">5m</option><option value="8">8m</option><option value="25">25m</option><option value="30">30m</option></select></label><label><input id="vehicleMoving" type="checkbox">载具运动</label><label><input id="directHit" type="checkbox">炸弹直接命中</label><label>距爆心 <select id="blastDistance"><option value="0">0m</option><option value="2.5">2.5m</option><option value="5">5m</option><option value="6">6m</option></select></label><label><input id="bombVehicle" type="checkbox">炸弹目标为载具</label></div><div id="vehicleReadout" class="target-readout"></div><p class="muted">物品在物品栏使用，上述距离与单位类型作为演练条件。维修需车辆静止且距离不超过 2m。</p></div><div class="sandbox-section"><h4>编号物品待命 <span>演练用物资发放</span></h4><div class="inline-controls"><label>物品编号 <select id="supplyItem">${ITEMS.filter(item => item.id !== 'ITM_005').map(item => `<option value="${item.id}">${item.id} · ${escape(item.name)}</option>`).join('')}</select></label><button class="secondary" data-supply>发放 1 件 / 1 批</button></div><p class="muted">发放入口用于验证缺少模型的物品效果，不属于正式获取渠道。制造书中的成品需要实际消耗点数和时间。</p></div>`);
}

function renderSandboxLive() {
  const target = game.state.target;
  const vehicle = game.state.vehicle;
  const c = game.character;
  if ($('targetReadout')) update('targetReadout', `目标生命 ${number(target.hp)} / ${number(target.maxHp)} · 眩晕 ${number(target.stun,1)} 秒 · 普通弹药 ${number(c.ammo)} · 目标护甲 ${number(target.armor)}<br>穿甲弹：步枪 ${c.ammoPools?.rifle || 0} / 手枪 ${c.ammoPools?.pistol || 0} / 冲锋枪 ${c.ammoPools?.smg || 0} / 狙击枪 ${c.ammoPools?.sniper || 0} / 霰弹枪 ${c.ammoPools?.shotgun || 0}<br>世界时间 ${number(game.state.worldTime,1)}s · 时间流速 ${number(game.timeScale,1)}×${c.bleeding ? ' · 流血中' : ''}${c.bandageCooldown > 0 ? ` · 绷带冷却 ${number(c.bandageCooldown,1)}s` : ''}`);
  if ($('vehicleReadout')) update('vehicleReadout', `载具耐久 ${number(vehicle.hp)} / ${number(vehicle.maxHp)} · ${vehicle.moving ? '运动中' : '静止'} · 累计驾驶 ${number(c.distance?.drive || 0,1)}m`);
  const story = document.querySelector('[data-story]');
  if (story) {story.setAttribute('aria-pressed',String(game.state.story)); story.innerHTML = `${game.state.story ? '离开剧情' : '进入剧情'}<small>自动打断思考</small>`;}
  document.querySelectorAll('[data-perform]').forEach(button => {
    button.disabled = !!c.skill.thinking && button.dataset.perform !== 'walk';
  });
  const checkbox = $('vehicleMoving');
  if (checkbox && document.activeElement !== checkbox) checkbox.checked = !!vehicle.moving;
  const logs = game.state.log || [];
  update('eventLog', logs.slice(0,12).map(entry => `<li><time>${number(entry.time,1)}s</time><span>${escape(entry.text)}</span></li>`).join(''));
}

function sendFrameState() {
  const c = game.character;
  const hidden = c.id !== 'CHR_003';
  const state = {type:'hero13-state',timeScale:hidden ? 0 : game.timeScale,moveMultiplier:game.stats().moveMultiplier,allowRun:!c.skill.thinking && !c.use,blocked:hidden || game.state.story || c.hp <= 0 || !!c.craft, ...(c.skill.thinking || c.use ? {action:'Walk'} : {})};
  const serialized = JSON.stringify(state);
  if (serialized !== lastFrameMessage) {
    $('characterFrame').contentWindow?.postMessage(state,location.origin);
    lastFrameMessage = serialized;
  }
}

function render() {
  if (!game.character || !game.definition) return;
  if (previousCharacter !== game.definition.id) characterChanged();
  update('characterPicker', CHARACTERS.map((character,index) => `<button class="character-choice" data-character="${character.id}" aria-pressed="${game.definition.id === character.id}"><span class="choice-number">0${index + 1}</span><span><span class="choice-name">${escape(character.name)}</span><span class="choice-role">${escape(character.role)}</span></span><span class="choice-indicator" aria-hidden="true"></span></button>`).join(''));
  const stats = game.stats();
  $('inventoryCount').textContent = String((game.character.inventory || []).reduce((sum,stack) => sum + stack.quantity,0));
  renderVitals(stats);
  renderSkill(stats);
  if (currentTab === 'attributes') renderAttributes(stats);
  if (currentTab === 'crafting') renderCrafting(stats);
  if (currentTab === 'inventory') {renderInventory(); renderRegistry();}
  if (currentTab === 'sandbox') renderSandboxLive();
  $('skillLevel').value = String(game.character.skillLevel);
  sendFrameState();
}

$('characterPicker').addEventListener('click', event => {
  const button = event.target.closest('[data-character]');
  if (button) command(() => game.setCharacter(button.dataset.character));
});
$('activateSkill').addEventListener('click', () => command(() => game.activateSkill()));
$('thinkButton').addEventListener('click', () => command(() => game.toggleThinking()));
$('dodgeButton').addEventListener('click', () => command(() => game.dodge()));
$('counterButton').addEventListener('click', () => command(() => game.counter()));
$('skillLevel').addEventListener('change', event => command(() => game.setSkillLevel(Number(event.target.value))));
$('resetGame').addEventListener('click', () => {
  if (!confirm('重置三名人物的属性、技能与物品栏存档？此操作无法撤销。')) return;
  command(() => {game.reset(); previousCharacter = null; return {ok:true,message:'全部人物档案已重置。'};});
});
$('recipeList').addEventListener('click', event => {
  const button = event.target.closest('[data-craft]');
  if (!button || button.disabled) return;
  const id = button.dataset.craft === 'ITM_005' ? document.querySelector('[data-ammo-choice]')?.value : button.dataset.craft;
  command(() => game.startCraft(id));
});
$('craftProgress').addEventListener('click', event => {if (event.target.closest('[data-cancel-craft]')) command(() => game.cancelCraft());});
$('inventoryList').addEventListener('click', event => {
  if (event.target.closest('[data-interrupt-use]')) {command(() => game.interruptUse()); return;}
  const button = event.target.closest('[data-use]');
  if (!button) return;
  const options = {uid:button.dataset.uid,distance:Number($('itemDistance')?.value || 1),unitClass:$('targetClass')?.value || 'light',directHit:!!$('directHit')?.checked,blastDistance:Number($('blastDistance')?.value || 0),vehicle:!!$('bombVehicle')?.checked};
  command(() => game.useItem(button.dataset.use,options));
});
$('sandboxControls').addEventListener('change', event => {
  if (event.target.id === 'vehicleMoving') game.state.vehicle.moving = event.target.checked;
  if (event.target.id === 'targetClass') game.state.target.type = event.target.value;
  if (event.target.id === 'targetArmor') game.state.target.armor = Number(event.target.value);
  render(); save();
});
$('sandboxControls').addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.perform) {
    const payload = JSON.parse(button.dataset.payload || '{}');
    if (button.dataset.perform === 'shoot') payload.ammoType = $('weaponAmmo').value || null;
    command(() => game.perform(button.dataset.perform,payload));
  }
  else if (button.hasAttribute('data-incoming')) command(() => game.queueAttack({damage:20,type:$('attackType').value,delay:2,unitClass:$('targetClass').value}));
  else if (button.hasAttribute('data-damage')) command(() => game.receiveAttack({damage:20,type:$('attackType').value}));
  else if (button.hasAttribute('data-story')) command(() => game.enterStory(!game.state.story));
  else if (button.hasAttribute('data-supply')) {
    const item = itemById[$('supplyItem').value];
    command(() => game.giveItem(item.id,item.quantity || 1));
  } else if (button.hasAttribute('data-reset-target')) command(() => {
    const target = game.state.target;
    target.hp = target.maxHp; target.stun = 0;
    return {ok:true,message:'演练目标已复位。'};
  });
});

window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== $('characterFrame').contentWindow) return;
  const message = event.data;
  if (['hero13-ready','hero13-scene-ready'].includes(message?.type)) {lastFrameMessage = ''; sendFrameState(); return;}
  if (message?.type !== 'hero13-motion' || game.character.id !== 'CHR_003' || !['run','walk'].includes(message.action)) return;
  if (!Number.isFinite(message.distance) || message.distance <= 0 || message.distance > 10) return;
  command(() => game.perform(message.action,{distance:message.distance}),{silent:true});
});
$('characterFrame').addEventListener('load', () => {lastFrameMessage = ''; sendFrameState();});
window.addEventListener('pagehide',save);
document.addEventListener('visibilitychange', () => {if (document.hidden) save();});

let previousTime = performance.now();
let renderAccumulator = 0;
let saveAccumulator = 0;
function frame(now) {
  const dt = Math.min((now - previousTime) / 1000,.25);
  previousTime = now;
  if (!document.hidden) {
    game.tick(dt);
    renderAccumulator += dt;
    saveAccumulator += dt;
    if (renderAccumulator >= 1 / 20) {renderAccumulator = 0; render();}
    if (saveAccumulator >= 5) {saveAccumulator = 0; save();}
  }
  requestAnimationFrame(frame);
}
render();
if (restoring) $('saveState').innerHTML = '<i></i>已载入本机存档';
requestAnimationFrame(frame);
