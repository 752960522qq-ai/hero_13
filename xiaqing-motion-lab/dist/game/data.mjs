// HERO 13 · authoritative v1 data. Missing assets stay null for later replacement.
// Percentages are fractions of the level-zero base; levels never compound them.
function freeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

export const RULES = freeze({
  version: 1,
  baseHealth: 100, healthPerLevel: 20,
  baseStamina: 100, staminaPerLevel: 20,
  attributeExp: [1000, 1500, 2500, 5000, 10000, 18000],
  defaultAttributeCap: 5, luoAttributeCap: 6,
  defaultSkillCap: 5, luoSkillCap: 6,
  luoLevelSixExp: 18000,
  luoGrowthMultiplier: null,
  skillUpgradeMethod: null,
  percentMode: 'additive-from-level-zero',
  luckMode: 'multiplicative',
  xp: {
    heal: 3,
    run: { distance: 10, exp: 5 }, swim: { distance: 10, exp: 5 },
    jump: { distance: 1, exp: 2 }, climb: { distance: 1, exp: 2 },
    shoot: 5, drive: { distance: 100, exp: 10 },
    meleeMiss: 5, meleeHit: 20,
    socialSuccess: 50, socialFailure: 10,
    craftSuccess: 50, craftFailure: 10,
  },
  bonuses: {
    move: 0.04, stability: 0.06, reload: 0.05,
    handling: 0.03, vehicleSpeed: 0.02,
    meleeDamage: 0.12, meleeSpeed: 0.03,
    social: 0.05, craftSpeed: 0.06, craftWasteReduction: 0.06,
    positiveChance: 0.06, negativeChanceReduction: 0.05,
  },
  skills: {
    SKL_001: {
      id: 'SKL_001', name: '完美身法', owner: 'CHR_001',
      timeScale: 0.5, rechargeSeconds: 120,
      baseDuration: 6, durationPerLevel: 2,
      baseDodgeChance: 0.14, dodgeChancePerLevel: 0.10,
      baseDodgeWindow: 0.4, dodgeWindowPerLevel: 0.1,
      baseCounterWindow: 0.1, counterWindowPerLevel: 0.05,
      counterDamage: 30, stun: { light: 5, medium: 3, heavy: 1 },
      toggle: true, resource: 'energy',
    },
    SKL_002: {
      id: 'SKL_002', name: '杀神本能', owner: 'CHR_002',
      baseDamageReduction: 0.30, damageReductionPerLevel: 0.10,
      baseMeleeBonus: 0.20, meleeBonusPerLevel: 0.05,
      baseShootingBonus: 0.10, shootingBonusPerLevel: 0.02,
      baseDuration: 8, durationPerLevel: 1,
      cooldownSeconds: 100, unlimitedAmmo: true,
    },
    SKL_003: {
      id: 'SKL_003', name: '巧手灵心', owner: 'CHR_003',
      baseCapacity: 100, capacityPerLevel: 0.15,
      baseRechargeSeconds: 90, rechargeRatePerLevel: 0.10,
      allowedThinkingActions: ['walk'],
      interruptThinkingOnStory: true,
      bookReceivesIntelligenceBonus: false,
    },
  },
  pending: [
    { id: 'LUO_GROWTH', text: '罗甄成长速度最快的具体倍率尚待设定；暂使用共同经验表，不擅自添加倍率。' },
    { id: 'SKILL_UPGRADE', text: '专属技能升级获取方式尚待设定；原型配置可手动预览各等级。' },
    { id: 'SKILL_RANGE', text: '专属技能等级暂按 0—5 级、罗甄 0—6 级实现，等待确认“五级”的范围。' },
  ],
});

const expThresholds = [1000, 1500, 2500, 5000, 10000];
export const ATTRIBUTES = freeze([
  { id: 'health', name: '生命', icon: '♡', expThresholds: [...expThresholds], description: '0 级生命上限 100，每级 +20；每实际恢复 1HP 获得 3EXP。', bonus: { maxHp: 20 }, trainable: true },
  { id: 'stamina', name: '体力', icon: '↗', expThresholds: [...expThresholds], description: '0 级体力上限 100，每级 +20；移动速度每级 +4%。跑步/游泳每 10m +5EXP，跳跃/攀爬每 1m +2EXP。', bonus: { maxStamina: 20, move: 0.04 }, trainable: true },
  { id: 'shooting', name: '射击', icon: '⊕', expThresholds: [...expThresholds], description: '射击稳定性每级 +6%，换弹速度每级 +5%；每发射一发子弹 +5EXP。', bonus: { stability: 0.06, reload: 0.05 }, trainable: true },
  { id: 'driving', name: '驾驶', icon: '⌁', expThresholds: [...expThresholds], description: '驾驶操纵性每级 +3%，载具最高速度每级 +2%；车辆运动时每驾驶 100m +10EXP。', bonus: { handling: 0.03, vehicleSpeed: 0.02 }, trainable: true },
  { id: 'strength', name: '力量', icon: '◇', expThresholds: [...expThresholds], description: '近战伤害每级 +12%，近战速度每级 +3%；攻击未命中 +5EXP，命中 +20EXP。', bonus: { meleeDamage: 0.12, meleeSpeed: 0.03 }, trainable: true },
  { id: 'charm', name: '魅力', icon: '✧', expThresholds: [...expThresholds], description: '社交加成每级 +5%；成功社交 +50EXP，失败 +10EXP。', bonus: { social: 0.05 }, trainable: true },
  { id: 'intelligence', name: '智力', icon: '⌘', expThresholds: [...expThresholds], description: '制造速度每级 +6%，制造损耗每级 −6%；普通制造成功 +50EXP、失败 +10EXP。制造书不受智力加成。', bonus: { craftSpeed: 0.06, craftWasteReduction: 0.06 }, trainable: true },
  { id: 'luck', name: '运气', icon: '♧', expThresholds: [], description: '正向随机事件概率每级 +6%，负向随机事件概率每级 −5%，均乘初始概率。运气固定，不可升级。', bonus: { positiveChance: 0.06, negativeChanceReduction: 0.05 }, trainable: false },
]);

export const CHARACTERS = freeze([
  {
    id: 'CHR_001', name: '罗甄', role: '狱警',
    description: '初始数值较平庸，成长上限最高、成长速度最快，运气最好。具体成长速度倍率待设定。',
    skillId: 'SKL_001', skillName: '完美身法',
    initialLevels: { health: 1, stamina: 1, shooting: 1, driving: 1, strength: 1, charm: 1, intelligence: 2, luck: 6 },
    attributeCap: 6, skillCap: 6, growthMultiplier: null,
    model: null, assetId: 'CHR_001_MODEL', assetStatus: 'pending',
  },
  {
    id: 'CHR_002', name: '徐哲', role: '维和老兵',
    description: '初始武力值最高。专属技能提升生存与进攻能力，持续期间射击不消耗子弹。',
    skillId: 'SKL_002', skillName: '杀神本能',
    initialLevels: { health: 3, stamina: 3, shooting: 4, driving: 3, strength: 4, charm: 0, intelligence: 1, luck: 1 },
    attributeCap: 5, skillCap: 5, growthMultiplier: 1,
    model: null, assetId: 'CHR_002_MODEL', assetStatus: 'pending',
  },
  {
    id: 'CHR_003', name: '夏晴', role: '工程师', identity: '跨性别女性',
    description: '跨性别女性，工程师。初始魅力与智力最高，善于思考和制造。',
    skillId: 'SKL_003', skillName: '巧手灵心',
    initialLevels: { health: 1, stamina: 0, shooting: 0, driving: 2, strength: 0, charm: 4, intelligence: 4, luck: 3 },
    attributeCap: 5, skillCap: 5, growthMultiplier: 1,
    model: './assets/xiaqing_native_animated.glb?v=6.3', assetId: 'CHR_003_MODEL', assetStatus: 'ready',
  },
]);

const pendingAsset = { model: null, icon: null, assetStatus: 'pending' };
const ammunition = {
  ...pendingAsset, type: '特殊弹药', level: 2, cost: 15, duration: 5,
  // A batch's quantity is defined; no maximum inventory stack was supplied.
  stack: null, armorReductionIgnore: 0.4, baseDamage: 'weapon',
  noArmorDamageMultiplier: 1, parentId: 'ITM_005',
};
export const ITEMS = freeze([
  {
    ...pendingAsset, id: 'ITM_001', assetId: 'ITM_001_MODEL', name: '土制炸弹', type: '投掷消耗品',
    level: 0, cost: 20, duration: 6, stack: 5,
    damage: 100, directHitDamage: 80, radius: 5, falloff: 'linear-to-zero',
    fuse: 3, range: 25, vehicleDamageMultiplier: 0.5,
    description: '爆炸中心 100 伤害，直接命中 80；半径 5m，随距离线性衰减至 0。引爆延迟 3 秒，最远投掷 25m，对载具伤害为 50%。',
  },
  {
    ...pendingAsset, id: 'ITM_002', assetId: 'ITM_002_MODEL', name: '简易绷带', type: '医疗消耗品',
    level: 0, cost: 15, duration: 5, stack: 10,
    heal: 30, useDuration: 3, cooldown: 5, clearsBleeding: true, allowedMovement: ['walk'],
    description: '使用 3 秒后恢复 30HP 并解除流血，使用冷却 5 秒；使用时允许步行。',
  },
  {
    ...pendingAsset, id: 'ITM_003', assetId: 'ITM_003_MODEL', name: '简易泰瑟枪', type: '一次性非致命武器',
    level: 1, cost: 30, duration: 15, stack: 1,
    damage: 5, range: 8, uses: 5, stun: { light: 5, medium: 2, heavy: 0 },
    shotInterval: 2, maxEnergy: 100, energyPerShot: 20, rechargeable: false, autoDisposeEmpty: true,
    description: '射程 8m、伤害 5，轻型眩晕 5 秒、中型 2 秒、重型无效。射击间隔 2 秒；电量 100，每发耗电 20，共 5 次，耗尽自动报废。',
  },
  {
    ...pendingAsset, id: 'ITM_004', assetId: 'ITM_004_MODEL', name: '维修工具', type: '维修消耗品',
    level: 1, cost: 30, duration: 15, stack: 5,
    repair: 150, useDuration: 8, range: 2, requiresStationary: true,
    interruptible: true, consumeOnComplete: true,
    description: '距离 2m 内维修静止载具，耗时 8 秒、恢复 150HP。允许中断，完成后才消耗物品。',
  },
  {
    ...pendingAsset, id: 'ITM_005', assetId: 'ITM_005_MODEL', name: '钨钢穿甲弹', type: '特殊弹药',
    level: 2, cost: 15, duration: 5, stack: null, craftable: false,
    armorReductionIgnore: 0.4, baseDamage: 'weapon', noArmorDamageMultiplier: 1,
    variants: ['ITM_005_A', 'ITM_005_B', 'ITM_005_C', 'ITM_005_D', 'ITM_005_E'],
    description: '削弱目标 40% 的护甲减伤效果，伤害继承枪械，对无甲目标伤害不变。每次制造只选择一种弹药：步枪×30、手枪×20、冲锋枪×50、狙击枪×10、霰弹枪×15。',
  },
  { ...ammunition, id: 'ITM_005_A', assetId: 'ITM_005_A_MODEL', name: '步枪穿甲弹', ammoType: 'rifle', quantity: 30, description: '每批 30 发；削弱护甲减伤效果 40%，基础伤害继承步枪。' },
  { ...ammunition, id: 'ITM_005_B', assetId: 'ITM_005_B_MODEL', name: '手枪穿甲弹', ammoType: 'pistol', quantity: 20, description: '每批 20 发；削弱护甲减伤效果 40%，基础伤害继承手枪。' },
  { ...ammunition, id: 'ITM_005_C', assetId: 'ITM_005_C_MODEL', name: '冲锋枪穿甲弹', ammoType: 'smg', quantity: 50, description: '每批 50 发；削弱护甲减伤效果 40%，基础伤害继承冲锋枪。' },
  { ...ammunition, id: 'ITM_005_D', assetId: 'ITM_005_D_MODEL', name: '狙击枪穿甲弹', ammoType: 'sniper', quantity: 10, description: '每批 10 发；削弱护甲减伤效果 40%，基础伤害继承狙击枪。' },
  { ...ammunition, id: 'ITM_005_E', assetId: 'ITM_005_E_MODEL', name: '霰弹枪穿甲弹', ammoType: 'shotgun', quantity: 15, description: '每批 15 发；削弱护甲减伤效果 40%，基础伤害继承霰弹枪。' },
  {
    ...pendingAsset, id: 'ITM_006', assetId: 'ITM_006_MODEL', name: '凯夫拉防弹衣', type: '身体护甲',
    level: 2, cost: 50, duration: 15, stack: 1,
    maxArmor: 100, absorption: { bullet: 0.70, explosion: 0.40, melee: 0.20 },
    slot: 'torso', weight: 5, repairable: true,
    description: '躯干护甲，护甲值 100、重量 5kg；吸收子弹 70%、爆炸 40%、近战 20%。可维修，护甲耗尽后失去防护，剩余伤害作用于生命。',
  },
]);

export const RECIPES = freeze(ITEMS.filter(item => item.id !== 'ITM_005'));
export const SKILLS = freeze(Object.values(RULES.skills));

// Stable hooks for a later resource importer. No stand-in pretends to be a finished asset.
export const ASSETS = freeze([
  ...CHARACTERS.map(character => ({ id: character.assetId, ownerId: character.id, kind: 'character', path: character.model, status: character.assetStatus })),
  ...ITEMS.map(item => ({ id: item.assetId, ownerId: item.id, kind: 'item', path: item.model, status: item.assetStatus })),
]);
