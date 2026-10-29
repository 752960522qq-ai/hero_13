import json,struct
for f in ['vest_xiaqing','green_t_xiaqing','school_uniform_xiaqing','floral_dress_xiaqing']:
 b=open('/workspace/recovered-xiaqing-site/dist/assets/'+f+'.glb','rb').read(); j=json.loads(b[20:20+struct.unpack_from('<I',b,12)[0]])
 print(f,len(j['nodes']),[(x['name'],x.get('rotation'),x.get('translation'),x.get('scale')) for x in j['nodes'] if x.get('name') in ['COG','hips','l_arm_humerus','l_arm_radius','l_leg_tibia','l_arm_humerus_twist_3_H']])
 print('anim',[(a['name'],len(a['channels'])) for a in j['animations']])
