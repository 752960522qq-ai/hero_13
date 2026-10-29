"""Package only actually changed district GLBs plus their audit and source metadata."""
from pathlib import Path
import json,gzip,hashlib,lzma,shutil,collections,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];OLD=Path('/workspace/scratch/705f52588668/work_v14');STAGE=ROOT/'repository_stage';PREFIX=Path('delivery/city_updates/v15_20261029');OUT=STAGE/PREFIX;OUT.mkdir(parents=True,exist_ok=True);(OUT/'districts').mkdir(exist_ok=True)
manifest=json.load(open(ROOT/'districts/districts_manifest.json'));base=json.load(open(OLD/'districts/districts_manifest.json'));plan=json.load(open(ROOT/'model/city_plan.json'));build=json.load(open(ROOT/'model/v15_build_report.json'));native=json.load(open(ROOT/'validation/native_validation.json'));assert native['status']=='PASS'
def hashfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def zone(xy,reg):
    x,y=xy
    if reg=='MAIN':return 1+sum(x>=v for v in [-500,0,500])+4*(y>=620)
    if reg=='WEST':return 9+(x>=-950)+2*(y>=-720)
    return 13+(x>=750)+2*(y>=-800)
prior_plan=json.load(open(OLD/'model/city_plan.json'))
def count(p):return collections.Counter(zone(b['center'],b.get('region','MAIN')) for b in p['buildings']+p['real_buildings'])
before=count(prior_plan);after=count(plan);lifts=collections.defaultdict(list);moves=collections.defaultdict(list)
byname={b.get('name',b.get('instance_name')):b for b in plan['buildings']+plan['real_buildings']}
for r in build['ground_corrections']:lifts[zone(byname[r['name']]['center'],byname[r['name']].get('region','MAIN'))].append(r['name'])
for r in build['moved_buildings']:
    n=r['name'];reg=byname[n].get('region','MAIN')
    for d in set([zone(r['old_center'],reg),zone(r['new_center'],reg)]):moves[d].append(n)
def pack(d):
    source=ROOT/'districts'/d['file'];compressed=ROOT/(d['file']+'.xz')
    if not compressed.exists():
        with source.open('rb') as src,lzma.open(compressed,'wb',preset=3) as dst:shutil.copyfileobj(src,dst,1048576)
    parts=[]
    with compressed.open('rb') as src:
        i=0
        while True:
            data=src.read(8*1048576)
            if not data:break
            name='districts/'+compressed.name+f'.part{i:03d}';dest=OUT/name;dest.write_bytes(data);parts.append({'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()});i+=1
    notes=[]
    if moves[d['id']]:notes.append('集中 CBD／内移市政区及迁出旧址复原：'+', '.join(moves[d['id']]))
    if lifts[d['id']]:notes.append('修正建筑下陷：'+', '.join(lifts[d['id']]))
    if not notes:notes.append('相邻场地、入口和地形接缝同步调整。')
    out={'id':d['id'],'name':d['name'],'file':d['file'],'bytes':d['file_size_bytes'],'sha256':d['sha256'],'base_sha256':base['districts'][d['id']-1]['sha256'],'compression':'xz','compressed_bytes':compressed.stat().st_size,'compressed_sha256':hashfile(compressed),'parts':parts,'building_units_before':before[d['id']],'building_units_after':after[d['id']],'change_notes':'\n'.join(notes)}
    print('PACKED',d['id'],len(parts),out['compressed_bytes'],flush=True);return out
changed_ids=manifest['exported_district_ids']
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:changed=list(pool.map(pack,[d for d in manifest['districts'] if d['id'] in changed_ids]))
all_districts=[dict(d,base_sha256=base['districts'][d['id']-1]['sha256']) for d in manifest['districts']]
update={'schema':'hero13.city.district-update.v1','update_id':'v15_20261029','date':'2026-10-29','baseline_version':'v14','baseline_commit':'c8f042ef1378a2f140d479eb46e6b2c9e9db2deb','depends_on_updates':['v14_20261029'],'changed_district_ids':changed_ids,'unchanged_district_ids':manifest['reused_district_ids'],'changed_districts':changed,'all_districts':all_districts,'resolved_districts_manifest':manifest,'units':'metres','placement':manifest['placement']}
(OUT/'manifest.json').write_text(json.dumps(update,ensure_ascii=False,indent=2))
src=(OLD/'release/delivery/city_updates/v14_20261029/reassemble.py').read_text().replace('v13','v14').replace('v14 set','v15 set').replace('these six matching districts','the changed matching districts')
(OUT/'reassemble.py').write_text(src)
for sub in ['tools','validation','metadata','previews']:(OUT/sub).mkdir(exist_ok=True)
for src in (ROOT/'tools').glob('*.py'):
    if src.name not in ['probe_access.py']:shutil.copy2(src,OUT/'tools'/src.name)
for src in (ROOT/'validation').glob('*.json'):shutil.copy2(src,OUT/'validation'/src.name)
for src in (ROOT/'previews').glob('*.png'):shutil.copy2(src,OUT/'previews'/src.name)
for n in ['v15_build_report.json','v15_finish_report.json','building_registry.csv','tianming_reservation.json']:shutil.copy2(ROOT/'model'/n,OUT/'metadata'/n)
for n in ['layout.json','ground_audit_before.json','access_profile_policy.json']:shutil.copy2(ROOT/n,OUT/'metadata'/n)
(OUT/'metadata/city_plan.json.gz').write_bytes(gzip.compress((ROOT/'model/city_plan.json').read_bytes(),mtime=0))
summary=f'''# 城市 v15：收紧 CBD、内移市政区、修复建筑下陷

基准：v14，提交 `c8f042ef1378a2f140d479eb46e6b2c9e9db2deb`。依赖先取得 v13，再应用 v14。本次仅替换区块 {', '.join(f'{i:02d}' for i in changed_ids)}；其余区块校验值不变。

- CBD 建筑向中央立交四周集中；规划边界从 365,500 m² 收紧到 255,254 m²（约缩小 30%）。建筑实际分布凸包从 {native['cbd_footprint_hull_before_m2']:.0f} m² 减为 {native['cbd_footprint_hull_after_m2']:.0f} m²。
- 原误放公寓区的 A32、A35 写字楼移入 CBD。CBD 现有 31 座；天明大厦 172×195 m 预留地及入口完整保留，未来合计 32 座。没有新增或重复建筑，全城仍为 664 座、净陆地 3.25 km²。
- 市政主楼和九栋配套占位楼集中到内陆街块；平均距岸线从 {native['municipal_shore_distance_before_mean_m']:.0f} m 增至 {native['municipal_shore_distance_after_mean_m']:.0f} m，保留主楼前庭空间。
- 修正 {len(build['ground_corrections'])} 栋占位楼下陷；重做迁移楼宇的基础、首层场地和入口，迁出旧址补回地面。源素材网格、贴图、建筑高度及道路网络保持原样。

## 区块替换

先准备一套校验通过的完整 v14 区块目录，然后运行：

```bash
python3 reassemble.py --baseline-dir /path/to/v14/districts --out /path/to/v15/districts
```

脚本会校验完整 v14 基准、每个分卷、压缩文件和 GLB；只重组这次修改的区块，其余复制基准。保留原世界坐标，导入根位置/旋转为 0、缩放为 1，移除旧的对应区块后再导入新版。不要叠加加载旧版区块和新版区块。

每个区块的新旧 SHA256、建筑数量变化和改动备注见 `manifest.json`。模型图见 `previews/`，几何验证见 `validation/`，可复现脚本及精确布局见 `tools/` 和 `metadata/`。静态模型已检查；没有宣称游戏碰撞、导航、交通或帧率已集成。
'''
(OUT/'README.md').write_text(summary)
(OUT/'REPRODUCE.md').write_text('先按 v14 REPRODUCE.md 恢复原生场景。将 metadata/layout.json、ground_audit_before.json、access_profile_policy.json 放到工作目录根部。依次执行 tools/build_city_v15.py、finish_city_v15.py、validate_city_v15.py（生成中间检查记录），再执行 rebuild_access_v15.py、finish_city_v15.py、validate_city_v15.py 完成入口分段和最终检查。最后执行 export_city_incremental_blender.py、validate_city_districts_blender.py。修改脚本内 BASE/ROOT/依赖目录指向恢复的位置。交付的 GLB 可直接重组，不要求重新执行 Blender。\n')
current=json.load(open(OLD/'repository_stage/design/city/districts/current_sources_v14.json'))
for d in current:
    row=manifest['districts'][d['id']-1];d['building_units']=after[d['id']]
    if d['id'] in changed_ids:d.update(version='v15',bytes=row['file_size_bytes'],sha256=row['sha256'],source={'type':'incremental_district_parts','manifest':str(PREFIX/'manifest.json')})
design=STAGE/'design/city';(design/'districts').mkdir(parents=True,exist_ok=True);(design/'v15').mkdir(exist_ok=True)
(design/'districts/current_sources_v15.json').write_text(json.dumps(current,ensure_ascii=False,indent=2))
for n in ['districts_manifest.json','partition_audit.json.gz']:shutil.copy2(ROOT/'districts'/n,design/'districts'/n)
shutil.copy2(ROOT/'validation/districts_validation.json',design/'districts/districts_validation.json');shutil.copy2(ROOT/'model/city_plan.json',design/'city_plan.json');(design/'city_plan.json.gz').write_bytes(gzip.compress((ROOT/'model/city_plan.json').read_bytes(),mtime=0))
(design/'v15/README.md').write_text(summary)
for n in ['v15_build_report.json','v15_finish_report.json','building_registry.csv']:shutil.copy2(ROOT/'model'/n,design/'v15'/n)
for n in ['assets/city/README.md','delivery/city_updates/README.md','design/city/districts/README.md']:
    olddoc=(OLD/'repository_stage'/n).read_text();dest=STAGE/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('> 最新增量为 **v15**：收紧 CBD、内移市政区、修复建筑下陷，误放公寓区的两栋写字楼改归 CBD。只替换实际变动区块；详见 `delivery/city_updates/v15_20261029/README.md`，当前来源清单为 `design/city/districts/current_sources_v15.json`。\n\n'+olddoc)
items=[]
for f in sorted(STAGE.rglob('*')):
    if not f.is_file():continue
    data=f.read_bytes();items.append({'repo_path':str(f.relative_to(STAGE)),'local_path':str(f),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
(ROOT/'repository_upload_items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2));print('PACKAGE_READY',len(items),sum(x['bytes'] for x in items),flush=True)
