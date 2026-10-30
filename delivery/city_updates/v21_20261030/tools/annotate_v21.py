"""Create exact model ID annotations and one-instance catalog previews."""
from pathlib import Path
import json,math,shutil,io,os
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];fontpath=R.parent/'work_v20/NotoSansCJKsc-Regular.otf';fontpath=fontpath if fontpath.exists() else Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');out=R/'previews/final';out.mkdir(parents=True,exist_ok=True);deliver=R/'deliverables';deliver.mkdir(exist_ok=True)
def font(n):return ImageFont.truetype(str(fontpath),n)
def save_png(image,path):
 stream=io.BytesIO();image.save(stream,format='PNG');data=stream.getvalue();temp=path.with_suffix('.staging')
 with temp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 with Image.open(temp) as check:check.verify()
 temp.replace(path)
def atomic_copy(source,dest):
 temp=dest.with_suffix('.staging');data=source.read_bytes()
 with temp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 if dest.suffix=='.png':
  with Image.open(temp) as check:check.verify()
 temp.replace(dest)
cat=json.load(open(R/'asset_catalog.json'));colors={'S05':'#267ca8','S07':'#a45739','S08':'#8257ab','S09':'#397c58'};titles={'01_newtown_north':'新城北部街坊','02_newtown_east':'新城东侧楼群','03_west_courts':'西岛转角街坊','04_west_street':'西岛沿街补充','05_newtown_plan':'新城建筑落位总览','06_south_mixed':'新城南侧混合街面'}
for view in json.load(open(R/'renders/projections.json')):
 base=R/'renders'/view['file'];im=Image.open(base).convert('RGB');W,H=im.size;draw=ImageDraw.Draw(im,'RGBA');name=base.stem;draw.rectangle((0,0,W,95),fill=(18,31,42,233));draw.text((26,12),'v21  '+titles[name],font=font(32),fill='white');draw.text((28,58),'这批22款各用一次  ·  编号旁标记的楼体保留未封口状态',font=font(20),fill='#d4e5ed')
 occupied=[]
 for a in sorted(view['anchors'],key=lambda a:a['y']):
  x,y=a['x'],a['y'];label=a['asset_id']+' *';color=colors[a['asset_id'][:3]];tw=draw.textbbox((0,0),label,font=font(20))[2]+20;th=31;options=[]
  for dx,dy in [(-tw/2,-42),(-tw/2,-75),(16,-16),(-tw-16,-16),(-tw/2,26),(30,-62),(-tw-30,-62)]:
   bx=max(6,min(W-tw-6,x+dx));by=max(105,min(H-76,y+dy));rect=(bx,by,bx+tw,by+th);over=sum(max(0,min(rect[2],b[2])-max(rect[0],b[0]))*max(0,min(rect[3],b[3])-max(rect[1],b[1])) for b in occupied);options.append((over,rect))
  _,rect=min(options,key=lambda x:x[0]);occupied.append(rect);draw.line((x,y,(rect[0]+rect[2])/2,rect[3]),fill=color,width=2);draw.ellipse((x-4,y-4,x+4,y+4),fill=color,outline='white',width=1);draw.rounded_rectangle(rect,radius=5,fill=color,outline='white',width=1);draw.text((rect[0]+10,rect[1]+2),label,font=font(20),fill='white')
 draw.rectangle((0,H-51,W,H),fill=(18,31,42,225));draw.text((24,H-39),'* 未封口／缺口保留；详见逐款问题清单。编号均对应唯一 I01 实例。',font=font(21),fill='white');save_png(im,out/(name+'_annotated.png'));atomic_copy(base,out/(name+'_clean.png'))
for page in range(2):
 items=cat[page*12:(page+1)*12];im=Image.new('RGB',(1600,1500),'#ecf1f5');draw=ImageDraw.Draw(im);draw.rectangle((0,0,1600,60),fill='#142732');draw.text((22,11),f'v21 新提取建筑  ·  每款仅用一次  ·  {page+1}/2',font=font(29),fill='white')
 for ix,a in enumerate(items):
  x=(ix%4)*400;y=60+(ix//4)*480;thumb=Image.open(R/'renders/assets'/(a['asset_id']+'.png')).convert('RGB').resize((370,370));im.paste(thumb,(x+15,y));title=a['asset_id']+' '+a['display_name_zh'];size=22
  while draw.textlength(title,font=font(size))>376:size-=1
  draw.text((x+12,y+372),title,font=font(size),fill='#1b2b34');draw.text((x+12,y+406),a['source_filename'],font=font(19),fill=colors[a['source_id']]);note='开放楼板 / 施工楼' if a['asset_id']=='S08-B03' else '未封口 / 缺口保留';draw.text((x+12,y+438),note+'   ×1',font=font(21),fill='#9b4c19')
 save_png(im,out/f'07_new_models_catalog_{page+1}.png')
# Two map comparisons use the same cameras, exposure and frame dimensions.
W,H=1900,1540;im=Image.new('RGB',(W,H),'#eff3f5');draw=ImageDraw.Draw(im);draw.rectangle((0,0,W,75),fill='#142732');draw.text((25,13),'v20 → v21  ·  22款各放一栋  ·  全城604栋',font=font(35),fill='white')
for col,name in enumerate(['01_newtown_north','03_west_courts']):
 for row,before in enumerate([True,False]):
  x=col*950;y=90+row*715;f=R/'renders'/(name+('_before' if before else '')+'.png');pic=Image.open(f).convert('RGB');pic.thumbnail((930,655));im.paste(pic,(x+(950-pic.width)//2,y));draw.text((x+20,y+657),('v20 改造前' if before else 'v21 新楼型各用一次')+' · '+titles[name],font=font(26),fill='#20333e')
save_png(im,out/'08_before_after_v21.png')
selected=[('01_newtown_north_annotated.png','v21_01_newtown_north_annotated.png'),('02_newtown_east_annotated.png','v21_02_newtown_east_annotated.png'),('03_west_courts_annotated.png','v21_03_west_courts_annotated.png'),('04_west_street_annotated.png','v21_04_west_street_annotated.png'),('06_south_mixed_annotated.png','v21_05_south_mixed_annotated.png'),('07_new_models_catalog_1.png','v21_06_new_models_catalog_1.png'),('07_new_models_catalog_2.png','v21_07_new_models_catalog_2.png'),('08_before_after_v21.png','v21_08_before_after.png')]
for src,dst in selected:atomic_copy(out/src,deliver/dst)
(R/'deliverable_files.json').write_text(json.dumps([str((deliver/dst).resolve()) for _,dst in selected],indent=2));print('PREVIEWS_COMPLETE',len(selected),flush=True)
