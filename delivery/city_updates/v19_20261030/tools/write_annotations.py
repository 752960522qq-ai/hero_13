from pathlib import Path
import json,csv,collections
R=Path(__file__).resolve().parents[1];layout=json.load(open(R/'layout.json'));catalog=json.load(open(R/'asset_catalog.json'));instances=layout['placements'];used=collections.Counter(b['asset_id'] for b in instances)
for a in catalog:
 a['map_instance_count']=used[a['asset_id']];a['instance_ids']=[b['instance_id'] for b in instances if b['asset_id']==a['asset_id']];a['district_ids']=sorted({b['district_id'] for b in instances if b['asset_id']==a['asset_id']})
 if a['status']!='rejected_black_source_albedo':a['status']='placed_v19' if used[a['asset_id']] else 'reserve_not_placed'
(R/'asset_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2));out=R/'annotations';out.mkdir(exist_ok=True)
fields=['模型编号','建筑名称','来源文件','原节点名称','分割文件','落位数量','地图实例编号','区块','状态','贴图处理']
with (out/'building_asset_catalog.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(fields)
 for a in catalog:w.writerow([a['asset_id'],a['display_name_zh'],a['source_filename'],a['source_node_name'],a['file'] if not a['status'].startswith('rejected') else '不交付为可用模型',a['map_instance_count'],' | '.join(a['instance_ids']),','.join(map(str,a['district_ids'])),{'placed_v19':'已落位','reserve_not_placed':'可用备用；未落位','rejected_black_source_albedo':'未采用；源贴图纯黑'}[a['status']],'AI 细节增强' if a.get('enhancement') else '保留原贴图'])
with (out/'building_map_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['地图实例编号','模型编号','建筑名称','来源文件','原节点','布局组团','区块','替换的旧建筑','X米','Y米','高度米','旋转度','统一缩放','新增/替换'])
 for b in instances:w.writerow([b['instance_id'],b['asset_id'],b['display_name_zh'],b['source_filename'],b['source_node_name'],b['group'],b['district_id'],' | '.join(b['replaces']),*b['center'],b['height'],b['rotation_deg'],b['scale'],'替换' if b['replaces'] else '新增'])
sources=json.load(open(R/'audit/sources.json'));decisions={
 'S01':'整城按材质合批，单独取一组会丢失玻璃和广告等部件；本轮不强行裁切。参考高低楼错落，保留当前 CBD 数量。',
 'S02':'分离 5 种完整亚洲建筑，保留门窗、雨棚、空调和屋顶设备；用于商住街坊和花园巷。',
 'S03':'分离 6 种商务楼；4 种落入新城商务步行组团，2 种大体量高楼备用。',
 'S04':'分离 10 种店铺、住宅、诊所和厂房，全部使用。4 种模型共用的紧凑贴图做 AI 细节增强；几何和 UV 保留。',
 'S05':'楼高递进和街角围合可参考；大部分贴图仅 64～256 像素，不作为本轮近景建筑。',
 'S06':'分离 6 组建筑；其中 5 种完整砖石街面楼使用，1 种铸铁楼的原始颜色图为纯黑，明确排除。借鉴连续街墙与内部庭院。',
 'S07':'参考细巷、街口和高低楼混合；低分辨率贴图不作为本轮近景素材。',
 'S08':'多处是单面照片立面、黑色背板或未封闭框架，不作为完整可绕行房屋直接放入地图。',
 'S09':'房屋与整片街区按材质合并，且含独立光照叠层；本轮参考空间层次，避免把叠层或道路误拆成房屋。'}
for s in sources:s['decision_zh']=decisions[s['id']]
(out/'source_audit.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
lines=['# v19 房屋来源与落位标注','','本轮从九份输入中筛选完整建筑。共分离 26 种可用房屋，使用其中 24 种，形成 41 个地图实例；另 1 组纯黑源贴图建筑仅保留排除记录，不列为可用模型。','','## 编号读法','','`S02-B01-I01`：第 S02 份源文件 / B01 房屋类型 / I01 地图实例。独立 GLB 的根与部件包含模型编号；城市区块内每个源网格包含完整实例编号、源文件、源节点、替换对象及组团。','','地图实例以世界米制坐标记录；独立素材为底部中心原点，地图区块保持原世界坐标。编号只出现在文件、节点、属性和标注预览，不烙入建筑贴图。','','## 九份素材审查','']
for s in sources:lines.append(f"- **{s['id']} · {s['file']}**：{s['decision_zh']}")
lines+=['','## 建筑目录','','| 编号 | 名称 | 来源 | 状态 | 实例数量 |','|---|---|---|---|---:|']
for a in catalog:lines.append(f"| {a['asset_id']} | {a['display_name_zh']} | {a['source_filename']} | {'已落位' if a['map_instance_count'] else '源贴图纯黑，排除' if a['status'].startswith('rejected') else '可用备用'} | {a['map_instance_count']} |")
lines+=['','## 贴图增强','','`S04-B02 / B03 / B04 / B06` 共用的 FillerBuildings1 贴图，经内置图像生成工具增强砖缝、墙面、窗框和金属边缘；原图 1024×1024，增强图实际为 1254×1254。保留几何与 UV，增强是细节重建，不声称恢复了丢失的原始信息。其余纹理保留源像素；纯黑、单面、缺面和极低分辨率近景候选没有混入交付。增强提示词保存在 `metadata/texture_enhancement_prompt.txt`。','','## 数量与布局','','37 栋占位楼被替换或整组重新组织，落入 41 栋正式素材，原 543 栋变为 547 栋；老城沿街 120 栋、后巷 80 栋和原正式素材保持。只修改 04、08、09、14 四区块，其余 14 块沿用原哈希。','','- 两处新城商住街坊采用连续街面、转角变化和共享内院。','- 商务楼沿既有弯路布置，采用不同高度，保留原道路骨架。','- 西岛为低层住宅、巷口店铺和共享绿院。','- 东岛为厂房、服务楼围合的装卸院。','','`building_map_instances.csv` 逐栋列出所有替换对应关系、坐标、角度和缩放。旧占位地块被合并组织时，一个新实例可能对应两个被移除的旧地块；CSV 会列出全部旧编号。']
(out/'ANNOTATIONS_zh.md').write_text('\n'.join(lines)+'\n')
print('ANNOTATIONS',len(catalog),len(instances),len(used))
