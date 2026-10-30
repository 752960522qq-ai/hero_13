from pathlib import Path
import json,math,shutil
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];out=R/'previews/final';out.mkdir(parents=True,exist_ok=True);fontfile=R/'NotoSansCJKsc-Regular.otf';font=lambda n:ImageFont.truetype(str(fontfile),n);titlefont=font(31);small=font(19);label=font(17);p=json.load(open(R/'model/city_plan.json'));layout=json.load(open(R/'layout.json'));sites=json.load(open(R/'model/site_levels.json'));props=json.load(open(R/'model/public_instances.json'))
titles={'01_newtown_crescent':'新城弧线生活街｜新增 25 栋','02_west_market':'西岛曲街｜20 栋商住楼与住宅','03_stepped_campus':'新城高低搭配商务组团｜新增 4 栋','04_newtown_roads':'新城道路与街坊布局','05_west_street_close':'西岛生活街近景｜电线杆、绿植与店铺'}
colors={'NT_CRESCENT_SHOPFRONTS':'#2176ab','WEST_MARKET_STREET':'#b76c1f','NT_STEPPED_CAMPUS':'#26866a'}
def labels(draw,anchors,W,H,scale=1):
 boxes=[]
 for a in sorted(anchors,key=lambda x:(x['y'],x['x'])):
  text=a['instance_id'];color=colors[a['group']];x=a['x'];y=a['y'];bb=draw.textbbox((0,0),text,font=label);w=bb[2]-bb[0]+14;h=30;opts=[]
  for radius in [22,45,75,105,140]:
   for theta in [0,math.pi,math.pi/2,-math.pi/2,.7,2.4,-.7,-2.4]:
    xx=max(6,min(W-w-6,x+math.cos(theta)*radius-w/2));yy=max(78,min(H-h-7,y+math.sin(theta)*radius-h/2));rect=(xx,yy,xx+w,yy+h);area=sum(max(0,min(rect[2],b[2])-max(rect[0],b[0]))*max(0,min(rect[3],b[3])-max(rect[1],b[1])) for b in boxes);opts.append((area*100+radius,rect))
  _,rect=min(opts,key=lambda x:x[0]);boxes.append(rect);cx=(rect[0]+rect[2])/2;cy=(rect[1]+rect[3])/2;draw.line([(x,y),(cx,cy)],fill=color,width=2);draw.ellipse((x-3,y-3,x+3,y+3),fill=color,outline='white');draw.rounded_rectangle(rect,radius=4,fill='#fcfcf8',outline=color,width=2);draw.text((rect[0]+7,rect[1]+3),text,font=label,fill=color)
for view in json.load(open(R/'renders/projections.json')):
 stem=Path(view['file']).stem;src=Image.open(R/'renders'/view['file']).convert('RGB');W,H=src.size;im=Image.new('RGB',(W,H+82),'#fafbf7');im.paste(src,(0,82));draw=ImageDraw.Draw(im);draw.text((24,12),titles[stem],font=titlefont,fill='#172d3b');draw.text((24,51),'hero_13 · v20｜编号对应模型节点与 CSV，建筑与设施均为实际场景渲染',font=small,fill='#506171');im.save(out/(stem+'_clean.png'));anchors=[{**a,'y':a['y']+82} for a in view['anchors']];labels(draw,anchors,W,H+82);im.save(out/(stem+'_annotated.png'))
# Dedicated plans make every new identifier readable without roof occlusion.
for region,bounds,size,name in [('MAIN',(610,560,935,805),(2100,1600),'06_main_building_plan'),('WEST',(-1030,-985,-770,-855),(2100,1200),'07_west_building_plan')]:
 W,H=size;x0,y0,x1,y1=bounds;s=min((W-140)/(x1-x0),(H-180)/(y1-y0));im=Image.new('RGB',size,'#edf2e8');d=ImageDraw.Draw(im)
 def xy(q):return (65+(q[0]-x0)*s,H-75-(q[1]-y0)*s)
 for e in p['edges']:
  if e['region']!=region:continue
  pts=[xy(q) for q in e['points']];new=e['name'].startswith('V20_');d.line(pts,fill='#c8c9be',width=max(1,int(e['width']*s)));d.line(pts,fill='#3e5967' if new else '#8f9a9e',width=max(1,int(e['carriage_width']*s)))
 for b in p['buildings']+p['real_buildings']:
  if b.get('region','MAIN')!=region:continue
  poly=b.get('footprint',b.get('footprint_xy'));new=b.get('added_in_version')=='v20';d.polygon([xy(q) for q in poly],fill=colors.get(b.get('group'),'#c6c7b9') if new else '#d5d5c7',outline='#6c7877')
 for a in props:
  if 'center' not in a:continue
  q=xy(a['center'])
  if a['type'] in ['tree','shrub']:d.ellipse((q[0]-5,q[1]-5,q[0]+5,q[1]+5),fill='#6f9c48')
  if a['type']=='utility_pole':d.rectangle((q[0]-3,q[1]-3,q[0]+3,q[1]+3),fill='#714b32')
 anchors=[]
 for a in sites:
  if a['region']!=region:continue
  xx,yy=xy(a['center']);anchors.append(dict(instance_id=a['name'],x=xx,y=yy,group=a['group']))
 d.rectangle((0,0,W,80),fill='#fafbf7');d.text((25,12),'新城逐栋编号平面图' if region=='MAIN' else '西岛逐栋编号平面图',font=titlefont,fill='#172d3b');d.text((25,51),'深蓝道路：本轮新增｜浅色建筑：原场景｜彩色建筑：本轮新增，全部编号可在 CSV 查找',font=small,fill='#506171');labels(d,anchors,W,H);im.save(out/(name+'.png'))
W,H=2000,1660;im=Image.new('RGB',(W,H),'#fafbf7');d=ImageDraw.Draw(im);d.text((30,15),'v19 → v20｜弧线街坊与公共设施对比',font=titlefont,fill='#172d3b')
for i,stem in enumerate(['01_newtown_crescent','02_west_market']):
 for j,suffix in enumerate(['_before','']):
  pic=Image.open(R/'renders'/(stem+suffix+'.png')).convert('RGB');pic.thumbnail((980,710));x=10+j*1000;y=115+i*780;im.paste(pic,(x,y));d.text((x+12,y-33),('v19 之前' if j==0 else 'v20 现在')+' · '+('新城' if i==0 else '西岛'),font=font(24),fill='#314657')
im.save(out/'08_before_after_v20.png')
print('ANNOTATED',len(sites),'buildings',len(props),'public instances',flush=True)
