import bpy,sys
from pathlib import Path
p=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(p/'huizhou_road_network.blend'))
bpy.ops.export_scene.gltf(filepath=str(p/'huizhou_road_network.glb'),export_format='GLB',export_yup=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,export_image_format='AUTO',export_copyright='Road Modular by mortalityrexotable, CC BY 4.0. User supplied building assets retain original textures.')
print('V14_LOCAL_MASTER_EXPORTED',flush=True)
