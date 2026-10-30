from pathlib import Path
import json,math,collections
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];font=R/'NotoSansCJKsc-Regular.otf';catalog=json.load(open(R/'asset_catalog.json'));usable=[a for a in catalog if not a['status'].startswith('rejected')];out=R/'previews/final';out.mkdir(exist_ok=True)
def F(size):return ImageFont.truetype(str(font),size)
def fittext(d,txt,width,size):
 while d.textbbox((0,0),txt,font=F(size))[2]>width and size>12:size-=1
 return F(size)
for page in range(2):
 items=usable[page*14:(page+1)*14];W=1900;cw=475;ch=590;im=Image.new('RGB',(W,150+ch*math.ceil(len(items)/4)),(237,239,241));d=ImageDraw.Draw(im);d.text((32,20),f'分割房屋目录 · {page+1}/2',font=F(44),fill=(25,36,49));d.text((34,87),'S 来源文件  /  B 房屋类型  /  I 地图实例    ·    26 种可用，24 种已落位',font=F(24),fill=(68,79,91))
 for i,a in enumerate(items):
  x=(i%4)*cw;y=150+(i//4)*ch;img=Image.open(R/'previews/catalog'/(a['asset_id']+'.png')).convert('RGB').resize((cw-16,cw-16));im.paste(img,(x+8,y));d.text((x+16,y+cw-10),a['asset_id']+'  '+a['display_name_zh'],font=fittext(d,a['asset_id']+'  '+a['display_name_zh'],cw-32,25),fill=(22,42,57));d.text((x+16,y+cw+29),a['source_filename'],font=fittext(d,a['source_filename'],cw-32,18),fill=(83,93,104));status=f"已落位 {a['map_instance_count']} 栋" if a['map_instance_count'] else '备用 · 未落位';d.text((x+16,y+cw+57),status+f"  /  高 {a['normalized_size_m'][2]:g}m",font=F(19),fill=(18,99,83) if a['map_instance_count'] else (158,99,29))
  if a.get('enhancement'):d.text((x+16,y+cw+86),'共用贴图已做 AI 细节增强',font=F(18),fill=(125,77,26))
 im.save(out/f'building_catalog_{page+1}.png')
# Exact labels are drawn from saved camera projections, not guessed from the image.
proj=R/'renders/projections.json'
if proj.exists():
 colors={'S02':(31,112,125),'S03':(60,85,135),'S04':(152,99,45),'S06':(112,66,106)}
 filters={'01_newtown_courts':{'NT_WEST_COURT','NT_EAST_COURT'},'02_west_court_close':{'NT_WEST_COURT'},'03_mixed_promonade':{'NT_MIXED_PROMENADE'},'04_west_garden':{'WEST_GARDEN_LANES'},'05_industrial_court':{'EAST_LOADING_COURT'}}
 titles={'01_newtown_courts':'新城商住街坊 · 实际模型与实例编号','02_west_court_close':'西侧连续街面与共享内院','03_mixed_promonade':'沿弯路错落布置的商务组团','04_west_garden':'西岛花园巷 · 住宅与巷口店铺','05_industrial_court':'东岛厂房与共享装卸院','06_main_island':'北岛全景 · 道路与原正式建筑保留'}
 for view in json.load(open(proj)):
  name=Path(view['file']).stem;raw=Image.open(R/'renders'/view['file']).convert('RGB');W,H=raw.size;im=Image.new('RGB',(W,H+110),'#f2f3f5');im.paste(raw,(0,80));d=ImageDraw.Draw(im);d.text((26,15),titles.get(name,name),font=F(32),fill=(25,40,50));rects=[]
  anchors=[a for a in view['anchors'] if name in filters and a['group'] in filters[name]]
  for a in sorted(anchors,key=lambda a:a['y']):
   x,y=a['x'],a['y']+80;text=a['instance_id'];f=F(21);bb=d.textbbox((0,0),text,font=f);w=bb[2]+14;h=31;c=colors[a['asset_id'].split('-')[0]];pos=None
   for dy in [-42,-77,-112,13,48,83]:
    for dx in [-w/2,12,-w-12]:
     xx=max(5,min(W-w-5,x+dx));yy=max(82,min(H+70-h,y+dy));r=(xx,yy,xx+w,yy+h)
     if not any(r[0]<b[2]+4 and r[2]>b[0]-4 and r[1]<b[3]+4 and r[3]>b[1]-4 for b in rects):pos=r;break
    if pos:break
   if pos is None:pos=(max(5,min(W-w-5,x-w/2)),max(82,y-42),max(5,min(W-w-5,x-w/2))+w,max(82,y-42)+h)
   rects.append(pos);d.line([(x,y),((pos[0]+pos[2])/2,pos[3] if pos[3]<y else pos[1])],fill=c,width=2);d.ellipse((x-4,y-4,x+4,y+4),fill=c,outline='white',width=1);d.rounded_rectangle(pos,radius=4,fill=(250,251,252),outline=c,width=2);d.text((pos[0]+7,pos[1]+1),text,font=f,fill=c)
  d.text((22,H+84),'编号对应 CSV、独立 GLB 文件与城市区块节点；模型贴图中不写字。',font=F(18),fill=(62,73,83));im.save(out/(name+'_annotated.png'))
print('PREVIEW_CATALOGS_READY')
