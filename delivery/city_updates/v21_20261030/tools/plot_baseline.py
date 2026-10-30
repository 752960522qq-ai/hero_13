from pathlib import Path
import json,gzip
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];p=json.load(open(R/'baseline/city_plan.json'))
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
for reg,bounds in [('MAIN',(450,340,1060,1060)),('WEST',(-1320,-1130,-430,-710))]:
 x0,y0,x1,y1=bounds;im=Image.new('RGB',(1400,1200),'#ecf1e9');d=ImageDraw.Draw(im);s=min(1300/(x1-x0),1100/(y1-y0))
 def xy(q):return (50+(q[0]-x0)*s,1150-(q[1]-y0)*s)
 for e in p['edges']:
  if e['region']!=reg:continue
  pts=[xy(q) for q in e['points']];d.line(pts,fill='#adb6b7',width=max(2,int(e['width']*s)))
  d.line(pts,fill='#4a5157',width=max(2,int(e['carriage_width']*s)))
 for b in p['buildings']:
  if b['region']!=reg:continue
  d.polygon([xy(q) for q in b['footprint']],fill='#b1a489',outline='#6a5d40');q=xy(b['center']);d.text(q,b['name'].split('_')[-1]+':'+str(b.get('block_id','')),font=font,fill='#30271e')
 for b in p['real_buildings']:
  if b.get('region','MAIN')!=reg:continue
  d.polygon([xy(q) for q in b['footprint_xy']],fill='#ab6f63',outline='#5d312c')
 for x in range(int(x0//100)*100,int(x1)+1,100):
  for y in range(int(y0//100)*100,int(y1)+1,100):
   q=xy([x,y]);d.ellipse((q[0]-2,q[1]-2,q[0]+2,q[1]+2),fill='blue');d.text(q,str(x)+','+str(y),font=font,fill='blue')
 im.save(R/'previews'/f'{reg}_baseline_plan.png')
