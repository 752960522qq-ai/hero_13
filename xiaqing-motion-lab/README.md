# 夏晴_牛仔裤 · 动作测试

The existing character test Site now uses the uploaded trousers model, named `夏晴_牛仔裤` in the Blender rig, web UI and runtime scene.

## Character

- Rebound from an unrigged T-pose to 22 body bones, fitted to this model's shoulders, elbows, wrists, hips, knees and sneaker height.
- Welded 15 source material partitions into one continuous skinned surface. Original textures and UV charts are retained. Source punctures are capped; source and exported GLB have zero open boundary edges.
- Reprojected the five existing motion clips to the new proportions: Idle, Walk, Run, ArmRaise, HandTest. T-pose arm orientation is converted to a relaxed neutral pose; hand orientation follows the forearm for locomotion, while HandTest retains wrist motion.
- Mesh vertices have at most four normalized bone influences. Sneakers are grounded from evaluated geometry while baking.
- Material color inspection separates skin/sleeve sections, hair, shirt, trousers, and left/right sneakers. These are color categories on a welded surface; the source sleeves share arm material charts.

## Verification

Blender 4.5.3 LTS: rendered neutral standing, walk/run and arm raising; sampled 11 poses per clip (55 poses) for finite bounded deformation. Source surface has zero boundary/nonmanifold edges. Export validation confirms 22 joints, five finite animation clips, normalized weights and zero open boundary edges after consolidating UV/material seams. JS syntax checked with Node. Browser and physical-phone interaction were not tested in this environment.

Hands use whole-hand bones; individual finger articulation is not included. Extreme poses can still show local garment intersections. No Android build or game-engine integration is part of this revision.

## Deliverables

- `dist/assets/xiaqing_trousers_rigged.glb`
- `dist/assets/xiaqing_trousers.blend.zip` — editable Blender scene with packed textures; unzip before opening. NLA tracks are muted for a clean T-pose opening; activate a track to preview animation.
- `dist/assets/jeans-report.json`, `jeans-verification.json`
- `tools/rig_jeans.py`, `verify_jeans.py`, `validate_jeans_glb.py`, `check_jeans_export.py` — session generation and verification scripts referencing the supplied source and prior Blender rig.

## Wrist correction v4.1
Run `tools/fix_jeans_hands.py` after the base rig script. Removes torso weights from distal forearms/palms, blends wrist weights along the forearm axis, and rebuilds HandTest with limited local wrist rotations. No topology changes. This revision checks only Idle frame 1, ArmRaise frame 61 and HandTest frame 23, plus exported GLB consistency; the 55-pose report above describes v4.0. Browser/phone interaction remains untested.

## Elbow and jaw correction v4.2
After the wrist correction run `tools/fix_jeans_elbows_head.py`. Elbow regions now use only upper-arm/forearm weights with a wider transition. Face/jaw vertices above z=0.818 follow Head rigidly; neck blending stays below the jaw. Geometry remains continuous; no cut seams introduced. Targeted validation: Walk 18, Run 9, ArmRaise 61; rigid jaw transform and finite elbow positions; source has zero boundary edges.

## Arm deformation and replacement clips v4.3
`tools/update_motions_arms.py` uses v4.2 as baseline. Idle comes from girl_Idle.fbx; Walk comes from girl Walk.fbx. Run retains its original timing and body/leg motion. Forearm axial twist is removed while preserving bend direction; two midpoint elbow helper bones preserve more bend volume using exported linear skinning. Upper/lower arm skin is isolated from torso influences. Four focused pose samples and a three-pose visual check replace a full animation sweep.

## Source hand pose restoration v4.4
Idle and Run arm, forearm, and hand orientations now come directly from girl_Idle.fbx and Running.fbx. Target neutral segment directions are aligned to the source before applying full animation rotation. This restores wrist articulation removed by the previous forearm-follow override. Elbow helper tracks are rebaked; other clips and body/leg tracks are retained. Segment direction agreement is checked during baking, followed by four focused pose samples and two renders. The mesh still has whole-hand bones, not articulated fingers.

## Natural Idle/Walk hands v4.5
Restore full source arm and wrist orientations for Walk as well as Idle. Add two lightweight grouped finger-bend controls, used only in Idle (17 degrees) and Walk (12 degrees); other animations retain zero curl. The source silhouette, mesh topology, UVs and previous weights outside distal hands are preserved. These controls are a relaxed grouped bend, not separate five-finger articulation.
Lateral arm spread is reduced by 2 degrees in Idle and 5 degrees in Walk to fit the target shoulder width while retaining the source motion timing.

## Elbow extension v4.6
Idle and Walk elbow flexion is reduced 30 percent, retaining a minimum soft bend of four degrees when applicable. Shoulder animation, wrist articulation and finger relaxation are retained. The hand follows the corrected forearm rigidly at the wrist; elbow helpers are rebaked. Running is unchanged. Key poses match the supplied reference timestamps approximately (Idle 211, Walk 11).

## Explicit elbow angles v4.7
With zero degrees defined as a straight upper-arm/forearm chain, Idle uses 10 degrees and Walk uses a continuous mirrored 20–30 degree cycle. Forearm, wrist and elbow-helper tracks are rebaked. Every baked elbow angle is checked against its target; wrist connection is checked. Other actions remain unchanged.

## Straight elbows v4.8
Idle and Walk use zero elbow flexion throughout. Upper-arm and forearm bone directions are collinear; hand articulation is preserved while wrist positions follow the extended forearms. Elbow-helper tracks are rebaked. Other clips are retained.

## Fist replacement v4.9
Replaced both hand islands with the closed-fist geometry extracted from the trenchcoat GLB. Fists use rigid Hand weights; wrist caps use the character skin material and are overlapped into the forearms. Targeted deformation checks cover Idle, Walk and HandTest; the binary GLB passes the existing 26-bone/five-clip validation.


## v5.0 — T 姿势与新拳头
- 双臂静置骨骼改为水平直线，网格重新适配，保留动作骨骼方向。
- 从 `source-models/body.glb` 裁切左右拳头并封口，绑定对应 Hand 骨骼。
- Walk 髋部高度改为周期平滑曲线，腿部逆解保留原脚位置；Run 动作来源不变。
- 专项验证见 `dist/assets/straight-arms-fists-walk-report.json`。


## v5.1 — 替换为新上传的牛仔裤夏晴
- 完整替换为 `source-models/xiaqing_trousers_v51.glb`，保留该模型的外观、材质和拳头。
- 按实际手臂横截面拉直 T 姿势，重新匹配肩肘腕，迁移身体权重并重建手臂权重。
- 保留五套动作和 v5.0 行走平滑高度曲线，检查导出权重、五个关键姿势和模型边界。
- 验证报告：`dist/assets/replacement-model-v51-report.json`。


## v5.3 — 新贴图与肩部微调
- 使用 `xiaqing_trousers(2).glb` 的 35 张贴图，保留已绑定模型的网格、UV 和权重。
- 完成待机、行走肩部约 8% 收拢与手臂内收 3°/5°；跑步、抬手和手腕动作数据保持不变。
- 使用 imagegen 局部修补发束 UV，再以胸前位置和浅色污染遮罩烘焙，仅覆盖胸前发束混入的衣料色。
- 图像编辑提示：保持 UV 岛布局，修补棕色发束内部的白灰衣料色块，延续邻近发丝走向。
- 专项报告：`dist/assets/texture-shoulder-v53-report.json`。
